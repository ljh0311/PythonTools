# AI Smart Camera System

An advanced AI-powered camera system that utilizes computer vision and machine learning techniques to improve image and video capture quality, inspired by INF2009 Image and Video Analytics projects.

## Features

### 🎯 AI-Powered Image Enhancement

- **Automatic Quality Analysis**: Analyzes brightness, contrast, and noise levels
- **Smart Denoising**: Uses Non-local Means Denoising for noise reduction
- **Intelligent Sharpening**: Applies unsharp masking for crisp images
- **Color Correction**: Automatic white balance and saturation enhancement
- **Exposure Correction**: Gamma correction for optimal brightness
- **Super Resolution**: Upscaling with intelligent interpolation

### 🔍 Advanced Detection Systems

- **Face Detection & Analysis**: Detects faces and assesses quality metrics
- **Object Detection**: YOLO-based object recognition with confidence scoring
- **Motion Detection**: Advanced motion tracking with history analysis
- **Smart AI Capture**: Automatically captures images when AI detects significant events
- **Event Classification**: Categorizes captures by detection type (face, object, motion)
- **Capture Sequences**: Captures multiple frames per event for better analysis
- **Rate Limiting**: Prevents excessive captures with configurable limits

### 📹 Smart Camera Detection & Selection

- **Automatic Camera Discovery**: Automatically detects all available cameras
- **Device Name Recognition**: Shows actual camera device names on Windows
- **Camera Preview**: Hover over camera buttons to see live preview
- **Detailed Information**: Resolution, FPS, and backend information
- **One-Click Selection**: Easy camera selection with visual feedback
- **Refresh Capability**: Re-detect cameras without restarting the application

### 🎛️ Enhanced User Interface

- **Modern GUI**: Intuitive tkinter-based interface with improved layout
- **Real-time Preview**: Live camera feed with enhancement overlay
- **Settings Control**: Adjustable camera parameters and AI settings
- **Status Monitoring**: FPS, detection status, and system health
- **Camera Management**: Visual camera selection with detailed information
- **Smart AI Capture Controls**: Configure auto-capture thresholds and limits
- **Storage Management**: Clean old captures and view storage statistics
- **Event Classification**: Organize captures by detection type

### Supported devices and multi-device UI

The GUI supports different layouts and input modes for:

- **Desktop/laptop**: Resizable window, configurable size and position (`GUI_CONFIG.window_size`, `min_window_size`). Window is centered and capped to screen.
- **Raspberry Pi (touchscreen)**: Deployment UI (`--device 1`) with screen-driven or configurable size, optional fullscreen (`deployment_fullscreen`), modern theme, and touch-friendly button targets (min ~48px).
- **Raspberry Pi (buttons/DPAD)**: Keyboard and DPAD navigation when `enable_dpad_navigation` is true (default): Left/Right (or Up/Down) move focus, Space/Enter activate, Escape clear focus. Use with hardware buttons via GPIO/evdev mapping to key events.

**Mobile (iOS/Android)**: The current app is Python/tkinter and does not run natively on phones. For an iOS/Android version, see [docs/MOBILE_STRATEGY.md](docs/MOBILE_STRATEGY.md) for options (Kivy/BeeWare, web PWA, or native app with API).

### Travel-friendly setup (phone as the lens, laptop as the app)

Many travelers still **carry a laptop** or a **small Windows tablet / mini PC**. SmartCam runs there; your phone can act only as the **camera device** the PC sees:

- **iPhone + Mac**: [Continuity Camera](https://support.apple.com/guide/mac-help/use-iphone-as-a-webcam-mchl77879b8f/mac) exposes the phone as a webcam to macOS apps — SmartCam then uses it like any other UVC source (platform dependent; Apple documents this flow).
- **Android / iPhone + Windows**: use a **USB webcam mode** app or a **Wi‑Fi IP camera** app the vendor documents for PC use; quality and latency vary — prefer **USB** when you need stable preview on a trip.
- **Dedicated USB webcam** or **action cam in UVC mode** is still the lowest-friction option on Windows.

The desktop GUI includes **Quick mode** presets (**Trip (simple)**, **Scenic (stills)**, **Balanced**, **Crowd-aware**) to reduce tuning before you drive, and a **Privacy & saves** button that explains what is written under your captures folder and how overlays / auto-capture behave.

## Installation

### Prerequisites

- Python 3.8 or higher
- Webcam or camera device
- Sufficient storage space for captures

### Install tiers (avoid a “split experience”)

SmartCam deliberately splits **lightweight core** vs **heavy AI** so a quick `pip install` can succeed on modest hardware. The tradeoff is: **README “AI features” need the second tier**, or those paths run in a reduced mode.

| Tier | Command | What you get |
|------|---------|----------------|
| **Lite (core)** | `pip install -r requirements.txt` | Camera, preview, OpenCV-heavy paths, Windows camera-name helpers. YOLO / full object stack **may be absent** if `torch` / `ultralytics` are not installed. |
| **Full AI** | `pip install -r requirements.txt -r requirements-ai.txt` | Adds `torch`, `torchvision`, `mediapipe`, `ultralytics`, `tensorflow`, etc., as listed in `requirements-ai.txt`. Use when you want the advertised detection / classification stack. |
| **Raspberry Pi** | `pip install -r requirements-rpi.txt` | Pi-oriented minimal set (see that file). |

On startup, the GUI launcher prints an **install profile banner** (Lite vs Full AI) so you can see which tier is active. To hide it (e.g. in scripts), set `SMARTCAM_QUIET_INSTALL_BANNER=1`.

If PyTorch fails on Windows, see `utils/fix_pytorch_installation.py` for a guided CPU/CUDA reinstall.

### Key dependencies (by tier)

**Core (`requirements.txt`)**

- `opencv-python`, `numpy`, `Pillow` — capture, preview, image pipeline
- Windows: `pywin32`, `WMI`, `comtypes` — better camera device names

**Full AI (`requirements-ai.txt`, optional)**

- `torch` / `torchvision` — deep learning runtime used by YOLO-style loading in `main.py`
- `mediapipe` — face / vision helpers where enabled
- `ultralytics` — YOLO object detection stack
- `tensorflow`, `scikit-learn`, `matplotlib`, `opencv-contrib-python` — as pulled in by that file

### Performance (laptops, warm cars, long sessions)

Continuous preview + detection is **CPU/GPU intensive**; on a laptop in a hot environment the machine may **thermal-throttle**, which lowers FPS and can feel like “the app got slow.” That is largely a hardware thermals + workload issue, not a single SmartCam bug.

Practical mitigations:

- Prefer **AC power** on long drives; avoid soft surfaces that block vents.
- In `gui_app` / camera profiles, use **lower preview resolution**, **frame skip**, and fewer simultaneous detectors when you do not need them (see `processing_profiles.py` and `GUI_CONFIG` in `config/smartcam_settings.json`).
- Close other heavy apps while recording or using auto-capture.

### Auto-capture and trust

**Smart AI Capture** can save images you did not consciously press the shutter for. That is useful for “never miss the moment” but increases **false positives** (motion, pets, passing cars, flicker).

Mitigations built into the product direction:

- **Cooldown**, **max captures per minute**, and **sequence length** limit runaway disk use.
- Review the **captures** folder and use **Storage cleanup** / **Storage stats** before a trip ends.

The desktop UI caption under **Auto Capture** reminds you to tune limits and review captures regularly.

### Windows-Specific Dependencies (Optional)

For enhanced camera device name detection on Windows:

- `pywin32`: Windows API access
- `WMI`: Windows Management Instrumentation
- `comtypes`: COM interface support

## Usage

### Command Line Interface

```bash
python main.py
```

### GUI Application

```bash
python launch_smartcam.py
# Or: python gui_app.py
```

- `--device 1`: Deployment UI (touch-friendly, portrait-style; for RPi touchscreen).
- `--device 2`: PC UI (full desktop layout).
- Window size, deployment fullscreen, and DPAD navigation are controlled via `config/smartcam_settings.json` under `GUI_CONFIG` (see Supported devices above).

### Camera Detection Test

```bash
python test_camera_detection.py
```

### Basic Usage

1. **Launch Application**: Start the GUI application
2. **Camera Detection**: Cameras are automatically detected on startup
3. **Select Camera**: Click on a camera button to select it
4. **Preview Camera**: Hover over camera buttons to see live preview
5. **Initialize Camera**: Click "Initialize Selected Camera" to start
6. **Configure Settings**: Adjust enhancement and detection parameters
7. **Start Capture**: Begin real-time processing
8. **Capture Images**: Take high-quality photos with AI enhancement
9. **Record Videos**: Create enhanced video recordings
10. **Monitor Events**: View automatically captured significant events

### Camera Selection Features

- **Automatic Detection**: Scans for all available cameras (up to 10 by default)
- **Device Names**: Shows actual camera names on Windows systems
- **Status Indicators**: Visual feedback for available/unavailable cameras
- **Error Information**: Detailed error messages for problematic cameras
- **Refresh Button**: Re-detect cameras without restarting
- **Preview on Hover**: See live camera feed when hovering over buttons

## Configuration

### Camera Settings

```python
capture_settings = {
    'resolution': (1920, 1080),
    'fps': 30,
    'quality': 95,
    'auto_focus': True,
    'exposure': 'auto',
    'auto_enhancement': True,
    'enhancement_type': 'auto'
}
```

### Detection Settings

```python
detection_settings = {
    'confidence_threshold': 0.5,
    'nms_threshold': 0.4,
    'motion_sensitivity': 0.3,
    'face_recognition_enabled': True,
    'object_detection_enabled': True,
    'motion_detection_enabled': True,
    'quality_enhancement_enabled': True
}
```

### Smart AI Capture Settings

```python
ai_capture_settings = {
    'auto_capture_enabled': True,
    'capture_cooldown_seconds': 5,
    'face_capture_threshold': 0.6,
    'object_capture_threshold': 0.7,
    'motion_capture_threshold': 0.5,
    'max_captures_per_minute': 12,
    'capture_sequence_count': 3,
    'capture_sequence_interval': 0.5,
    'save_detection_overlay': True,
    'event_classification': True,
}
```

### Enhancement Types

- `auto`: Automatic detection and application of enhancements
- `denoise`: Noise reduction
- `sharpen`: Image sharpening
- `color_correction`: Color and white balance correction
- `exposure_correction`: Brightness and contrast adjustment
- `super_resolution`: Image upscaling

## File Structure

```
SmartCam/
├── main.py                    # Core smart camera system
├── gui_app.py                 # GUI application
├── launch_smartcam.py         # Application launcher
├── test_camera_detection.py   # Camera detection test script
├── requirements.txt           # Python dependencies
├── README.md                 # This file
├── gui/                      # GUI components
│   ├── components/           # GUI component modules
│   ├── dialogs/              # Dialog windows (error, progress, splash)
│   ├── styles/               # Theme and styling
│   └── windows/              # Additional windows
├── utils/                    # Utility scripts and helpers
│   ├── error_handler.py      # Error handling utilities
│   ├── fix_pytorch_installation.py  # PyTorch fix script
│   ├── fix_yolo_loading.py   # YOLO loading fix script
│   ├── performance_optimizer.py  # Performance optimization
│   ├── optimized_camera_settings.py  # Camera settings utilities
│   ├── smartCap.py           # Auto-capture utilities
│   └── demo.py               # Demo script
├── config/                   # Configuration files
│   ├── settings.py           # Settings management
│   └── smartcam_settings.json  # Settings file
├── models/                   # AI model files (optional)
└── captures/                 # Output directory
    ├── images/               # Enhanced images and AI captures
    ├── videos/               # Enhanced videos
    ├── events/               # AI event captures with classification
    │   ├── face_detection_*/ # Face detection events
    │   ├── object_*/         # Object detection events
    │   └── motion_detection_*/ # Motion detection events
    └── enhanced/             # Additional enhanced content
```

## Smart AI Capture System

### Features

- **Automatic Event Detection**: Captures images when AI detects faces, objects, or motion
- **Configurable Thresholds**: Adjust confidence levels for different detection types
- **Rate Limiting**: Prevents excessive captures with cooldown periods and per-minute limits
- **Event Classification**: Organizes captures by detection type (face, object, motion)
- **Capture Sequences**: Captures multiple frames per event for better analysis
- **Detection Overlays**: Saves frames with bounding boxes and labels drawn

### Usage

1. Enable "Auto Capture" in the AI Settings tab
2. Configure capture thresholds and limits
3. Start capture and let the AI automatically capture significant events
4. View organized captures in the `captures/events/` directory

## Storage Management System

### Features

- **Smart Cleanup**: Delete old captures based on age (1 hour to 1 week)
- **Storage Statistics**: View detailed storage usage and file counts
- **Preview Mode**: See what files would be deleted before actually deleting them
- **Safe Operation**: Validates file types and handles errors gracefully

### Usage

1. Click "Storage Cleanup" in the Actions tab
2. Select age threshold (1 hour to 1 week)
3. Preview files to be deleted
4. Execute cleanup to free storage space

## AI Techniques Used

### From INF2009 Image Analytics

- **Color Segmentation**: RGB color space analysis
- **Image Normalization**: Dynamic range adjustment
- **Feature Detection**: HOG features and facial landmarks
- **Quality Assessment**: Sharpness, brightness, and contrast metrics

### From INF2009 Video Analytics

- **Object Detection**: EfficientDet and YOLO models
- **Motion Analysis**: Frame differencing and contour detection
- **Real-time Processing**: Asynchronous detection pipelines
- **Gesture Recognition**: Hand landmark detection (extensible)

### Advanced Enhancements

- **CLAHE**: Contrast Limited Adaptive Histogram Equalization
- **Non-local Means**: Advanced denoising algorithm
- **Unsharp Masking**: Intelligent sharpening technique
- **Gamma Correction**: Exposure optimization

## Performance Optimization

### Multi-threading

- Separate capture and processing threads
- Queue-based frame management
- Non-blocking UI updates

### Memory Management

- Automatic frame dropping when queues are full
- Efficient image processing pipelines
- Smart storage cleanup

### GPU Acceleration

- PyTorch GPU support for object detection
- OpenCV GPU operations where available
- Optimized model loading

## Error Handling & Troubleshooting

### Comprehensive Error Handling

The application now includes a sophisticated error handling system:

- **Error Dialog System**: Uses `error_dialog.py` for detailed error reporting
- **Context-Aware Suggestions**: Provides specific recovery suggestions based on error type
- **Graceful Degradation**: Continues operation even when some components fail
- **Global Exception Handler**: Catches unhandled errors and displays them properly

### Common Issues & Solutions

1. **Camera Not Detected**
   - Run `python test_camera_detection.py` to diagnose camera issues
   - Check if camera is in use by other applications
   - Verify camera drivers are installed
   - Try refreshing cameras in the GUI
   - Check camera permissions in system settings

2. **Camera Selection Issues**
   - Ensure camera is not being used by another application
   - Check camera permissions in system settings
   - Try different camera backends (DirectShow, Media Foundation)
   - Restart the application if camera detection fails

3. **PyTorch Installation Errors (WinError 193)**
   - This error occurs when PyTorch is corrupted or has architecture mismatches
   - Run `python utils/fix_pytorch_installation.py` to diagnose and fix PyTorch issues
   - The application will continue to work without PyTorch, but object detection will be limited
   - Ensure you're using 64-bit Python (PyTorch requires 64-bit on Windows)
   - Reinstall PyTorch: `pip uninstall torch torchvision && pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu`

4. **YOLO Model Loading Errors**
   - Run `python utils/fix_yolo_loading.py` to automatically fix YOLO issues
   - The system will use a fallback object detection if YOLO fails
   - Check internet connection for model downloads
   - Verify PyTorch and ultralytics are properly installed

5. **Performance Issues**
   - Reduce resolution or FPS settings
   - Disable unnecessary detection features
   - Check available system resources
   - Close other applications to free up memory

6. **TensorFlow Warnings**
   - These are informational warnings and don't affect functionality
   - Can be suppressed by setting environment variables (done automatically)

7. **GUI Errors**
   - Check that Tkinter is properly installed
   - Try running in different display modes
   - Restart the application if GUI becomes unresponsive

### Error Logging

The system includes comprehensive logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Camera Detection Troubleshooting

```bash
# Test camera detection
python test_camera_detection.py

# Check OpenCV camera backends
python -c "import cv2; print(cv2.getBackendName())"
```

## Contributing

### Adding New Features

1. Extend the `ImageQualityEnhancer` class for new enhancement types
2. Add new detection methods to respective analyzer classes
3. Update GUI components for new controls
4. Include proper error handling and logging

### Model Integration

1. Place custom models in the `models/` directory
2. Update model loading logic in `_load_ai_models()`
3. Ensure compatibility with existing detection pipeline

### Camera Detection Improvements

1. Add support for additional camera backends
2. Implement camera device name detection for other platforms
3. Add camera capability detection (supported resolutions, formats)

## License

This project is for educational and research purposes, incorporating techniques from INF2009 Image and Video Analytics coursework.

## Acknowledgments

- INF2009 Image Analytics course materials
- INF2009 Video Analytics course materials
- OpenCV community for computer vision tools
- PyTorch and MediaPipe for AI frameworks
- YOLO and EfficientDet model developers

## Usage

### Basic Usage

```bash
# Run the GUI application
python gui_app.py

# Run with deployment mode (touch-friendly interface)
python gui_app.py -device 1

# Run with PC mode (full interface)
python gui_app.py -device 2
```

### Command Line Usage

```bash
# Test camera detection
python test_camera_detection.py

# Fix YOLO loading issues
python utils/fix_yolo_loading.py

# Fix PyTorch installation
python utils/fix_pytorch_installation.py

# Run demo
python utils/demo.py
```

### Smart AI Capture Example

```python
from main import SmartCamera

# Initialize camera
camera = SmartCamera(camera_id=0)

# Configure AI capture settings
ai_settings = {
    'auto_capture_enabled': True,
    'capture_cooldown_seconds': 5,
    'face_capture_threshold': 0.6,
    'object_capture_threshold': 0.7,
    'motion_capture_threshold': 0.5,
    'max_captures_per_minute': 12,
    'capture_sequence_count': 3,
    'save_detection_overlay': True,
}
camera.set_ai_capture_settings(ai_settings)

# Start capture - AI will automatically capture events
camera.start_capture()

# Let it run for a while...
import time
time.sleep(30)

# Stop capture
camera.stop_capture()

# Clean up old files (older than 24 hours)
stats = camera.cleanup_old_captures(age_hours=24)
print(f"Cleaned up {stats['files_deleted']} files")

# Get storage statistics
stats = camera.get_storage_stats()
print(f"Total storage: {stats['total_size_mb']:.2f} MB")

camera.cleanup()
```

## Future Enhancements

- [ ] Real-time super-resolution models
- [ ] Advanced face recognition with database
- [ ] Gesture and pose estimation
- [ ] Cloud-based processing capabilities
- [ ] Mobile app integration
- [ ] Advanced video stabilization
- [ ] Multi-camera support
- [ ] Custom model training interface
