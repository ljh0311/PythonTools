# INF2009 Labs GUI Launcher

## Overview

The consolidated GUI launcher provides a user-friendly interface to run all INF2009 edge computing lab experiments without needing to manually execute Python scripts or modify code.

## Features

### 🎯 Unified Interface
- Single application for all three modules
- Tabbed interface for easy navigation
- Real-time output display
- Progress indicators

### 🔬 Experiment Management
- **Deep Learning on Edge**: Run MobileNet experiments with quantization options
- **Image Analytics**: Execute image processing experiments with configurable duration
- **Video Analytics**: Run video processing experiments with screenshot capture
- **Results Viewer**: Browse results and generate reports

### ⚙️ Configuration Options
- Toggle quantization on/off
- Enable/disable predictions
- Set experiment duration
- Automatic screenshot capture
- Custom output directories

## Quick Start

### Windows
```bash
run_launcher.bat
```

### Linux/Mac
```bash
chmod +x run_launcher.sh
./run_launcher.sh
```

### Direct Python
```bash
python launcher.py
# or
python3 launcher.py
```

## Requirements

### Core Dependencies
- Python 3.7+
- tkinter (usually included with Python)

### Optional Dependencies
- `pyautogui` - For automatic screenshot capture
- `torch` - For Deep Learning experiments
- `opencv-python` - For Image/Video experiments
- `mediapipe` - For advanced video analytics

Install all dependencies:
```bash
pip install -r requirements.txt
pip install pyautogui  # Optional, for screenshots
```

## Usage Guide

### 1. Deep Learning on Edge Tab

**Available Experiments:**
- Basic MobileNet - Standard MobileNetV2 inference
- Quantized MobileNet - Optimized quantized version
- MobileNet with Predictions - Shows top 10 class predictions

**Options:**
- **Enable Quantization**: Toggle quantization on/off
- **Show Predictions**: Display real-time class predictions

**How to Run:**
1. Select an experiment from the radio buttons
2. Configure options (quantization, predictions)
3. Click "Run Experiment"
4. Monitor output in the right panel
5. Click "Stop" to terminate early

### 2. Image Analytics Tab

**Available Experiments:**
- Color Segmentation - RGB color channel separation
- HOG Features - Histogram of Oriented Gradients
- Face Detection - MediaPipe face detection
- Facial Landmarks - Detailed facial feature tracking
- Human Capture (OpenCV) - Haar cascade detection
- Human Capture (MediaPipe) - MediaPipe detection

**Options:**
- **Capture Screenshot**: Automatically save experiment screenshots
- **Duration**: Set experiment runtime (5-60 seconds)

**How to Run:**
1. Select an experiment
2. Set duration and screenshot options
3. Click "Run Experiment"
4. View output and captured screenshots

### 3. Video Analytics Tab

**Available Experiments:**
- Optical Flow - Motion tracking using Lucas-Kanade/Farneback
- Hand Landmark Detection - 21-point hand tracking
- Hand Gesture Recognition - Real-time gesture classification
- Object Detection - EfficientDet object detection

**Options:**
- **Capture Screenshot**: Save experiment screenshots
- **Duration**: Set experiment runtime (5-60 seconds)

**How to Run:**
1. Select an experiment
2. Configure options
3. Click "Run Experiment"
4. Monitor progress and view results

### 4. Results & Reports Tab

**Features:**
- View results from all modules
- Browse experiment outputs
- Generate combined lab reports
- Open results folders

**Actions:**
- **View Results**: Browse files for each module
- **Generate Report**: Create combined markdown report
- **Open Folder**: Open results directory in file explorer

## Output Structure

Results are organized in the following structure:

```
results/
├── dl_on_edge/          # Deep Learning experiment results
│   ├── fps_measurements.txt
│   └── quantization_results.png
├── image_analytics/      # Image experiment screenshots
│   ├── image_capture_display_*.png
│   ├── image_hog_feature_*.png
│   └── ...
└── video_analytics/      # Video experiment screenshots
    ├── optical_flow_*.png
    ├── hand_gesture_*.png
    └── ...
```

## Troubleshooting

### Launcher won't start
- Ensure Python 3.7+ is installed
- Check that tkinter is available: `python -m tkinter`
- On Linux, install tkinter: `sudo apt-get install python3-tk`

### Experiments fail to run
- Check that required packages are installed
- Verify camera/webcam is connected (for image/video experiments)
- Check output panel for specific error messages
- Ensure you're in the correct directory with `Codes/` folder

### Screenshots not capturing
- Install pyautogui: `pip install pyautogui`
- Ensure experiment window is visible
- Check file permissions for results directory

### Camera not detected
- Verify camera is connected
- Check camera permissions
- Some experiments will use test images if camera unavailable

## Tips

1. **Start Simple**: Begin with basic experiments before trying advanced features
2. **Monitor Resources**: Some experiments are resource-intensive; monitor system performance
3. **Save Results**: Use the Results tab to review and save important outputs
4. **Read Output**: The output panels provide valuable debugging information
5. **Stop Early**: Use the Stop button if experiments hang or take too long

## Keyboard Shortcuts

- `Ctrl+C` - Stop current experiment (if supported)
- `Tab` - Navigate between tabs
- `Enter` - Activate selected button

## Advanced Usage

### Running from Command Line

You can still run individual scripts directly:

```bash
# Deep Learning
python Codes/mobile_net.py

# Image Analytics
python Codes/image_capture_display.py

# Video Analytics
python Codes/optical_flow.py
```

### Custom Configuration

Modify `launcher.py` to:
- Change default experiment durations
- Add new experiments
- Customize output directories
- Modify screenshot settings

## Support

For issues or questions:
1. Check the main README.md for module-specific documentation
2. Review experiment code in `Codes/` directory
3. Check output panels for error messages
4. Verify all dependencies are installed

---

**Happy Experimenting! 🚀**
