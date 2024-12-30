# Brightness Controller

A Python application that automatically adjusts screen brightness based on camera input or screen content.

## Features

- Camera-based brightness control
- Screen content-based brightness control
- Smooth brightness transitions
- User-friendly GUI interface
- Configurable minimum and maximum brightness levels

## Requirements

- Python 3.7+
- Webcam (for camera-based control)
- Windows OS (screen brightness control is primarily tested on Windows)

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

## Configuration

You can modify the following parameters in `brightness_controller.py`:
- `min_brightness`: Minimum allowed brightness level (default: 15)
- `max_brightness`: Maximum allowed brightness level (default: 100)
- `history_size`: Size of brightness history buffer for smoothing (default: 30)
- `transition_steps`: Number of steps for smooth brightness transition (default: 5)
- `transition_delay`: Delay between transition steps in seconds (default: 0.05)

## License

MIT License 