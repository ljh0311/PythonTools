import cv2
import numpy as np
import time
from brightness_controller import HumanDetector


def main():
    # Create BrightnessController instance with distance detection enabled
    controller = HumanDetector(
        enable_human_detection=True, 
        strict_detection=False,
        enable_distance_detection=True
    )
    controller._setup_face_detection()

    # Setup camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera.")
        return

    print("🎯 Distance-Based Human Detection Test")
    print("=" * 50)
    print("Controls:")
    print("  'q' - Quit")
    print("  'c' - Start/Stop Calibration")
    print("  '1' - Add Primary User Sample (close to camera)")
    print("  '2' - Add Distant Person Sample (far from camera)")
    print("  'd' - Toggle Distance Detection")
    print("  's' - Toggle Strict Detection")
    print("  'r' - Reset to Default Thresholds")
    print("=" * 50)

    calibration_mode = False
    distance_detection_enabled = True
    strict_detection_enabled = False

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to grab frame.")
            break

        # Get detailed detection information
        detection_info = controller.get_detection_info(frame)
        
        # Detect human using the controller's method
        human_present = controller.detect_human(frame)

        # Draw detection results on frame
        y_offset = 30
        line_height = 25
        
        # Main detection status
        status_text = "Primary User: " + ("✅ DETECTED" if human_present else "❌ NOT DETECTED")
        color = (0, 255, 0) if human_present else (0, 0, 255)
        cv2.putText(frame, status_text, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        y_offset += line_height

        # Distance detection status
        distance_status = "Distance Detection: " + ("ON" if distance_detection_enabled else "OFF")
        cv2.putText(frame, distance_status, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += line_height

        # Calibration mode status
        if calibration_mode:
            cv2.putText(frame, "CALIBRATION MODE ACTIVE", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            y_offset += line_height
            cv2.putText(frame, f"Samples: {len(controller.calibration_samples)}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += line_height

        # Face detection details
        if detection_info['faces_detected'] > 0:
            cv2.putText(frame, f"Faces Detected: {detection_info['faces_detected']}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += line_height
            
            cv2.putText(frame, f"Largest Face: {detection_info['largest_face_percentage']:.3f}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += line_height

            # Draw rectangles around detected faces with distance-based colors
            for face_detail in detection_info['face_details']:
                x, y, w, h = face_detail['x'], face_detail['y'], face_detail['w'], face_detail['h']
                face_type = face_detail['face_type']
                face_percentage = face_detail['face_percentage']
                
                # Choose color based on face type
                if face_type == "primary_user":
                    color = (0, 255, 0)  # Green for primary user
                    label = "PRIMARY USER"
                elif face_type == "distant_person":
                    color = (0, 165, 255)  # Orange for distant person
                    label = "DISTANT PERSON"
                else:
                    color = (128, 128, 128)  # Gray for undetected
                    label = "TOO SMALL"
                
                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Draw label
                cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                # Draw face percentage
                cv2.putText(frame, f"{face_percentage:.3f}", (x, y + h + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        else:
            cv2.putText(frame, "No faces detected", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (128, 128, 128), 2)
            y_offset += line_height

        # Show current thresholds
        if distance_detection_enabled:
            y_offset += 10
            cv2.putText(frame, "Current Thresholds:", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
            y_offset += 20
            
            thresholds = detection_info['thresholds']
            cv2.putText(frame, f"Primary User Min: {thresholds['primary_user_min']:.3f}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            y_offset += 15
            cv2.putText(frame, f"Distant Person Min: {thresholds['distant_person_min']:.3f}", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 165, 255), 1)
            y_offset += 15

        # Show detection instability info
        controller._check_detection_instability()
        instability_info = f"Instability: {controller.detection_instability_count}"
        cv2.putText(frame, instability_info, (10, frame.shape[0] - 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        strict_mode_info = f"Strict Mode: {controller.strict_detection}"
        cv2.putText(frame, strict_mode_info, (10, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Show instructions
        cv2.putText(frame, "Press 'c' for calibration, 'q' to quit", (10, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        cv2.imshow("Distance-Based Human Detection Test", frame)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('c'):
            if not calibration_mode:
                controller.start_calibration()
                calibration_mode = True
                print("🎯 Calibration started! Position yourself at different distances and press '1' or '2' to add samples.")
            else:
                success = controller.stop_calibration()
                calibration_mode = False
                if success:
                    print("✅ Calibration completed successfully!")
                else:
                    print("⚠️ Calibration failed. Need at least 5 samples.")
        elif key == ord('1') and calibration_mode:
            if detection_info['largest_face_percentage'] > 0:
                controller.add_calibration_sample(detection_info['largest_face_percentage'], 'primary_user')
            else:
                print("⚠️ No face detected to add as primary user sample.")
        elif key == ord('2') and calibration_mode:
            if detection_info['largest_face_percentage'] > 0:
                controller.add_calibration_sample(detection_info['largest_face_percentage'], 'distant_person')
            else:
                print("⚠️ No face detected to add as distant person sample.")
        elif key == ord('d'):
            distance_detection_enabled = not distance_detection_enabled
            controller.enable_distance_detection = distance_detection_enabled
            print(f"🔧 Distance detection {'enabled' if distance_detection_enabled else 'disabled'}")
        elif key == ord('s'):
            strict_detection_enabled = not strict_detection_enabled
            controller.strict_detection = strict_detection_enabled
            print(f"🔧 Strict detection {'enabled' if strict_detection_enabled else 'disabled'}")
        elif key == ord('r'):
            # Reset to default thresholds
            controller.calibrated_thresholds = {
                'primary_user_min': 0.025,
                'primary_user_max': 0.15,
                'distant_person_min': 0.008,
                'distant_person_max': 0.025
            }
            print("🔄 Reset to default thresholds")

    cap.release()
    cv2.destroyAllWindows()
    
    # Print final summary
    print("\n" + "=" * 50)
    print("Session Summary:")
    print(f"Final thresholds: {controller.calibrated_thresholds}")
    print("=" * 50)


if __name__ == "__main__":
    main()