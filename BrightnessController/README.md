# Brightness Controller

A Python application that automatically adjusts screen brightness based on camera input or screen content, with advanced features including human detection and eye health monitoring.

## Features

- **Camera-based brightness control**: Adjusts brightness based on ambient light detected by your webcam
- **Screen content-based brightness control**: Adjusts brightness based on the average brightness of your screen content
- **Human Detection**: Automatically reduces screen brightness to 0% when no human is detected, helping save energy and reduce eye strain
- **Eye Health Monitoring**: Tracks brightness levels and provides health recommendations
- **Smooth brightness transitions**: Prevents jarring brightness changes
- **User-friendly GUI interface**: Easy-to-use interface with real-time status updates
- **Configurable settings**: Adjustable minimum and maximum brightness levels
- **Session Statistics**: Track your brightness usage and eye health metrics

## Human Detection Feature

The human detection feature uses computer vision to detect human faces through your webcam:

- **Automatic Power Saving**: When no human is detected, screen brightness automatically drops to 0%
- **Smart Detection**: Uses OpenCV's Haar cascade classifier for reliable face detection
- **Distance-Based Detection**: Differentiates between primary user (close to camera) and distant people
- **Reduced False Positives**: Implements a history buffer to minimize false detections
- **Real-time Status**: GUI shows current human detection status
- **Configurable**: Can be enabled/disabled through the GUI
- **Calibration Support**: Test tool allows retraining and calibration for optimal detection

### How Human Detection Works

1. The camera continuously monitors for human faces
2. When a face is detected, normal brightness control resumes
3. When no face is detected for several consecutive frames, brightness drops to 0%
4. The system uses a detection history buffer to reduce false positives/negatives
5. **Distance Detection**: Only faces close to the camera are considered as the primary user
6. **Background Filtering**: People walking by or sitting far away are ignored

### Tips for Best Human Detection Results

- Ensure good lighting on your face
- Position yourself clearly in front of the camera
- Keep the camera unobstructed
- Enable "Distance Detection" to ignore people in the background
- Use the test tool (`test.py`) to calibrate distance detection for your setup
- Works best in camera-based mode
- May not work perfectly in all lighting conditions

### Testing and Calibration

Use the test tool to calibrate and test human detection:

**Command Line Interface:**
```bash
python test.py
```

**Graphical User Interface (Recommended):**
```bash
python test_gui.py
# or
python run_test_gui.py
```

The test tools provide:
- Real-time visualization of face detection
- Distance-based detection testing
- Calibration mode for optimal threshold adjustment
- Interactive controls for testing different scenarios
- **GUI Features:**
  - Live camera feed with detection overlays
  - Real-time status updates
  - Easy-to-use calibration controls
  - Activity logging
  - Threshold management
  - Detection settings toggles

## Requirements

- Python 3.7+
- Webcam (for camera-based control and human detection)
- Windows OS (screen brightness control is primarily tested on Windows)
- OpenCV (included in requirements.txt)

### Additional Requirements for Test GUI

For the graphical test interface, install additional dependencies:
```bash
pip install -r requirements_test_gui.txt
```

## Installation

1. Clone this repository:

```bash
git clone https://github.com/ljh0311/PythonTools.git
cd PythonTools/BrightnessController
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

## Usage

Run the GUI application:

```bash
python brightness_gui.py
```

The application provides two modes:

1. **Camera-based**: Adjusts screen brightness based on ambient light detected by your webcam
2. **Screen Content-based**: Adjusts brightness based on the average brightness of your screen content

### Using Human Detection

1. Select "Camera-based" mode
2. Check "Enable Human Detection" in the Human Detection section
3. Click "Start" to begin
4. The "Human Present" indicator will show your detection status
5. When you leave the camera view, brightness will automatically drop to 0%
6. When you return, normal brightness control will resume

## Configuration

You can modify the following parameters in `brightness_controller.py`:

- `min_brightness`: Minimum allowed brightness level (default: 15)
- `max_brightness`: Maximum allowed brightness level (default: 100)
- `history_size`: Size of brightness history buffer for smoothing (default: 30)
- `transition_steps`: Number of steps for smooth brightness transition (default: 5)
- `transition_delay`: Delay between transition steps in seconds (default: 0.05)
- `enable_human_detection`: Whether to enable human detection (default: True)
- `enable_distance_detection`: Whether to differentiate between close and distant people (default: True)
- `detection_history_size`: Number of consecutive detections to confirm human presence (default: 5)

## Eye Health Features

The application includes comprehensive eye health monitoring:

- **Brightness Classification**: Categorizes brightness levels from "Too Dark" to "Too Bright"
- **Health Recommendations**: Provides specific advice for each brightness category
- **Unhealthy Time Tracking**: Monitors time spent in non-optimal brightness ranges
- **Session Statistics**: Tracks average brightness, health status, and recommendations
- **20-20-20 Rule Reminders**: Encourages regular eye breaks

## License

MIT License
