# Human Detection Test GUI - User Guide

## Overview

The Human Detection Test GUI provides an intuitive interface for testing and calibrating the distance-based human detection system. It allows you to:

- Test human detection in real-time
- Calibrate distance thresholds for your specific environment
- Monitor detection performance
- Adjust detection settings
- View live camera feed with detection overlays

## Getting Started

### 1. Launch the Application

```bash
python test_gui.py
# or
python run_test_gui.py
```

### 2. Install Dependencies (if needed)

```bash
pip install -r requirements_test_gui.txt
```

## Interface Layout

The GUI is divided into several sections:

### Left Panel - Controls

#### Camera Controls
- **Start Camera**: Begin video capture and detection
- **Start Calibration**: Enter calibration mode for training

#### Detection Settings
- **Distance Detection**: Enable/disable distance-based detection
- **Strict Detection**: Use stricter detection parameters
- **Auto-Strict**: Automatically switch to strict mode when needed

#### Calibration Controls
- **Add Primary User Sample**: Add sample when you're close to camera
- **Add Distant Person Sample**: Add sample when someone is far from camera
- **Reset to Defaults**: Restore default threshold values

#### Status Display
- **Camera Status**: Shows if camera is active/inactive
- **Calibration Status**: Shows current calibration state
- **Samples Count**: Number of calibration samples collected

### Right Panel - Video and Information

#### Camera Feed
- Live video display with detection overlays
- Color-coded face detection:
  - 🟢 **Green**: Primary user (close to camera)
  - 🟠 **Orange**: Distant person (background)
  - ⚫ **Gray**: Face too small (ignored)

#### Detection Information
- **Primary User**: Shows if you're detected as the main user
- **Distant Person**: Shows if someone in background is detected
- **Faces Detected**: Total number of faces found

#### Current Thresholds
- Displays current detection thresholds
- Updates automatically after calibration

#### Activity Log
- Timestamped log of all activities
- Shows calibration progress and errors

### Bottom Panel - Help
- Quick usage instructions
- Step-by-step guidance

## How to Use

### Step 1: Start Testing
1. Click **"Start Camera"** to begin video capture
2. Position yourself in front of the camera
3. Observe detection results in real-time

### Step 2: Enable Distance Detection
1. Check **"Distance Detection"** checkbox
2. Notice how detection changes - only close faces are considered primary users
3. Background people should be ignored

### Step 3: Calibrate for Your Environment
1. Click **"Start Calibration"**
2. Position yourself at your typical working distance from camera
3. Click **"Add Primary User Sample"** several times
4. Move further away or have someone stand in background
5. Click **"Add Distant Person Sample"** several times
6. Click **"Stop Calibration"** when you have at least 5 samples

### Step 4: Test Calibration
1. Move around at different distances
2. Have others walk by in background
3. Verify that only you (close to camera) are detected as primary user
4. Background people should be ignored

## Understanding Detection Results

### Face Detection Colors
- **🟢 Green Rectangle**: Primary user detected (close to camera)
  - This face will trigger brightness control
  - Should be you at your normal working position
  
- **🟠 Orange Rectangle**: Distant person detected (background)
  - This face is ignored for brightness control
  - Prevents false triggers from people walking by
  
- **⚫ Gray Rectangle**: Face too small (ignored)
  - Face is too far away to matter
  - Completely ignored by the system

### Detection Status Indicators
- **✅ Detected**: Face found and classified
- **❌ Not Detected**: No face of that type found
- **Numbers**: Count of total faces detected

## Calibration Tips

### For Best Results
1. **Good Lighting**: Ensure your face is well-lit during calibration
2. **Clear View**: Keep camera unobstructed
3. **Multiple Samples**: Add at least 5-10 samples of each type
4. **Realistic Positions**: Use positions you'll actually be in during normal use
5. **Background Variation**: Include samples with different background conditions

### Sample Collection Strategy
1. **Primary User Samples**:
   - Normal working distance from camera
   - Slightly different angles and positions
   - Different lighting conditions
   
2. **Distant Person Samples**:
   - People standing/walking in background
   - Different distances from camera
   - Various positions in frame

### Troubleshooting Calibration
- **Too Sensitive**: System detects background people as primary users
  - Add more distant person samples
  - Increase primary user minimum threshold
  
- **Not Sensitive Enough**: System doesn't detect you when it should
  - Add more primary user samples
  - Decrease primary user minimum threshold
  
- **Unstable Detection**: Detection flickers on/off
  - Enable "Strict Detection"
  - Add more samples for better threshold calculation

## Advanced Features

### Detection Settings
- **Distance Detection**: Core feature for differentiating close vs. distant people
- **Strict Detection**: More conservative detection parameters
- **Auto-Strict**: Automatically switches to strict mode when needed

### Threshold Management
- **Automatic Calculation**: Thresholds calculated from your calibration samples
- **Manual Reset**: Restore default values if needed
- **Real-time Updates**: See threshold changes immediately

### Performance Monitoring
- **Live Logging**: All activities recorded with timestamps
- **Detection Statistics**: Real-time performance metrics
- **Error Reporting**: Clear error messages for troubleshooting

## Troubleshooting

### Common Issues

#### Camera Not Working
- Check webcam permissions
- Ensure no other application is using the camera
- Try restarting the application

#### Poor Detection Quality
- Improve lighting conditions
- Clean camera lens
- Ensure stable camera position
- Recalibrate with better samples

#### Calibration Fails
- Ensure at least 5 samples are collected
- Check that samples are diverse
- Verify camera is working properly
- Try resetting to defaults and recalibrating

#### GUI Freezes
- Check system resources
- Ensure camera is not stuck
- Restart application if needed

### Performance Tips
- **Frame Rate**: GUI runs at ~30 FPS for smooth experience
- **CPU Usage**: Detection processing is optimized for efficiency
- **Memory**: Video frames are processed efficiently to minimize memory usage

## Technical Details

### Detection Algorithm
- Uses OpenCV Haar cascade classifier
- Face size percentage calculation for distance estimation
- Statistical threshold calculation from calibration samples
- Real-time processing with minimal latency

### Threading Model
- Main GUI thread for user interface
- Separate video processing thread for camera operations
- Thread-safe updates using Tkinter's `after_idle`

### Camera Integration
- Supports multiple camera backends (DirectShow, V4L)
- Automatic camera detection and initialization
- Configurable resolution and frame rate

## Support

If you encounter issues:
1. Check the activity log for error messages
2. Verify all dependencies are installed
3. Ensure camera permissions are granted
4. Try resetting to default settings
5. Recalibrate with different samples

For additional help, refer to the main README.md file or check the console output for detailed error information.
