#!/usr/bin/env python3
"""
Command-line interface for 3D reconstruction from photos.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

from photo_upload_processor import PhotoUploadProcessor

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Photo processing: panorama or 3D reconstruction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reconstruct from photos in a directory
  python photo_reconstruction_cli.py --input-dir ./photos --output-dir ./reconstruction

  # Reconstruct from specific photo files
  python photo_reconstruction_cli.py --photos photo1.jpg photo2.jpg photo3.jpg

  # Use GUI mode
  python photo_reconstruction_cli.py --gui
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-dir", type=str,
                            help="Directory containing photos to process")
    input_group.add_argument("--photos", nargs="+", type=str,
                            help="List of photo files to process")
    input_group.add_argument("--gui", action="store_true",
                            help="Launch GUI interface")
    
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Directory to save reconstruction results (default: output)")
    parser.add_argument("--target-size", nargs=2, type=int, default=[640, 480],
                        metavar=("WIDTH", "HEIGHT"),
                        help="Target size for resizing photos (default: 640 480)")
    parser.add_argument("--max-photos", type=int, default=20,
                        help="Maximum number of photos to use (default: 20)")
    parser.add_argument("--save-intermediate", action="store_true",
                        help="Save intermediate processing results")
    parser.add_argument("--mode", choices=["panorama", "reconstruction"], default="panorama",
                        help="Processing mode contract (default: panorama)")
    parser.add_argument("--calibration-file", type=str, default=None,
                        help="Optional camera calibration JSON with camera_matrix/dist_coeffs")
    
    return parser.parse_args()

def get_photo_files_from_directory(directory: str) -> List[str]:
    """Get all photo files from a directory.
    
    Args:
        directory: Directory path
        
    Returns:
        List of photo file paths
    """
    photo_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
    photo_files = []
    
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory '{directory}' does not exist")
        return []
    
    if not dir_path.is_dir():
        print(f"Error: '{directory}' is not a directory")
        return []
    
    for file_path in dir_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in photo_extensions:
            photo_files.append(str(file_path))
    
    return sorted(photo_files)

def validate_photo_files(photo_files: List[str]) -> List[str]:
    """Validate that photo files exist and are accessible.
    
    Args:
        photo_files: List of photo file paths
        
    Returns:
        List of valid photo file paths
    """
    valid_files = []
    
    for photo_file in photo_files:
        if not os.path.exists(photo_file):
            print(f"Warning: Photo file '{photo_file}' does not exist, skipping")
            continue
        
        if not os.path.isfile(photo_file):
            print(f"Warning: '{photo_file}' is not a file, skipping")
            continue
        
        valid_files.append(photo_file)
    
    return valid_files

def print_progress(progress: int, message: str):
    """Print progress updates.
    
    Args:
        progress: Progress percentage (0-100)
        message: Progress message
    """
    # Create a simple progress bar
    bar_length = 40
    filled_length = int(bar_length * progress // 100)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    
    print(f"\r[{bar}] {progress:3d}% - {message}", end='', flush=True)
    
    if progress == 100:
        print()  # New line when complete

def main():
    """Main entry point."""
    args = parse_args()
    
    # Launch GUI if requested
    if args.gui:
        from photo_upload_processor import PhotoUploadGUI
        gui = PhotoUploadGUI()
        try:
            gui.run()
        finally:
            gui.close()
        return
    
    # Get photo files
    if args.input_dir:
        photo_files = get_photo_files_from_directory(args.input_dir)
        if not photo_files:
            print(f"No photo files found in directory '{args.input_dir}'")
            return
    else:  # args.photos
        photo_files = validate_photo_files(args.photos)
        if not photo_files:
            print("No valid photo files provided")
            return
    
    print(f"Found {len(photo_files)} photo files")
    
    # Limit number of photos if specified
    if len(photo_files) > args.max_photos:
        print(f"Limiting to {args.max_photos} photos (use --max-photos to change)")
        photo_files = photo_files[:args.max_photos]
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize processor
    processor = PhotoUploadProcessor(str(output_dir))
    
    try:
        processor.set_mode(args.mode)
        if args.calibration_file:
            loaded = processor.reconstruction_engine.load_camera_params(args.calibration_file)
            if loaded:
                print(f"Loaded camera calibration from: {args.calibration_file}")
            else:
                print(f"Warning: could not load calibration file: {args.calibration_file}")
        print(f"Starting photo pipeline in '{args.mode}' mode...")
        print("This may take several minutes depending on the number of photos.")
        
        # Perform reconstruction
        success = processor.reconstruct_from_photos(photo_files, print_progress)
        
        if success:
            print(f"\n{args.mode.capitalize()} pipeline completed successfully!")
            
            # Save results
            print("Saving reconstruction results...")
            saved_files = processor.save_reconstruction()
            
            if saved_files:
                print("Files saved:")
                for file_type, path in saved_files.items():
                    print(f"  {file_type}: {path}")
            else:
                print("Warning: Failed to save reconstruction results")
        else:
            print("\nReconstruction failed. Please try with different photos.")
            print("Tips for better results:")
            print("  - Use photos with good lighting")
            print("  - Ensure photos have overlapping areas")
            print("  - Avoid blurry or low-quality images")
            print("  - Take photos from different angles around the object")
    
    except KeyboardInterrupt:
        print("\nReconstruction interrupted by user")
    except Exception as e:
        print(f"\nError during reconstruction: {e}")
    finally:
        processor.close()

if __name__ == "__main__":
    main() 