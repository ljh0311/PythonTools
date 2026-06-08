import os
import sys
import cv2
import numpy as np
import open3d as o3d
import logging
import time

# Add project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.camera.camera_manager import CameraManager
from src.image_processing.processor import ImageProcessor
from src.utils.config import load_config, create_default_config
from src.reconstruction.single_cam_reconstructor import SingleCamReconstructor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("single_cam_view")

def main():
    # Try to load configuration
    try:
        config_path = "config/config.json"
        config = load_config(config_path)
    except:
        logger.warning("Using default configuration")
        config = create_default_config()
    
    # Initialize components
    camera_manager = CameraManager(config.get("cameras", {}))
    image_processor = ImageProcessor(config.get("image_processing", {}))
    visualizer = SingleCamReconstructor(config.get("reconstruction", {}))
    
    # Create visualizer window
    vis = o3d.visualization.Visualizer()
    vis.create_window("The Eyes - Single Camera View", width=800, height=600)
    
    # Main loop
    try:
        while True:
            # Capture frame
            frames = camera_manager.capture_all()
            if not frames:
                logger.error("No camera frames captured")
                break
                
            # Process the first camera's frame
            cam_id = list(frames.keys())[0]
            processed_frame = image_processor.process(frames[cam_id])
            
            # Create point cloud
            point_cloud, _ = visualizer.reconstruct(processed_frame)
            
            # Update visualization
            vis.clear_geometries()
            vis.add_geometry(point_cloud)
            vis.poll_events()
            vis.update_renderer()
            
            # Check if window is closed
            if not vis.poll_events():
                break
                
            # Pause briefly
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        logger.info("Visualization stopped by user")
    except Exception as e:
        logger.error(f"Error in visualization: {e}")
    finally:
        # Clean up
        vis.destroy_window()
        camera_manager.release_all()

if __name__ == "__main__":
    main()
