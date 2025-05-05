import cv2
import numpy as np
import argparse
import time
import os
import threading
import open3d as o3d
from pathlib import Path
from typing import Optional

from live_camera_processor import LiveCameraProcessor
from reconstruction_engine import ReconstructionEngine

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Live 3D reconstruction from camera")
    
    parser.add_argument("--camera-id", type=int, default=0,
                        help="Camera device ID (default: 0)")
    parser.add_argument("--width", type=int, default=640,
                        help="Camera capture width (default: 640)")
    parser.add_argument("--height", type=int, default=480,
                        help="Camera capture height (default: 480)")
    parser.add_argument("--output-dir", type=str, default="output",
                        help="Directory to save reconstruction results (default: output)")
    parser.add_argument("--save-keyframes", action="store_true",
                        help="Save keyframes to disk")
    
    return parser.parse_args()

def main():
    """Main application entry point."""
    args = parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create keyframes directory if needed
    keyframes_dir = output_dir / "keyframes"
    if args.save_keyframes:
        keyframes_dir.mkdir(exist_ok=True)
    
    print(f"Starting live 3D reconstruction with camera ID {args.camera_id}")
    print("Controls:")
    print("  - Press 'SPACE' to add current frame as keyframe")
    print("  - Press 'R' to start dense reconstruction from keyframes")
    print("  - Press 'S' to save the current reconstruction")
    print("  - Press 'ESC' to exit")
    
    # Initialize camera processor
    camera = LiveCameraProcessor(
        camera_id=args.camera_id,
        width=args.width,
        height=args.height
    )
    
    # Initialize reconstruction engine
    reconstruction = ReconstructionEngine()
    
    # Start camera capture
    camera.start_capture()
    
    # Wait for camera to initialize
    time.sleep(1.0)
    
    # Flag to track if visualization is started
    vis_started = False
    
    # Main application loop
    keyframe_count = 0
    last_keyframe_time = time.time()
    
    try:
        while True:
            # Get the latest frame
            frame = camera.get_latest_frame()
            if frame is None:
                time.sleep(0.1)
                continue
            
            # Show the frame
            cv2.imshow("Live Camera", frame)
            
            # Process the frame
            reconstruction.process_frame(frame)
            
            # Update visualization if started
            if vis_started:
                reconstruction.update_visualization()
            
            # Key handling
            key = cv2.waitKey(1) & 0xFF
            
            # ESC to exit
            if key == 27:
                break
                
            # Space to add keyframe
            elif key == 32:  # Space key
                # Add minimum time between keyframes
                current_time = time.time()
                if current_time - last_keyframe_time > 1.0:
                    print("Adding current frame as keyframe")
                    reconstruction.process_frame(frame, add_to_keyframes=True)
                    
                    # Save keyframe if requested
                    if args.save_keyframes:
                        keyframe_path = keyframes_dir / f"keyframe_{keyframe_count:04d}.jpg"
                        cv2.imwrite(str(keyframe_path), frame)
                        keyframe_count += 1
                        
                    last_keyframe_time = current_time
                
            # R to run dense reconstruction
            elif key == 114:  # 'r' key
                print("Starting dense reconstruction...")
                
                # Start visualization if not already started
                if not vis_started:
                    reconstruction.start_visualization()
                    vis_started = True
                
                # Run in a separate thread to avoid blocking UI
                threading.Thread(
                    target=reconstruction.process_keyframes,
                    daemon=True
                ).start()
                
            # S to save reconstruction
            elif key == 115:  # 's' key
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                # Save the point cloud
                pcd_path = output_dir / f"reconstruction_{timestamp}.ply"
                if len(reconstruction.point_cloud.points) > 0:
                    print(f"Saving point cloud to {pcd_path}")
                    o3d.io.write_point_cloud(str(pcd_path), reconstruction.point_cloud)
                
                # Save the mesh if available
                if reconstruction.mesh is not None:
                    mesh_path = output_dir / f"mesh_{timestamp}.ply"
                    print(f"Saving mesh to {mesh_path}")
                    o3d.io.write_triangle_mesh(str(mesh_path), reconstruction.mesh)
                    
    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        print("Cleaning up...")
        camera.stop()
        reconstruction.close()
        cv2.destroyAllWindows()
        
    print("Application ended")

if __name__ == "__main__":
    main() 