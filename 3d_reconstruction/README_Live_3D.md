# Live 3D Reconstruction from Camera

This module enables real-time 3D reconstruction using a connected camera. It uses computer vision techniques to track features across video frames, calculate camera pose, and create a 3D point cloud which can be further processed into a 3D mesh.

## Prerequisites

- Python 3.7+
- OpenCV
- NumPy
- Open3D
- COLMAP (optional, for dense reconstruction)

All requirements are listed in the `requirements.txt` file.

## Installation on Windows

1. Ensure you have all dependencies installed:

```bash
pip install numpy opencv-python
pip install open3d --no-cache-dir
pip install pyntcloud plyfile tqdm matplotlib
```

2. For COLMAP support (optional but recommended for higher quality reconstruction):
   - Windows: Download and install from https://colmap.github.io/install.html
   - Add COLMAP to your PATH environment variable

## Usage

### Command Line Interface

Run the live reconstruction application with default settings:

```
python src/live_reconstruction_app.py
```

### Command Line Options

- `--camera-id`: Select camera by device ID (default: 0)
- `--width`: Set camera capture width (default: 640)
- `--height`: Set camera capture height (default: 480)
- `--output-dir`: Directory to save reconstruction results (default: "output")
- `--save-keyframes`: Save keyframes to disk (default: false)

Example with options:

```
python src/live_reconstruction_app.py --camera-id 1 --width 1280 --height 720 --save-keyframes
```

### Controls

During the application:

- **Space bar**: Add the current frame as a keyframe for reconstruction
- **R key**: Start dense reconstruction using collected keyframes
- **S key**: Save the current reconstruction (point cloud and mesh if available)
- **ESC**: Exit the application

## How It Works

1. The application captures live video from your camera
2. When you press Space, it saves the current frame as a keyframe
3. When you press R, it processes all keyframes to generate a 3D reconstruction:
   - Feature detection and matching across frames
   - Camera pose estimation
   - Point cloud generation
   - Mesh creation (if enough keyframes and features)
4. When you press S, it saves the reconstruction to the output directory

## Tips for Good Reconstruction

- Move slowly around the object/scene
- Ensure good lighting conditions
- Capture keyframes from different viewpoints (roughly 15-30 degrees apart)
- Include some texture or distinctive features in the scene
- Avoid reflective or transparent surfaces
- Keep the camera at a consistent distance from the subject

## Output Files

- Point clouds are saved as `.ply` files in the output directory
- Meshes (if generated) are also saved as `.ply` files
- These can be opened with 3D software like MeshLab, Blender, or Open3D's visualizer

## Troubleshooting

If you encounter installation issues, please refer to the `TROUBLESHOOTING.md` file for detailed solutions specifically for Windows environments.

1. **Camera not found**: Check if your camera ID is correct
   ```
   python src/live_reconstruction_app.py --camera-id 1
   ```

2. **Low quality reconstruction**: Try:
   - Adding more keyframes
   - Ensuring good lighting
   - Moving more slowly between keyframes
   - Installing COLMAP for better reconstruction quality

3. **COLMAP errors**: Make sure COLMAP is properly installed and in your PATH

## For Developers

The live 3D reconstruction consists of three main components:

1. `LiveCameraProcessor`: Handles camera access and frame capture
2. `ReconstructionEngine`: Processes frames and performs 3D reconstruction
3. `live_reconstruction_app.py`: Main application that connects everything

You can import and use these components in your own applications.

### Example Integration

```python
from live_camera_processor import LiveCameraProcessor
from reconstruction_engine import ReconstructionEngine

# Initialize components
camera = LiveCameraProcessor(camera_id=0)
reconstruction = ReconstructionEngine()

# Start camera
camera.start_capture()

# Process frames
frame = camera.get_latest_frame()
reconstruction.process_frame(frame, add_to_keyframes=True)

# Generate reconstruction
reconstruction.process_keyframes()

# Save result
# ... (see source code for details)
``` 