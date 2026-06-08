"""
Vision Modules Demo
Standalone script to test visual odometry, dynamic obstacle prediction, and scene understanding
"""

import cv2
import numpy as np
import time
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vision.visual_odometry import VisualOdometry
from src.vision.dynamic_obstacle_predictor import DynamicObstaclePredictor
from src.vision.scene_understanding import SceneUnderstanding

def is_camera_available():
    """Check if camera is available"""
    try:
        cap = cv2.VideoCapture(0)
        if cap is not None and cap.isOpened():
            cap.release()
            return True
        return False
    except Exception:
        return False

def main():
    """Main demo function"""
    print("Vision Modules Demo")
    print("==================")
    
    # Check camera availability
    if not is_camera_available():
        print("Error: Camera not available!")
        print("Please ensure a camera is connected and accessible.")
        return
    
    print("Camera detected. Initializing vision modules...")
    
    # Initialize vision modules
    try:
        vo = VisualOdometry()
        dynobs = DynamicObstaclePredictor()
        scene = SceneUnderstanding()
        print("✓ All vision modules initialized successfully")
    except Exception as e:
        print(f"Error initializing vision modules: {e}")
        return
    
    # Open camera
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        print("Error: Cannot open camera!")
        return
    
    print("\nDemo Controls:")
    print("  'q' - Quit")
    print("  'v' - Toggle Visual Odometry")
    print("  'd' - Toggle Dynamic Obstacle Prediction")
    print("  's' - Toggle Scene Understanding")
    print("  'a' - Toggle All")
    print("  'r' - Reset all modules")
    print("\nPress any key to start...")
    cv2.waitKey(0)
    
    # Display flags
    show_vo = True
    show_dynobs = True
    show_scene = True
    
    frame_count = 0
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break
        
        frame_count += 1
        
        # Create display frame
        display_frame = frame.copy()
        
        # Process with vision modules
        results = {}
        
        # Visual Odometry
        if show_vo:
            try:
                motion = vo.process_frame(frame)
                results['vo'] = motion
                vo_status = vo.get_status()
                
                if motion:
                    dx, dy, dtheta = motion
                    # Draw motion vector
                    center = (frame.shape[1]//2, frame.shape[0]//2)
                    end_point = (int(center[0] + dx*1000), int(center[1] + dy*1000))
                    cv2.arrowedLine(display_frame, center, end_point, (0, 255, 0), 2)
                    
                    # Display motion info
                    cv2.putText(display_frame, f"Motion: dx={dx:.3f}, dy={dy:.3f}, dtheta={dtheta:.3f}", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(display_frame, f"Features: {vo_status['features_count']}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                else:
                    # Show status when no motion detected
                    cv2.putText(display_frame, f"VO Status: {vo_status['initialized']}", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.putText(display_frame, f"Features: {vo_status['features_count']}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            except Exception as e:
                print(f"VO error: {e}")
                cv2.putText(display_frame, f"VO Error: {str(e)[:30]}", 
                          (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Dynamic Obstacle Prediction
        if show_dynobs:
            try:
                obstacles = dynobs.process_frame(frame)
                results['dynobs'] = obstacles
                dynobs_status = dynobs.get_status()
                
                for obstacle in obstacles:
                    x, y, w, h = obstacle.bbox
                    
                    # Draw bounding box with color based on risk level
                    color = (0, 0, 255) if obstacle.risk_level == "high" else (0, 165, 255) if obstacle.risk_level == "medium" else (0, 255, 0)
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                    
                    # Draw predicted position
                    if obstacle.predicted_position:
                        pred_x, pred_y = obstacle.predicted_position
                        cv2.circle(display_frame, (int(pred_x), int(pred_y)), 5, (255, 0, 0), -1)
                        cv2.line(display_frame, (x + w//2, y + h//2), (int(pred_x), int(pred_y)), (255, 0, 0), 2)
                    
                    # Display obstacle info
                    label = f"{obstacle.class_name} ({obstacle.confidence:.2f})"
                    if obstacle.time_to_collision:
                        label += f" TTC: {obstacle.time_to_collision:.1f}s"
                    cv2.putText(display_frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                cv2.putText(display_frame, f"Tracked Objects: {dynobs_status['tracked_objects_count']}", 
                          (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(display_frame, f"Detector: {'Available' if dynobs_status['detector_available'] else 'Fallback'}", 
                          (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            except Exception as e:
                print(f"Dynamic obstacle error: {e}")
                cv2.putText(display_frame, f"DO Error: {str(e)[:30]}", 
                          (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        
        # Scene Understanding
        if show_scene:
            try:
                scene_analysis = scene.process_frame(frame)
                results['scene'] = scene_analysis
                scene_status = scene.get_status()
                
                # Draw regions
                regions = scene_analysis.get('regions', [])
                for region in regions:
                    x, y, w, h = region.bbox
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), region.color, 2)
                    
                    # Display region info
                    label = f"{region.element_type.value} ({region.confidence:.2f})"
                    cv2.putText(display_frame, label, (x, y + h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, region.color, 1)
                
                # Display navigation features
                nav_features = scene_analysis.get('navigation_features', {})
                cv2.putText(display_frame, f"Safe Directions: {len(nav_features.get('safe_directions', []))}", 
                          (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(display_frame, f"Recommended Speed: {nav_features.get('recommended_speed', 1.0):.1f}", 
                          (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                cv2.putText(display_frame, f"Clearance: {nav_features.get('clearance_estimate', 1.0):.1f}m", 
                          (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            except Exception as e:
                print(f"Scene understanding error: {e}")
        
        # Display FPS
        elapsed_time = time.time() - start_time
        fps = frame_count / elapsed_time if elapsed_time > 0 else 0
        cv2.putText(display_frame, f"FPS: {fps:.1f}", (10, display_frame.shape[0] - 40), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Display status
        status_text = f"VO: {'ON' if show_vo else 'OFF'} | DO: {'ON' if show_dynobs else 'OFF'} | SU: {'ON' if show_scene else 'OFF'}"
        cv2.putText(display_frame, status_text, (10, display_frame.shape[0] - 20), 
                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Display controls
        cv2.putText(display_frame, "q=quit v=VO d=Obstacles s=Scene a=All r=Reset", 
                  (10, display_frame.shape[0] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
        
        cv2.imshow("Vision Modules Demo", display_frame)
        
        # Handle key presses
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('v'):
            show_vo = not show_vo
            print(f"Visual Odometry: {'ON' if show_vo else 'OFF'}")
        elif key == ord('d'):
            show_dynobs = not show_dynobs
            print(f"Dynamic Obstacles: {'ON' if show_dynobs else 'OFF'}")
        elif key == ord('s'):
            show_scene = not show_scene
            print(f"Scene Understanding: {'ON' if show_scene else 'OFF'}")
        elif key == ord('a'):
            show_vo = show_dynobs = show_scene = not show_vo
            print(f"All modules: {'ON' if show_vo else 'OFF'}")
        elif key == ord('r'):
            vo.reset()
            dynobs.reset()
            scene.reset()
            print("All modules reset")
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("\nDemo completed!")

if __name__ == "__main__":
    main() 