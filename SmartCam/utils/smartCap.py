import cv2
import numpy as np
import time
from main import FaceAnalyzer, MotionDetector

def auto_capture_on_face_or_motion(
    camera_id=0,
    output_dir="captures",
    min_interval=2.0,
    face_quality_threshold=0.2,
    motion_sensitivity=0.3,
    show_window_name="Auto Capture (Face/Motion)",
    draw_face_box=True,
    draw_motion_text=True,
    save_format="jpg"
):
    """
    Automatically capture frames from the camera when a face or motion is detected.

    Parameters:
        camera_id (int): Camera index for cv2.VideoCapture.
        output_dir (str): Directory to save captured images.
        min_interval (float): Minimum seconds between captures.
        face_quality_threshold (float): Minimum face quality to trigger capture.
        motion_sensitivity (float): Sensitivity for motion detection.
        show_window_name (str): Name of the OpenCV window.
        draw_face_box (bool): Whether to draw face bounding boxes.
        draw_motion_text (bool): Whether to overlay motion text on frame.
        save_format (str): Image file format for saving captures.
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        print("❌ Unable to open camera.")
        return

    face_analyzer = FaceAnalyzer()
    motion_detector = MotionDetector(sensitivity=motion_sensitivity)

    last_capture_time = 0

    print("🚦 Auto-capture started. Press 'q' to quit.")
    print(f"Configurations:")
    print(f"  camera_id={camera_id}")
    print(f"  output_dir='{output_dir}'")
    print(f"  min_interval={min_interval}")
    print(f"  face_quality_threshold={face_quality_threshold}")
    print(f"  motion_sensitivity={motion_sensitivity}")
    print(f"  save_format={save_format}")
    print(f"  draw_face_box={draw_face_box}, draw_motion_text={draw_motion_text}")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to read frame from camera.")
            break

        # Detect faces
        faces = face_analyzer.detect_faces(frame)
        # Detect motion
        motion = motion_detector.detect_motion(frame)

        capture_reason = None
        if faces and any(face['face_quality'] > face_quality_threshold for face in faces):
            capture_reason = "face"
        elif motion:
            capture_reason = "motion"

        now = time.time()
        if capture_reason and (now - last_capture_time) >= min_interval:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{output_dir}/capture_{capture_reason}_{timestamp}.{save_format}"
            cv2.imwrite(filename, frame)
            print(f"📸 Captured image due to {capture_reason}: {filename}")
            last_capture_time = now

        # Draw face bounding boxes for visualization
        if draw_face_box and faces:
            for face in faces:
                x, y, w, h = face['bbox']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, f"Q:{face['face_quality']:.2f}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        if draw_motion_text and motion:
            cv2.putText(frame, "MOTION DETECTED", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        cv2.imshow(show_window_name, frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("🛑 Auto-capture stopped.")

if __name__ == "__main__":
    auto_capture_on_face_or_motion()
