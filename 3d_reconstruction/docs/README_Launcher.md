# 3D Reconstruction Launcher

This document describes the new unified launcher system that replaces the old batch files with a modern Tkinter GUI.

## Overview

The new launcher system provides a single, user-friendly interface for accessing all 3D reconstruction features. It replaces the old batch files (`setup_and_run.bat`, `start_live_reconstruction.bat`, `start_photo_reconstruction.bat`) with a unified GUI launcher.

## Quick Start

### Launch the Application

```bash
# Windows - Double click or run from command line
launcher.bat

# Or directly with Python
python src/launcher_gui.py
```

## Features

### 📹 Live Camera Reconstruction
- Real-time 3D reconstruction from camera feed
- Press SPACE to capture keyframes
- Press R to start reconstruction
- Press S to save results
- Press ESC to exit

### 📸 Photo Upload Reconstruction
- Upload multiple photos for reconstruction
- Automatic photo processing and alignment
- Interactive 3D visualization
- Save point clouds and meshes

### 🎯 Advanced Photo Positioning (Coming Soon)
- Manual photo positioning in 3D space
- Custom camera pose estimation
- Advanced reconstruction options

### 🔧 Setup Dependencies
- Install required Python packages
- Check system compatibility
- Troubleshoot installation issues

## File Structure

```
3d_reconstruction/
├── launcher.bat                    # Main launcher (replaces old batch files)
├── src/
│   ├── launcher_gui.py            # Main launcher GUI
│   ├── simple_photo_positioning_gui.py  # Simple photo positioning
│   ├── advanced_photo_reconstruction_gui.py  # Advanced positioning (future)
│   ├── live_reconstruction_app.py # Live camera reconstruction
│   ├── photo_upload_processor.py  # Photo upload reconstruction
│   └── reconstruction_engine.py   # Core reconstruction engine
├── setup_and_run.bat              # Legacy - kept for reference
├── start_live_reconstruction.bat  # Legacy - kept for reference
├── start_photo_reconstruction.bat # Legacy - kept for reference
└── requirements.txt               # Python dependencies
```

## Migration from Old System

### Old Way (Batch Files)
```bash
# Setup and run live reconstruction
setup_and_run.bat

# Or run live reconstruction directly
start_live_reconstruction.bat

# Or run photo reconstruction
start_photo_reconstruction.bat
```

### New Way (Unified Launcher)
```bash
# Single launcher for everything
launcher.bat
```

Then use the GUI to:
1. Choose your reconstruction method
2. Let the launcher handle dependencies
3. Launch the appropriate application

## Benefits of the New System

### ✅ Unified Interface
- Single entry point for all features
- Consistent user experience
- No need to remember multiple batch files

### ✅ Better Error Handling
- Automatic dependency checking
- Clear error messages
- Built-in troubleshooting

### ✅ Modern GUI
- Professional appearance
- Intuitive navigation
- Progress indicators

### ✅ Extensible
- Easy to add new features
- Modular design
- Future-proof architecture

## Troubleshooting

### Launcher Won't Start
1. Ensure Python 3.7+ is installed
2. Check that Python is in your PATH
3. Run `python --version` to verify

### Dependencies Missing
1. Click "Setup Dependencies" in the launcher
2. Or run manually: `pip install -r requirements.txt`
3. Check TROUBLESHOOTING.md for detailed help

### Application Won't Launch
1. Check the status message in the launcher
2. Ensure all dependencies are installed
3. Try running the application directly from src/ directory

## Advanced Usage

### Direct Application Launch
If you prefer to launch applications directly:

```bash
# Live reconstruction
python src/live_reconstruction_app.py

# Photo upload
python src/photo_upload_processor.py

# Simple photo positioning
python src/simple_photo_positioning_gui.py
```

### Command Line Options
Some applications support command line options:

```bash
# Live reconstruction with custom camera
python src/live_reconstruction_app.py --camera-id 1 --width 1280 --height 720

# Photo upload with specific output directory
python src/photo_upload_processor.py --output-dir ./my_reconstruction
```

## Future Enhancements

### Planned Features
- Advanced photo positioning GUI
- Batch processing capabilities
- Integration with external 3D viewers
- Cloud-based reconstruction options

### Customization
- Theme selection
- Custom keyboard shortcuts
- Plugin system for extensions

## Support

For issues and questions:
1. Check the launcher status messages
2. Review the application-specific documentation
3. See TROUBLESHOOTING.md for common issues
4. Check the main README.md for general information

## Legacy Support

The old batch files are still available for:
- Advanced users who prefer command line
- Automated scripts and workflows
- Backward compatibility

However, the new launcher is recommended for most users. 