# Photo Processing (Panorama + 3D)

This module supports two explicit contracts:
- `panorama`: create a 360 equirectangular panorama.
- `reconstruction`: create a 3D point cloud/mesh (COLMAP-first backend, manual fallback).

## Features

- **Multiple Photo Upload**: Select multiple photos through a file dialog
- **Photo Validation**: Automatically validates photos for reconstruction suitability
- **Smart Preprocessing**: Resizes and optimizes photos for better reconstruction
- **Progress Tracking**: Real-time progress updates during processing
- **Mode Contract**: Select `panorama` or `reconstruction` explicitly
- **3D Visualization**: Interactive 3D viewer for reconstruction results
- **Export Options**: Save panoramas, point clouds, and meshes
- **Flexible Input**: Support for various image formats (JPG, PNG, BMP, TIFF)

## Quick Start

### GUI Mode (Recommended for beginners)

1. **Run the application**:
   ```bash
   # Windows
   start_photo_reconstruction.bat
   
   # Or directly with Python
   python src/photo_upload_processor.py
   ```

2. **Select Photos**: Click "Select Photos" and choose multiple photos of your object
3. **Choose Mode**: Select `panorama` or `reconstruction`
4. **Start Processing**: Click "Start Reconstruction" to begin
5. **View Results**: Panorama image or 3D output is generated
5. **Save Results**: Click "Save Results" to export the reconstruction

### Command-Line Mode

```bash
# Panorama mode
python src/photo_reconstruction_cli.py --input-dir ./photos --mode panorama

# 3D reconstruction mode
python src/photo_reconstruction_cli.py --input-dir ./photos --mode reconstruction

# Launch GUI from command line
python src/photo_reconstruction_cli.py --gui
```

## Photo Requirements

For best reconstruction results, follow these guidelines:

### Photo Quality
- **Resolution**: Minimum 100x100 pixels, recommended 1920x1080 or higher
- **Format**: JPG, PNG, BMP, or TIFF
- **Quality**: Clear, well-lit photos with minimal blur

### Photo Coverage
- **Overlap**: Each photo should overlap with others by 60-80%
- **Angles**: Take photos from different angles around the object
- **Quantity**: 10-50 photos typically work well
- **Complete Coverage**: Ensure all sides of the object are photographed

### Lighting and Environment
- **Good Lighting**: Avoid shadows and harsh lighting
- **Static Object**: The object should not move between photos
- **Clean Background**: Simple backgrounds work better
- **No Reflections**: Avoid reflective surfaces when possible

## File Structure

```
3d_reconstruction/
├── src/
│   ├── photo_upload_processor.py    # Main photo processing module
│   ├── photo_reconstruction_cli.py  # Command-line interface
│   └── reconstruction_engine.py     # Core reconstruction engine
├── start_photo_reconstruction.bat   # Windows launcher
├── output/                          # Default output directory
│   ├── photo_reconstruction_pointcloud_YYYYMMDD_HHMMSS.ply
│   ├── photo_reconstruction_mesh_YYYYMMDD_HHMMSS.ply
│   └── photo_reconstruction_info_YYYYMMDD_HHMMSS.txt
└── requirements.txt                 # Python dependencies
```

## Output Files

The reconstruction process generates several output files:

### Point Cloud (.ply)
- **Format**: PLY (Polygon File Format)
- **Content**: 3D points with color information
- **Usage**: Can be opened in 3D viewers like MeshLab, CloudCompare

### Mesh (.ply)
- **Format**: PLY triangle mesh
- **Content**: 3D surface reconstruction
- **Usage**: Can be 3D printed or used in CAD software

### Info File (.txt)
- **Format**: Text file with reconstruction metadata
- **Content**: Processing details, statistics, and parameters

## Advanced Usage

### Command-Line Options

```bash
python src/photo_reconstruction_cli.py --help
```

Available options:
- `--input-dir DIR`: Process all photos in a directory
- `--photos FILE1 FILE2...`: Process specific photo files
- `--gui`: Launch graphical interface
- `--output-dir DIR`: Specify output directory (default: output)
- `--mode {panorama,reconstruction}`: Choose output contract
- `--calibration-file FILE`: Optional JSON calibration file (`camera_matrix`, `dist_coeffs`)
- `--target-size WIDTH HEIGHT`: Resize photos (default: 640 480)
- `--max-photos N`: Limit number of photos (default: 20)
- `--save-intermediate`: Save intermediate processing results

### Programmatic Usage

```python
from src.photo_upload_processor import PhotoUploadProcessor

# Initialize processor
processor = PhotoUploadProcessor(output_dir="my_reconstruction")

# Process photos
photo_paths = ["photo1.jpg", "photo2.jpg", "photo3.jpg"]
success = processor.reconstruct_from_photos(photo_paths)

if success:
    # Save results
    saved_files = processor.save_reconstruction()
    print("Reconstruction saved:", saved_files)

# Clean up
processor.close()
```

## Troubleshooting

### Common Issues

**"Need at least 2 valid photos for reconstruction"**
- Ensure you've selected at least 2 photos
- Check that photos are valid image files
- Verify photos meet minimum size requirements

**"3D reconstruction failed"**
- Try with different photos
- Ensure photos have sufficient overlap
- Check lighting conditions
- Reduce number of photos if processing too many

**"Cannot read image"**
- Verify image file is not corrupted
- Check file format is supported
- Ensure file permissions allow reading

**Performance Issues**
- Reduce photo resolution using `--target-size`
- Limit number of photos with `--max-photos`
- Close other applications to free memory

### Tips for Better Results

1. **Take More Photos**: More photos generally yield better results
2. **Vary Angles**: Capture object from many different viewpoints
3. **Good Lighting**: Ensure consistent, even lighting
4. **High Resolution**: Use high-resolution photos when possible
5. **Clean Background**: Simple backgrounds work better
6. **No Motion**: Keep object completely still between photos

## Technical Details

### Processing Pipeline

1. **Photo Validation**: Check file existence, format, and size
2. **Preprocessing**: Resize, denoise, and optimize images
3. **Feature Detection**: Extract keypoints and descriptors
4. **Matching**: Find correspondences between photos
5. **Pose Estimation**: Calculate camera positions
6. **Triangulation**: Generate 3D points
7. **Mesh Generation**: Create surface reconstruction
8. **Export**: Save results in standard formats

### Dependencies

- **OpenCV**: Image processing and computer vision
- **Open3D**: 3D data processing and visualization
- **NumPy**: Numerical computations
- **Tkinter**: Graphical user interface
- **COLMAP**: Structure from Motion (optional)

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review photo requirements and tips
3. Try with different photos
4. Check system requirements and dependencies

## License

This module is part of the 3D Reconstruction project. See the main README for license information. 