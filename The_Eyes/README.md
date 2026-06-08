# The Eyes - Home Security Surveillance System

A Python-based home security application that provides multi-camera surveillance with motion detection, recording, and alerting capabilities.

## Overview

"The Eyes" is a comprehensive home security surveillance system that allows you to monitor multiple cameras simultaneously. It provides real-time monitoring, motion detection, automatic recording, and alert notifications to help keep your home secure.

## Features

### Core Features

- **Multi-Camera Monitoring**: View multiple camera feeds simultaneously in a customizable grid layout
- **Dynamic Layout System**: Auto-adapting grid layouts (1x1, 2x2, 3x3, 4x4) or custom arrangements
- **Camera Management**: Easy camera discovery, configuration, and management
- **Real-Time Display**: Low-latency video streaming with FPS monitoring

### Security Features

- **Motion Detection**: Advanced background subtraction-based motion detection with configurable sensitivity
- **Automatic Recording**: Motion-triggered or continuous video recording with automatic file management
- **Alert System**: Visual and audio alerts for motion detection and camera offline events
- **Detection Zones**: Define specific areas for motion detection
- **Recording Management**: Automatic file splitting, size limits, and retention policies

### Technical Features

- **Performance Optimized**: Multi-threaded frame capture and efficient rendering
- **Multiple Camera Types**: Support for webcams, IP cameras (RTSP/HTTP), and Intel RealSense cameras
- **Network Camera Discovery**: Automatic scanning for network cameras
- **Snapshot Capture**: Save individual frames with timestamps
- **Fullscreen View**: Click any camera to view in fullscreen mode

## Requirements

- Python 3.8+
- One or more cameras (webcams, IP cameras, or Intel RealSense)
- OpenCV for camera access and video processing
- Windows/Linux/MacOS support

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/The_Eyes.git
cd The_Eyes
```

1. Create a virtual environment (recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Configure the application:
   - Edit `config/config.json` to configure cameras, motion detection, and recording settings
   - Or use the GUI to scan and add cameras automatically

## Project Structure

```
The_Eyes/
├── config/             # Configuration files
│   ├── config.json     # Main application configuration
│   └── scenes.json     # Camera scene configurations
├── recordings/         # Video recordings (created automatically)
├── screenshots/        # Snapshot images (created automatically)
├── logs/               # Application logs
├── src/                # Source code
│   ├── camera/         # Camera management and interfaces
│   │   ├── camera_manager.py      # Main camera manager
│   │   └── camera_scanner_gui.py  # Network camera scanner
│   ├── gui/            # GUI components
│   │   ├── components/ # Reusable UI components
│   │   │   └── camera_view.py     # Camera view widget
│   │   └── dialogs/    # Dialog windows
│   ├── security/       # Security features
│   │   ├── motion_detector.py     # Motion detection
│   │   ├── recorder.py            # Video recording
│   │   └── alert_manager.py       # Alert management
│   ├── utils/          # Utility functions
│   └── gui_app.py      # Main GUI application
└── scripts/            # Utility scripts
```

## Usage

### Starting the Application

Run the GUI application:

```bash
python src/run_gui.py
```

Or use the batch script (Windows):

```bash
scripts\run_the_eyes_gui.bat
```

### Basic Workflow

1. **Scan for Cameras**: Click "Scan for Cameras" to automatically detect connected webcams and network cameras
2. **View Camera Feeds**: Cameras will automatically appear in the monitoring tab with a grid layout
3. **Configure Layout**: Use the layout dropdown to change how cameras are arranged (auto, 1x1, 2x2, 3x3, 4x4, etc.)
4. **Enable Security Features**:
   - Go to Settings tab to enable motion detection
   - Configure recording settings (motion-triggered or continuous)
   - Set up alert preferences

### Camera Controls

- **Fullscreen**: Click the 🔍 button or double-click a camera view
- **Snapshot**: Click the 📷 button to save a screenshot
- **Settings**: Click the ⚙️ button to configure individual camera settings

### Motion Detection

1. Enable motion detection in Settings
2. Adjust sensitivity and minimum detection area
3. Optionally define detection zones to monitor specific areas
4. Motion events will trigger alerts and automatic recording (if enabled)

### Recording

- **Motion-Triggered**: Automatically starts recording when motion is detected
- **Continuous**: Records all camera feeds continuously
- Recordings are saved to the `recordings/` directory
- Files are automatically split when size or duration limits are reached

## Configuration

Edit `config/config.json` to customize:

- **Cameras**: Camera configurations and settings
- **Motion Detection**: Sensitivity, detection zones, methods
- **Recording**: Output directory, codec, file size limits, retention
- **Alerts**: Alert types, sound/visual preferences, log file location
- **Display**: Layout preferences, FPS display, resolution settings

## Troubleshooting

### Cameras Not Detected

- Ensure cameras are properly connected
- Check camera permissions (especially on Linux/Mac)
- Try running the camera scanner tool: `python src/camera/camera_scanner_gui.py`

### High CPU Usage

- Reduce the number of visible cameras
- Lower camera resolution in settings
- Disable motion detection if not needed
- Reduce FPS limit in system settings

### Recording Issues

- Check available disk space
- Verify write permissions for the recordings directory
- Try a different video codec if playback issues occur

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
