#!/usr/bin/env python3
"""
AI Smart Camera System Demo
Demonstrates key features and capabilities of the AI-powered camera system.
"""

import cv2
import numpy as np
import time
import os
from datetime import datetime
from main import SmartCamera, ImageQualityEnhancer, FaceAnalyzer, MotionDetector

def demo_image_enhancement():
    """Demonstrate image enhancement capabilities."""
    print("🎯 Image Enhancement Demo")
    print("=" * 40)
    
    # Initialize enhancer
    enhancer = ImageQualityEnhancer()
    
    # Create a test image (or use camera)
    print("Initializing camera for enhancement demo...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Camera not available. Creating synthetic test image...")
        # Create synthetic test image
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        # Add some noise
        noise = np.random.normal(0, 25, test_image.shape).astype(np.uint8)
        test_image = cv2.add(test_image, noise)
    else:
        ret, test_image = cap.read()
        cap.release()
    
    # Create output directory
    os.makedirs("demo_output", exist_ok=True)
    
    # Apply different enhancements
    enhancement_types = ['auto', 'denoise', 'sharpen', 'color_correction', 'exposure_correction']
    
    for enhancement_type in enhancement_types:
        print(f"Applying {enhancement_type} enhancement...")
        
        # Apply enhancement
        enhanced = enhancer.enhance_image_quality(test_image, enhancement_type)
        
        # Save result
        filename = f"demo_output/enhanced_{enhancement_type}_{datetime.now().strftime('%H%M%S')}.jpg"
        cv2.imwrite(filename, enhanced)
        print(f"✅ Saved: {filename}")
        
        # Show comparison
        comparison = np.hstack([test_image, enhanced])
        cv2.imshow(f"Original vs {enhancement_type.title()}", comparison)
        cv2.waitKey(1000)
    
    cv2.destroyAllWindows()
    print("✅ Image enhancement demo completed!\n")

def demo_face_analysis():
    """Demonstrate face detection and analysis."""
    print("👤 Face Analysis Demo")
    print("=" * 40)
    
    # Initialize face analyzer
    analyzer = FaceAnalyzer()
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not available for face analysis demo")
        return
    
    print("Starting face detection (press 'q' to quit)...")
    
    start_time = time.time()
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect faces
        faces = analyzer.detect_faces(frame)
        
        # Draw results
        for face in faces:
            x, y, w, h = face['bbox']
            quality = face['face_quality']
            eyes = face['eyes_detected']
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Add text
            cv2.putText(frame, f"Quality: {quality:.2f}", (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(frame, f"Eyes: {eyes}", (x, y+h+20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        
        # Show frame
        cv2.imshow("Face Analysis Demo", frame)
        
        frame_count += 1
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time
    print(f"✅ Face analysis demo completed! Average FPS: {fps:.1f}\n")

def demo_motion_detection():
    """Demonstrate motion detection capabilities."""
    print("🎬 Motion Detection Demo")
    print("=" * 40)
    
    # Initialize motion detector
    detector = MotionDetector(sensitivity=0.3)
    
    # Initialize camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Camera not available for motion detection demo")
        return
    
    print("Starting motion detection (press 'q' to quit)...")
    print("Move around to see motion detection in action!")
    
    start_time = time.time()
    motion_count = 0
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect motion
        motion_detected = detector.detect_motion(frame)
        
        if motion_detected:
            motion_count += 1
            # Add motion indicator
            cv2.putText(frame, "MOTION DETECTED!", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.circle(frame, (frame.shape[1]-50, 50), 30, (0, 0, 255), -1)
        
        # Show frame
        cv2.imshow("Motion Detection Demo", frame)
        
        frame_count += 1
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    elapsed_time = time.time() - start_time
    fps = frame_count / elapsed_time
    motion_percentage = (motion_count / frame_count) * 100
    
    print(f"✅ Motion detection demo completed!")
    print(f"   Average FPS: {fps:.1f}")
    print(f"   Motion detected in {motion_percentage:.1f}% of frames\n")

def demo_smart_camera():
    """Demonstrate full smart camera system."""
    print("📹 Smart Camera System Demo")
    print("=" * 40)
    
    try:
        # Initialize smart camera
        print("Initializing Smart Camera System...")
        camera = SmartCamera(camera_id=0)
        
        print("Smart Camera Features:")
        print("- AI-powered image enhancement")
        print("- Face detection and analysis")
        print("- Motion detection")
        print("- Object detection (YOLO)")
        print("- Automatic event capture")
        print()
        
        # Get camera info
        info = camera.get_camera_info()
        print("Camera Information:")
        for key, value in info.items():
            print(f"  {key.title()}: {value}")
        print()
        
        # Start capture
        print("Starting capture (5 seconds)...")
        camera.start_capture()
        
        # Capture a few high-quality images
        for i in range(3):
            time.sleep(2)
            filename = camera.capture_high_quality_image('auto')
            if filename:
                print(f"✅ Captured enhanced image {i+1}: {os.path.basename(filename)}")
        
        # Stop capture
        camera.stop_capture()
        camera.cleanup()
        
        print("✅ Smart camera demo completed!\n")
        
    except Exception as e:
        print(f"❌ Smart camera demo failed: {str(e)}\n")

def main():
    """Run all demos."""
    print("🤖 AI Smart Camera System - Feature Demo")
    print("=" * 50)
    print()
    
    demos = [
        ("Image Enhancement", demo_image_enhancement),
        ("Face Analysis", demo_face_analysis),
        ("Motion Detection", demo_motion_detection),
        ("Full Smart Camera", demo_smart_camera)
    ]
    
    print("Available demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  5. Run all demos")
    print("  6. Exit")
    print()
    
    while True:
        try:
            choice = input("Select demo (1-6): ").strip()
            
            if choice == '1':
                demo_image_enhancement()
            elif choice == '2':
                demo_face_analysis()
            elif choice == '3':
                demo_motion_detection()
            elif choice == '4':
                demo_smart_camera()
            elif choice == '5':
                print("Running all demos...\n")
                for name, demo_func in demos:
                    print(f"🎬 Running {name} Demo")
                    print("-" * 30)
                    demo_func()
                    input("Press Enter to continue to next demo...")
                print("✅ All demos completed!")
                break
            elif choice == '6':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1-6.")
                
        except KeyboardInterrupt:
            print("\n👋 Demo interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"❌ Demo error: {str(e)}")

if __name__ == "__main__":
    main() 