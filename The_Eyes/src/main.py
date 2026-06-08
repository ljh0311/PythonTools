#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The Eyes - CLI entry point (optional multi-camera 3D reconstruction pipeline).

Primary home-surveillance UI: run `python src/run_gui.py` (see README).
"""

import argparse
import logging
import os
import sys
import time

# Repo root on path for `src.*` imports (matches run_gui.py).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from src.camera.camera_manager import CameraManager
from src.image_processing.processor import ImageProcessor
from src.feature_matching.matcher import FeatureMatcher
from src.reconstruction.reconstructor import Reconstructor
from src.rendering.renderer import Renderer
from src.utils.config import load_config
from src.utils.logger import setup_logger


def parse_args():
    parser = argparse.ArgumentParser(
        description="The Eyes - optional 3D reconstruction from multiple cameras (CLI)"
    )
    _default_cfg = os.path.join(_REPO_ROOT, "config", "config.json")
    _default_out = os.path.join(_REPO_ROOT, "output")
    parser.add_argument("-c", "--config", default=_default_cfg, help="Path to configuration file")
    parser.add_argument("-o", "--output", default=_default_out, help="Output directory for 3D models")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--calibrate", action="store_true", help="Run camera calibration")
    parser.add_argument("--visualize", action="store_true", help="Visualize the reconstruction process")
    return parser.parse_args()


def main():
    # Parse command line arguments
    args = parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger("the_eyes", log_level)
    logger.info("Starting The Eyes - 3D Reconstruction System")
    
    # Load configuration
    try:
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return 1
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    try:
        # Initialize camera system
        logger.info("Initializing camera system...")
        camera_manager = CameraManager(config["cameras"])
        
        # Check number of available cameras
        if len(camera_manager.cameras) < 2:
            logger.error("At least two working cameras are required for 3D reconstruction. Found: %d", len(camera_manager.cameras))
            print("ERROR: At least two working cameras are required for 3D reconstruction.")
            return 1
        
        # If calibration is requested, run it and exit
        if args.calibrate:
            logger.info("Starting camera calibration...")
            camera_manager.calibrate()
            logger.info("Calibration completed. Exiting.")
            return 0
        
        # Initialize processing components
        image_processor = ImageProcessor(config["image_processing"])
        feature_matcher = FeatureMatcher(config["feature_matching"])
        reconstructor = Reconstructor(config["reconstruction"])
        renderer = Renderer(config["rendering"])
        
        logger.info("System initialized, starting processing loop")
        
        # Main processing loop
        while True:
            # Capture images from all cameras
            logger.debug("Capturing images from cameras")
            frames = camera_manager.capture_all()
            # Remove any None frames (failed captures)
            frames = {k: v for k, v in frames.items() if v is not None}
            if len(frames) < 2:
                logger.warning("Not enough valid frames captured for reconstruction. Skipping this cycle.")
                time.sleep(1)
                continue
            
            # Process images
            logger.debug("Processing images")
            processed_frames = image_processor.process_batch(frames)
            
            # Extract and match features
            logger.debug("Extracting and matching features")
            features = feature_matcher.match_features(processed_frames)
            
            # Reconstruct 3D model
            logger.debug("Reconstructing 3D model")
            point_cloud, mesh = reconstructor.reconstruct(features)
            
            # Render and save the results
            logger.debug("Rendering and saving results")
            renderer.render(point_cloud, mesh, os.path.join(args.output, f"model_{int(time.time())}.ply"))
            
            # Optionally visualize
            if args.visualize:
                renderer.visualize(point_cloud, mesh)
            
            # Check for exit condition (could be modified to be event-based)
            if camera_manager.should_exit():
                break
                
        logger.info("Processing complete, shutting down")
        camera_manager.release_all()
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error in main processing loop: {e}", exc_info=args.debug)
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 