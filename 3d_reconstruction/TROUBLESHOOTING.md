# Troubleshooting Guide for Live 3D Reconstruction on Windows

This guide helps resolve common issues with the Live 3D Reconstruction application on Windows.

## Installation Issues

### Open3D Not Found

If you encounter `ModuleNotFoundError: No module named 'open3d'`:

```
pip install open3d --no-cache-dir
```

If that doesn't work, you can try the following:

1. Make sure you have Visual C++ Redistributable installed:
   - Download from [Microsoft's website](https://aka.ms/vs/17/release/vc_redist.x64.exe)

2. Try installing a specific version of Open3D:
   ```
   pip install open3d==0.17.0
   ```

### PyTorch3D Installation Issues

PyTorch3D is optional and quite complex to install on Windows. If you don't need advanced deep learning-based reconstruction:

1. Remove or comment out the `pytorch3d` line in `requirements.txt`
2. The application will use the built-in reconstruction methods instead

## Runtime Issues

### Camera Not Detected

If your camera isn't detected:

1. Make sure it's properly connected
2. Try a different camera ID:
   ```
   python src/live_reconstruction_app.py --camera-id 1
   ```
3. Check your Windows privacy settings:
   - Go to Settings > Privacy & Security > Camera
   - Make sure camera access is enabled for apps

### Visualization Problems

If the 3D visualization doesn't appear:

1. Make sure you've installed Open3D correctly
2. Try adding several keyframes (at least 3-5) before pressing 'R'
3. Make sure your GPU drivers are up to date

### COLMAP Integration Issues

If you're trying to use COLMAP for better reconstruction:

1. Download and install COLMAP from the [official website](https://colmap.github.io/install.html)
2. Add the COLMAP installation directory to your PATH environment variable:
   - Search for "Edit environment variables for your account" in Windows
   - Edit the PATH variable and add the COLMAP bin directory
   - Restart your terminal/command prompt

## Performance Optimization

If the application is running slowly:

1. Try reducing the camera resolution:
   ```
   python src/live_reconstruction_app.py --width 320 --height 240
   ```

2. Ensure you have good lighting for better feature detection

3. Use a more powerful computer if possible, especially one with a dedicated GPU

## Saving and Viewing 3D Models

After saving your 3D models:

1. Use [MeshLab](https://www.meshlab.net/) to open and view .ply files (free and easy to use on Windows)
2. Use [Blender](https://www.blender.org/) for more advanced 3D model editing

## Common Error Messages and Solutions

### "Failed to open camera with ID X"

- Try a different camera ID or check if the camera is properly connected

### "COLMAP processing failed"

- Make sure COLMAP is properly installed and in your PATH
- The application will fall back to built-in methods

### "Failing to match features between frames"

- Improve lighting conditions
- Move the camera more slowly
- Ensure your scene has enough texture or distinctive features 