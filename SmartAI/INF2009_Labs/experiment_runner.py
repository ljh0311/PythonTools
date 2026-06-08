import cv2
import numpy as np
import time
import os
from datetime import datetime
import tkinter as tk
from tkinter import simpledialog
import urllib.request
import sys
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.framework.formats import landmark_pb2

def download_file(url, filename):
    """Download a file from URL and show progress"""
    print(f"Downloading {filename}...")
    try:
        urllib.request.urlretrieve(url, filename)
        print(f"Successfully downloaded {filename}")
    except Exception as e:
        print(f"Error downloading {filename}: {str(e)}")
        sys.exit(1)

# Download required models if they don't exist
MODELS = {
    'hand_landmarker.task': 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
    'gesture_recognizer.task': 'https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task',
    'efficientdet.tflite': 'https://storage.googleapis.com/mediapipe-models/object_detector/efficientdet_lite0/int8/1/efficientdet_lite0.tflite'
}

for model_file, model_url in MODELS.items():
    if not os.path.exists(model_file):
        download_file(model_url, model_file)

def ensure_directory(directory):
    """Create directory if it doesn't exist"""
    if not os.path.exists(directory):
        os.makedirs(directory)

def save_screenshot(frame, experiment_name, results_dir):
    """Save a screenshot with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{experiment_name}_{timestamp}.png"
    filepath = os.path.join(results_dir, filename)
    cv2.imwrite(filepath, frame)
    return filename

def start_recording(output_path, frame_size, fps=20.0):
    """Start video recording"""
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    return cv2.VideoWriter(output_path, fourcc, fps, frame_size)

def get_custom_filename():
    """Get custom filename from user using tkinter dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    filename = simpledialog.askstring("Input", "Enter the filename for results (without extension):")
    if filename:
        return filename + ".md"
    return "experiment_results.md"

def run_optical_flow():
    """Run optical flow experiment"""
    print("Running Optical Flow experiment...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return None

    # Get the first frame
    ret, frame = cap.read()
    if not ret:
        return None

    # Initialize optical flow parameters
    old_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Record for 5 seconds
    out = start_recording("temp_optical_flow.avi", (frame.shape[1], frame.shape[0]))
    start_time = time.time()
    
    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate optical flow using Farneback method
        flow = cv2.calcOpticalFlowFarneback(old_gray, frame_gray, None,
                                          0.5, 3, 15, 3, 5, 1.2, 0)
        
        # Visualization
        h, w = frame_gray.shape[:2]
        y, x = np.mgrid[16//2:h:16, 16//2:w:16].reshape(2,-1)
        fx, fy = flow[y,x].T
        
        lines = np.vstack([x, y, x+fx, y+fy]).T.reshape(-1, 2, 2)
        lines = np.int32(lines + 0.5)
        vis = frame.copy()
        cv2.polylines(vis, lines, 0, (0, 255, 0))
        
        cv2.imshow('Optical Flow', vis)
        out.write(vis)
        
        old_gray = frame_gray.copy()
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    out.release()
    cap.release()
    cv2.destroyAllWindows()
    return "temp_optical_flow.avi"

def run_hand_landmark():
    """Run hand landmark detection experiment"""
    print("Running Hand Landmark Detection experiment...")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return None

    # Initialize MediaPipe hand landmark detector
    base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2)
    detector = vision.HandLandmarker.create_from_options(options)

    # Record for 5 seconds
    ret, frame = cap.read()
    out = start_recording("temp_hand_landmark.avi", (frame.shape[1], frame.shape[0]))
    start_time = time.time()

    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect hand landmarks
        detection_result = detector.detect(mp_image)
        
        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                # Draw all 21 landmarks
                for landmark in hand_landmarks:
                    x = int(landmark.x * frame.shape[1])
                    y = int(landmark.y * frame.shape[0])
                    cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

                # Check for thumb up gesture
                threshold = 0.1
                thumb_tip_y = hand_landmarks[4].y
                thumb_base_y = hand_landmarks[1].y
                if thumb_tip_y < thumb_base_y - threshold:
                    cv2.putText(frame, 'Thumb Up', (10,30),
                              cv2.FONT_HERSHEY_DUPLEX, 1, (88, 205, 54), 1)

        cv2.imshow('Hand Landmarks', frame)
        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    out.release()
    cap.release()
    cv2.destroyAllWindows()
    return "temp_hand_landmark.avi"

def run_hand_gesture():
    """Run hand gesture recognition experiment"""
    print("Running Hand Gesture Recognition experiment...")
    recognition_result_list = []
    
    def save_result(result, unused_output_image, timestamp_ms):
        recognition_result_list.append(result)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return None

    # Initialize MediaPipe hand gesture recognizer
    base_options = python.BaseOptions(model_asset_path='gesture_recognizer.task')
    options = vision.GestureRecognizerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
        result_callback=save_result)
    recognizer = vision.GestureRecognizer.create_from_options(options)

    # Record for 5 seconds
    ret, frame = cap.read()
    out = start_recording("temp_hand_gesture.avi", (frame.shape[1], frame.shape[0]))
    start_time = time.time()

    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        recognizer.recognize_async(mp_image, time.time_ns() // 1_000_000)

        if recognition_result_list:
            result = recognition_result_list[0]
            if result.hand_landmarks:
                for hand_index, hand_landmarks in enumerate(result.hand_landmarks):
                    # Draw landmarks
                    hand_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
                    hand_landmarks_proto.landmark.extend([
                        landmark_pb2.NormalizedLandmark(x=landmark.x, y=landmark.y, z=landmark.z)
                        for landmark in hand_landmarks
                    ])
                    mp.solutions.drawing_utils.draw_landmarks(
                        frame,
                        hand_landmarks_proto,
                        mp.solutions.hands.HAND_CONNECTIONS)

                    # Show gesture if detected
                    if result.gestures:
                        gesture = result.gestures[hand_index]
                        category_name = gesture[0].category_name
                        score = round(gesture[0].score, 2)
                        cv2.putText(frame, f'{category_name} ({score})',
                                  (10, 30 + hand_index * 30),
                                  cv2.FONT_HERSHEY_DUPLEX, 1,
                                  (255, 255, 255), 2)

            recognition_result_list.clear()

        cv2.imshow('Hand Gesture Recognition', frame)
        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    out.release()
    cap.release()
    cv2.destroyAllWindows()
    return "temp_hand_gesture.avi"

def run_object_detection():
    """Run object detection experiment"""
    print("Running Object Detection experiment...")
    detection_result_list = []
    
    def save_result(result, unused_output_image, timestamp_ms):
        detection_result_list.append(result)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open webcam")
        return None

    # Initialize MediaPipe object detector
    base_options = python.BaseOptions(model_asset_path='efficientdet.tflite')
    options = vision.ObjectDetectorOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.LIVE_STREAM,
        max_results=5,
        score_threshold=0.5,
        result_callback=save_result)
    detector = vision.ObjectDetector.create_from_options(options)

    # Record for 5 seconds
    ret, frame = cap.read()
    out = start_recording("temp_object_detection.avi", (frame.shape[1], frame.shape[0]))
    start_time = time.time()

    while time.time() - start_time < 5:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        detector.detect_async(mp_image, time.time_ns() // 1_000_000)

        if detection_result_list:
            for detection in detection_result_list[0].detections:
                bbox = detection.bounding_box
                start_point = bbox.origin_x, bbox.origin_y
                end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
                cv2.rectangle(frame, start_point, end_point, (0, 165, 255), 3)

                category = detection.categories[0]
                cv2.putText(frame,
                           f'{category.category_name} ({round(category.score, 2)})',
                           (bbox.origin_x + 10, bbox.origin_y + 30),
                           cv2.FONT_HERSHEY_DUPLEX, 1, (0, 0, 0), 2)

            detection_result_list.clear()

        cv2.imshow('Object Detection', frame)
        out.write(frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    out.release()
    cap.release()
    cv2.destroyAllWindows()
    return "temp_object_detection.avi"

def generate_markdown(results, output_filename):
    """Generate markdown file with results"""
    with open(output_filename, 'w') as f:
        f.write("# Video Analytics Experiments Results\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for experiment, files in results.items():
            f.write(f"## {experiment}\n\n")
            for file in files:
                if file.endswith('.png'):
                    f.write(f"![{experiment}]({file})\n\n")
                elif file.endswith('.avi'):
                    f.write(f"Video recording saved as: [{file}]({file})\n\n")

def main():
    # Create results directory
    results_dir = "experiment_results"
    ensure_directory(results_dir)

    # Dictionary to store results
    results = {}

    # Run experiments
    experiments = [
        ("Optical Flow", run_optical_flow),
        ("Hand Landmark Detection", run_hand_landmark),
        ("Hand Gesture Recognition", run_hand_gesture),
        ("Object Detection", run_object_detection)
    ]

    for name, func in experiments:
        print(f"\nRunning {name} experiment...")
        video_file = func()
        if video_file:
            # Take a screenshot from the video
            cap = cv2.VideoCapture(video_file)
            ret, frame = cap.read()
            if ret:
                screenshot_file = save_screenshot(frame, name.lower().replace(" ", "_"), results_dir)
                results[name] = [video_file, screenshot_file]
            cap.release()

    # Get custom filename from user
    output_filename = get_custom_filename()
    
    # Generate markdown file
    generate_markdown(results, output_filename)
    print(f"\nResults saved to {output_filename}")

if __name__ == "__main__":
    main() 