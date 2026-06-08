# 3D Reconstruction from Video and Photos

This project implements a modular pipeline for processing camera/video and photo sets with two explicit photo contracts:
- `panorama` mode: builds a 360 equirectangular panorama.
- `reconstruction` mode: builds a 3D point cloud/mesh (COLMAP-first, manual SfM fallback).

## Project Structure

```
3d_reconstruction/
├── src/                           # Source code
│   ├── live_reconstruction_app.py # Live camera reconstruction
│   ├── photo_upload_processor.py  # Photo upload and processing
│   ├── photo_reconstruction_cli.py # Command-line photo interface
│   ├── reconstruction_engine.py   # Core reconstruction engine
│   ├── live_camera_processor.py   # Live camera handling
│   └── video_processor.py         # Video processing utilities
├── data/                          # Input video/photo data
├── output/                        # Generated 3D models and results
├── start_live_reconstruction.bat  # Live reconstruction launcher
├── start_photo_reconstruction.bat # Photo reconstruction launcher
├── setup_and_run.bat              # Setup and run script
├── requirements.txt               # Python dependencies
├── README_Live_3D.md             # Live reconstruction documentation
├── README_Photo_Upload.md        # Photo upload documentation
└── TROUBLESHOOTING.md            # Troubleshooting guide
```

## Features

### ✅ Implemented
- **Live Camera Reconstruction**: Incremental triangulation from live camera feed
- **Photo Upload & Processing**: Multi-photo processing with explicit mode selection (`panorama` or `reconstruction`)
- **GUI Interface**: User-friendly graphical interface for photo processing
- **Command-Line Interface**: Flexible CLI for batch processing
- **Feature Detection & Matching**: ORB-based feature extraction
- **Camera Pose Estimation**: Relative pose calculation between frames
- **Point Cloud Generation**: 3D point cloud creation and visualization
- **Mesh Generation**: Surface reconstruction from point clouds
- **Export Options**: Save results in PLY format
- **Progress Tracking**: Real-time progress updates
- **Calibration Support**: Optional `camera_matrix` + `dist_coeffs` JSON for improved geometry
- **Metrics Logging**: Inlier ratio and backend usage summary

### 🔄 In Development
- Texture mapping
- Advanced mesh optimization
- Multi-scale reconstruction
- GPU acceleration

## Quick Start

### Live Camera Reconstruction
```bash
# Windows
start_live_reconstruction.bat

# Or directly
python src/live_reconstruction_app.py
```

### Photo Upload Reconstruction
```bash
# Windows (GUI)
start_photo_reconstruction.bat

# Command line panorama
python src/photo_reconstruction_cli.py --input-dir ./photos --mode panorama

# Command line 3D reconstruction (COLMAP-first backend)
python src/photo_reconstruction_cli.py --input-dir ./photos --mode reconstruction
```

## Setup

1. **Install Python 3.7+** and ensure it's in your PATH

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   - For live reconstruction: `start_live_reconstruction.bat`
   - For photo upload: `start_photo_reconstruction.bat`

## Usage

### Live Camera Mode
1. Run the live reconstruction application
2. Point camera at object to reconstruct
3. Press SPACE to capture keyframes
4. Press R to start reconstruction
5. Press S to save results

### Photo Upload Mode
1. Run the photo reconstruction application
2. Select multiple photos of your object
3. Click "Start Reconstruction"
4. View 3D results in visualization window
5. Save reconstruction results

## Input Requirements

### For Live Camera
- USB camera or webcam
- Good lighting conditions
- Static object or slow movement
- Camera movement around object

### For Photos
- 10-50 photos recommended
- 60-80% overlap between photos
- Good lighting, minimal shadows
- Photos from different angles
- Supported formats: JPG, PNG, BMP, TIFF

## Output

The system generates mode-specific outputs:
- **Panorama mode**: Panorama image (`.png`) + info file (`.txt`)
- **Reconstruction mode**: Point cloud (`.ply`) + optional mesh (`.ply`) + info file (`.txt`)

## Dependencies

- **OpenCV**: Image processing and computer vision
- **Open3D**: 3D data processing and visualization
- **NumPy**: Numerical computations
- **Tkinter**: Graphical user interface
- **COLMAP**: Structure from Motion (optional)
- **PyTorch3D**: Deep learning-based reconstruction (optional)

## Documentation

- [Live 3D Reconstruction Guide](README_Live_3D.md)
- [Photo Upload Guide](README_Photo_Upload.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

## License

MIT License 