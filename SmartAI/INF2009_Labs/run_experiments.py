import os
import subprocess
import time
from datetime import datetime
import cv2
import numpy as np
import pyautogui
import signal
import sys

def signal_handler(sig, frame):
    print('\nGracefully exiting...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def create_directory(dir_name):
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

def save_screenshot(frame, filename, results_dir):
    filepath = os.path.join(results_dir, filename)
    cv2.imwrite(filepath, frame)
    print(f"Screenshot saved as {filepath}")
    return filepath

def run_and_capture(script_name, capture_duration=10, results_dir="results"):
    print(f"\nRunning {script_name}...")
    print("Press 'q' to move to the next experiment or Ctrl+C to exit")
    
    # Create results directory if it doesn't exist
    create_directory(results_dir)
    
    try:
        # Get the path to the virtual environment's Python
        venv_python = os.path.join("image", "Scripts", "python.exe")
        
        # Start the script using the virtual environment's Python
        process = subprocess.Popen([venv_python, f'Codes/{script_name}'])
        
        # Wait a few seconds for the windows to appear
        time.sleep(3)
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Take a screenshot using pyautogui
        try:
            time.sleep(2)
            # Capture the entire screen
            screenshot = pyautogui.screenshot()
            # Convert to numpy array for OpenCV
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Save the screenshot
            filename = f"{script_name.replace('.py', '')}_{timestamp}.png"
            save_screenshot(frame, filename, results_dir)
            
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
        
        # Wait for specified duration or until user presses 'q'
        start_time = time.time()
        while time.time() - start_time < capture_duration:
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            time.sleep(0.1)
            
    except Exception as e:
        print(f"Error running {script_name}: {e}")
    finally:
        # Clean up
        try:
            process.terminate()
            process.wait(timeout=3)
        except:
            try:
                process.kill()
            except:
                pass
        
        # Close any remaining OpenCV windows
        cv2.destroyAllWindows()

def generate_markdown_report(results_dir="results"):
    report = """# Image Analytics Lab Results

## Environment Setup
- Virtual environment 'image' created and activated
- Required packages installed:
  - opencv-python
  - scikit-image
  - mediapipe
  - pyautogui (for screenshots)

## Experiments and Results

### 1. Basic Color Segmentation
- This experiment demonstrates RGB color segmentation
- The code captures video from webcam and segments it into red, green, and blue components
"""
    
    # Add screenshots and descriptions for each experiment
    for filename in sorted(os.listdir(results_dir)):
        if filename.startswith("image_capture_display"):
            report += f"\n![Color Segmentation]({os.path.join(results_dir, filename)})\n"
            report += "- RGB color segmentation demonstration\n"
            report += "- Shows original image and its color components\n"
        elif filename.startswith("image_hog_feature"):
            report += "\n### 2. HOG Feature Extraction\n"
            report += "- This experiment demonstrates Histogram of Oriented Gradients (HOG)\n"
            report += "- HOG is used for edge detection and feature extraction\n"
            report += f"\n![HOG Features]({os.path.join(results_dir, filename)})\n"
            report += "- Left: Original image, Right: HOG visualization\n"
            report += "- Shows edge detection and feature patterns\n"
        elif filename.startswith("image_face_capture"):
            report += "\n### 3. Face Detection\n"
            report += "- This experiment shows real-time face detection using MediaPipe\n"
            report += f"\n![Face Detection]({os.path.join(results_dir, filename)})\n"
            report += "- Shows basic face detection capabilities\n"
        elif filename.startswith("image_live_facial_landmarks"):
            report += "\n### 4. Facial Landmarks Detection\n"
            report += "- This experiment demonstrates detailed facial landmark detection\n"
            report += "- Uses MediaPipe's Face Mesh for precise facial feature tracking\n"
            report += f"\n![Facial Landmarks]({os.path.join(results_dir, filename)})\n"
            report += "- Shows detailed facial mesh and contours\n"
            report += "- Tracks 468 facial landmarks in real-time\n"
    
    # Write the report
    with open("lab_results.md", "w") as f:
        f.write(report)
    print("\nLab results have been documented in lab_results.md")

def main():
    # Ensure we're in the virtual environment
    if not os.environ.get('VIRTUAL_ENV'):
        print("Please activate the 'image' virtual environment first!")
        return

    # Create results directory
    results_dir = "results"
    create_directory(results_dir)

    # List of scripts to run
    scripts = [
        "image_capture_display.py",
        "image_hog_feature.py",
        "image_face_capture.py",
        "image_live_facial_landmarks.py"
    ]

    print("\nStarting Image Analytics Lab Experiments")
    print("=======================================")
    print("Each experiment will run for 10 seconds")
    print("Press 'q' to move to the next experiment")
    print("Press Ctrl+C to exit the program")
    print("=======================================\n")

    # Run each script and capture results
    for script in scripts:
        run_and_capture(script, capture_duration=10, results_dir=results_dir)

    # Generate markdown report
    generate_markdown_report(results_dir)
    print("\nAll experiments completed!")

if __name__ == "__main__":
    main() 