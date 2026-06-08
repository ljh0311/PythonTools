#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Add Network Cameras to The Eyes

This script runs the network camera scanner and adds any discovered cameras
to The Eyes project configuration file.
"""

import os
import sys
import json
import yaml
import argparse
import logging
import subprocess
import re
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("add_cameras")

# Default paths
CONFIG_DIR = "config"
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
SCAN_RESULTS_FILE = "camera_scan_results.json"

def run_camera_scan(network: str = None, output_file: str = SCAN_RESULTS_FILE) -> bool:
    """
    Run the network camera scanner.
    
    Args:
        network: Optional network range to scan
        output_file: Path to save scan results
        
    Returns:
        True if scan was successful, False otherwise
    """
    try:
        # Construct the command
        cmd = [sys.executable, "network_camera_scanner.py", "-o", output_file]
        if network:
            cmd.extend(["-n", network])
        
        # Run the scanner
        logger.info(f"Running network camera scanner...")
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if process.returncode != 0:
            logger.error(f"Scanner failed with error: {process.stderr}")
            return False
            
        logger.info("Camera scan completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error running camera scan: {e}")
        return False

def load_scan_results(scan_file: str = SCAN_RESULTS_FILE) -> List[Dict]:
    """
    Load camera scan results from JSON file.
    
    Args:
        scan_file: Path to the scan results file
        
    Returns:
        List of camera scan results
    """
    try:
        if not os.path.exists(scan_file):
            logger.error(f"Scan results file not found: {scan_file}")
            return []
            
        with open(scan_file, 'r') as f:
            scan_results = json.load(f)
            
        # Filter to only keep cameras
        cameras = [r for r in scan_results if r.get("is_camera", False)]
        logger.info(f"Loaded {len(cameras)} cameras from scan results")
        return cameras
        
    except Exception as e:
        logger.error(f"Error loading scan results: {e}")
        return []

def load_config(config_file: str = CONFIG_FILE) -> Dict:
    """
    Load The Eyes configuration file.
    
    Args:
        config_file: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        if not os.path.exists(config_file):
            logger.warning(f"Config file not found: {config_file}")
            # Create default config structure
            return {
                "cameras": {}
            }
            
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            
        # Initialize cameras section if it doesn't exist
        if config is None:
            config = {}
        if "cameras" not in config:
            config["cameras"] = {}
            
        return config
        
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {"cameras": {}}

def save_config(config: Dict, config_file: str = CONFIG_FILE) -> bool:
    """
    Save The Eyes configuration file.
    
    Args:
        config: Configuration dictionary
        config_file: Path to save the configuration
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        # Make sure config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
            
        logger.info(f"Configuration saved to {config_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False

def extract_camera_url(camera: Dict) -> str:
    """
    Extract the best URL for a camera from scan results.
    
    Args:
        camera: Camera scan result dictionary
        
    Returns:
        Camera URL or empty string if none found
    """
    # First check for detected camera endpoints
    if camera.get("camera_endpoints"):
        # Prefer RTSP endpoints if available
        rtsp_endpoints = [url for url in camera["camera_endpoints"] if url.startswith("rtsp://")]
        if rtsp_endpoints:
            return rtsp_endpoints[0]
            
        # Fall back to first available endpoint
        return camera["camera_endpoints"][0]
        
    # Check for RTSP ports
    rtsp_ports = [p for p in camera.get("open_ports", []) if p in [554, 8554, 10554]]
    if rtsp_ports:
        # Use the first RTSP port
        return f"rtsp://{camera['ip']}:{rtsp_ports[0]}/"
        
    # Check for HTTP ports
    http_ports = [p for p in camera.get("open_ports", []) if p in [80, 8000, 8080]]
    if http_ports:
        return f"http://{camera['ip']}:{http_ports[0]}/video"
        
    # If we couldn't determine a specific URL, return IP address
    return camera["ip"]

def add_cameras_to_config(cameras: List[Dict], config: Dict) -> Dict:
    """
    Add cameras from scan results to configuration.
    
    Args:
        cameras: List of camera scan results
        config: The Eyes configuration dictionary
        
    Returns:
        Updated configuration dictionary
    """
    # Ensure cameras section exists
    if "cameras" not in config:
        config["cameras"] = {}
        
    added_count = 0
    updated_count = 0
    
    # Process each camera
    for camera in cameras:
        ip = camera["ip"]
        camera_id = f"network_cam_{ip.replace('.', '_')}"
        
        # Extract camera URL
        url = extract_camera_url(camera)
        
        # Check if camera already exists
        if camera_id in config["cameras"]:
            # Update existing camera
            config["cameras"][camera_id]["ip"] = ip
            config["cameras"][camera_id]["url"] = url
            updated_count += 1
        else:
            # Add new camera
            hostname = camera.get("hostname", "").replace(".", "_")
            name = hostname if hostname and hostname != ip else f"Camera {ip}"
            
            config["cameras"][camera_id] = {
                "type": "network",
                "name": name,
                "ip": ip,
                "url": url,
                "width": 640,
                "height": 480,
                "fps": 25,
                "auto_reconnect": True
            }
            added_count += 1
    
    logger.info(f"Added {added_count} new cameras and updated {updated_count} existing cameras")
    return config

def main():
    """Main function to run the camera integration."""
    parser = argparse.ArgumentParser(description="Add Network Cameras to The Eyes")
    parser.add_argument("-n", "--network", help="Network range to scan (CIDR notation, e.g., 192.168.1.0/24)")
    parser.add_argument("-c", "--config", help="Path to The Eyes config file", default=CONFIG_FILE)
    parser.add_argument("-s", "--scan-file", help="Path to scan results file", default=SCAN_RESULTS_FILE)
    parser.add_argument("--skip-scan", action="store_true", help="Skip network scanning and use existing results")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Print banner
    print("\n" + "=" * 70)
    print(" ADDING NETWORK CAMERAS TO THE EYES ".center(70, "="))
    print("=" * 70 + "\n")
    
    try:
        # Run camera scan if not skipped
        if not args.skip_scan:
            success = run_camera_scan(args.network, args.scan_file)
            if not success:
                print("Failed to run camera scan. Check log for details.")
                return
        else:
            print("Skipping network scan, using existing results file.")
        
        # Load scan results
        cameras = load_scan_results(args.scan_file)
        if not cameras:
            print("No cameras found in scan results.")
            return
            
        # Load current config
        config = load_config(args.config)
        
        # Add cameras to config
        config = add_cameras_to_config(cameras, config)
        
        # Save updated config
        save_config(config, args.config)
        
        print(f"\nSuccess! Added detected cameras to config: {args.config}")
        print(f"Total cameras in configuration: {len(config['cameras'])}")
        
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"\nError during operation: {e}")
        
    print("")

if __name__ == "__main__":
    main() 