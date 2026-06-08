# 3D Reconstruction Suite - Basic Setup

A simplified 3D reconstruction application with a clean, basic GUI interface.

## Quick Start

1. **Install Python 3.7 or higher** if you haven't already
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Launch the application:**
   ```
   launcher.bat
   ```
   Or run directly:
   ```
   python src/basic_launcher_gui.py
   ```

## Features

### 📹 Live Camera Reconstruction
- Uses your computer's camera to capture images in real-time
- Automatically processes images to create a 3D model
- Best for small objects placed in front of the camera

### 📸 Photo Upload Reconstruction
- Upload multiple photos of an object from different angles
- Manually select photos and process them
- Best for larger objects or when you want more control

## Requirements

- Python 3.7 or higher
- Webcam (for live reconstruction)
- Good lighting conditions
- Stable camera position

## Dependencies

The main dependencies are:
- OpenCV (cv2) - for image processing
- NumPy - for numerical operations
- Open3D - for 3D reconstruction
- Tkinter - for the GUI (usually comes with Python)

## Project Structure

```
3d_reconstruction/
├── src/
│   ├── basic_launcher_gui.py      # Main launcher GUI
│   ├── live_reconstruction_app.py # Live camera reconstruction
│   ├── photo_upload_processor.py  # Photo upload reconstruction
│   ├── reconstruction_engine.py   # Core reconstruction logic
│   ├── live_camera_processor.py   # Camera processing
│   ├── photo_reconstruction_cli.py # CLI version
│   └── video_processor.py         # Video processing utilities
├── output/                        # Generated 3D models
├── launcher.bat                   # Windows launcher script
├── requirements.txt               # Python dependencies
└── README files                   # Documentation
```

## Usage Tips

1. **For Live Reconstruction:**
   - Ensure good lighting
   - Keep the object centered in the camera view
   - Move slowly around the object
   - Avoid reflective surfaces

2. **For Photo Upload:**
   - Take photos from different angles (at least 10-20 photos)
   - Ensure good lighting in all photos
   - Avoid motion blur
   - Include the entire object in each photo

## Troubleshooting

If you encounter issues:

1. **Check Python version:** `python --version`
2. **Verify dependencies:** `pip list`
3. **Check camera access:** Make sure your webcam is not being used by another application
4. **Check file permissions:** Ensure you have write access to the output directory

## Support

For detailed troubleshooting, see `TROUBLESHOOTING.md`
For specific feature documentation, see the individual README files. 