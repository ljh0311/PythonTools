#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network Camera Scanner for The Eyes

This script scans the local network for devices and attempts to identify IP cameras.
It uses various methods to detect cameras including:
1. Port scanning for common camera ports
2. ONVIF device discovery
3. Common camera HTTP endpoints detection
"""

import socket
import subprocess
import threading
import queue
import time
import re
import logging
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Set
import ipaddress
import sys
import json
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('network_camera_scan.log')
    ]
)

logger = logging.getLogger("camera_scanner")

# Common camera ports
CAMERA_PORTS = [
    80,    # HTTP
    554,   # RTSP
    443,   # HTTPS
    8000,  # Alternative HTTP
    8080,  # Alternative HTTP
    8554,  # Alternative RTSP
    37777, # Dahua
    9000,  # Hikvision
    10554, # ONVIF
]

# Common camera URLs/endpoints
CAMERA_ENDPOINTS = [
    "/onvif/device_service",
    "/axis-cgi/jpg/image.cgi",
    "/video.mjpg",
    "/video.cgi",
    "/mjpg/video.mjpg",
    "/cgi-bin/snapshot.cgi",
    "/snapshot.jpg",
    "/video/mjpg.cgi",
    "/live/0/main/default.m3u8",  # HLS streaming
    "/doc/page/login.asp",  # Hikvision
    "/view/index.shtml",    # Hikvision
    "/cgi-bin/viewer/video.jpg",  # Vivotek
    "/media/video",         # Mobotix
    "/nphMotionJpeg",       # Panasonic
    "/cam/realmonitor",     # Dahua
    "/webcam.mjpeg",        # Generic webcam stream
]

def get_local_ip() -> str:
    """Get the local IP address of this computer."""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        sys.exit(1)

def discover_network_range(local_ip: str) -> str:
    """Determine the network range based on local IP."""
    try:
        # Convert IP to network with /24 subnet mask
        ip_parts = local_ip.split('.')
        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        return network
    except Exception as e:
        logger.error(f"Error determining network range: {e}")
        return "192.168.1.0/24"  # Default fallback

def scan_host(ip: str, ports: List[int], timeout: float = 0.5) -> Dict:
    """
    Scan a host for open ports that might indicate a camera.
    
    Args:
        ip: IP address to scan
        ports: List of ports to check
        timeout: Socket timeout in seconds
        
    Returns:
        Dictionary with scan results
    """
    result = {
        "ip": ip,
        "hostname": "",
        "open_ports": [],
        "camera_endpoints": [],
        "is_camera": False
    }
    
    # Try to get hostname
    try:
        result["hostname"] = socket.getfqdn(ip)
    except:
        pass
    
    # Check for open ports
    for port in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            connection = s.connect_ex((ip, port))
            if connection == 0:
                result["open_ports"].append(port)
            s.close()
        except:
            continue
    
    # If no open ports found, return early
    if not result["open_ports"]:
        return result
    
    # Check for camera-specific endpoints on open HTTP/HTTPS ports
    http_ports = [p for p in result["open_ports"] if p in [80, 443, 8000, 8080]]
    for port in http_ports:
        protocol = "https" if port == 443 else "http"
        for endpoint in CAMERA_ENDPOINTS:
            url = f"{protocol}://{ip}:{port}{endpoint}"
            try:
                response = requests.get(url, timeout=1, verify=False)
                if response.status_code == 200:
                    result["camera_endpoints"].append(url)
                    result["is_camera"] = True
                    break
            except:
                continue
    
    # If we found camera endpoints or have RTSP ports open, mark as camera
    if result["camera_endpoints"] or any(p in result["open_ports"] for p in [554, 8554, 10554]):
        result["is_camera"] = True
    
    return result

def ping_sweep(network: str) -> List[str]:
    """
    Perform a ping sweep to find live hosts on the network.
    Uses different commands based on the operating system.
    
    Args:
        network: Network range in CIDR notation (e.g., "192.168.1.0/24")
        
    Returns:
        List of live IP addresses
    """
    live_hosts = []
    network_obj = ipaddress.IPv4Network(network)
    
    # Use different ping commands based on OS
    if sys.platform == "win32":
        ping_cmd = "ping -n 1 -w 200 {}"
        ping_success = "TTL="
    else:  # Linux/Mac
        ping_cmd = "ping -c 1 -W 1 {}"
        ping_success = "1 received"
    
    def ping_host(ip):
        try:
            result = subprocess.run(
                ping_cmd.format(ip), 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            if ping_success in result.stdout:
                return str(ip)
            return None
        except:
            return None
    
    logger.info(f"Starting ping sweep of {network}...")
    
    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(ping_host, network_obj.hosts()))
    
    # Filter out None values
    live_hosts = [ip for ip in results if ip]
    
    logger.info(f"Ping sweep complete. Found {len(live_hosts)} live hosts.")
    return live_hosts

def scan_network(network: str, ports_to_scan: List[int] = None) -> List[Dict]:
    """
    Scan the network for potential cameras.
    
    Args:
        network: Network range in CIDR notation (e.g., "192.168.1.0/24")
        ports_to_scan: List of ports to scan (defaults to CAMERA_PORTS)
        
    Returns:
        List of dictionaries with scan results
    """
    if ports_to_scan is None:
        ports_to_scan = CAMERA_PORTS
    
    # Find live hosts first
    live_hosts = ping_sweep(network)
    
    if not live_hosts:
        logger.warning("No live hosts found on the network.")
        return []
    
    logger.info(f"Scanning {len(live_hosts)} hosts for camera ports...")
    
    # Scan each host for camera ports
    scan_results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(scan_host, ip, ports_to_scan): ip for ip in live_hosts}
        for future in futures:
            try:
                result = future.result()
                scan_results.append(result)
                if result["is_camera"]:
                    logger.info(f"Found potential camera at {result['ip']}:{result['open_ports']}")
            except Exception as e:
                logger.error(f"Error scanning {futures[future]}: {e}")
    
    return scan_results

def format_scan_results(results: List[Dict]) -> str:
    """Format scan results for display."""
    camera_count = sum(1 for r in results if r["is_camera"])
    output = [
        "=" * 70,
        f"NETWORK CAMERA SCAN RESULTS - Found {camera_count} potential cameras",
        "=" * 70,
        ""
    ]
    
    # First display cameras
    if camera_count > 0:
        output.append("DETECTED CAMERAS:")
        output.append("-" * 70)
        
        for result in sorted([r for r in results if r["is_camera"]], key=lambda x: x["ip"]):
            ip = result["ip"]
            hostname = f" ({result['hostname']})" if result["hostname"] and result["hostname"] != ip else ""
            output.append(f"{ip}{hostname}")
            
            # Show open ports
            if result["open_ports"]:
                output.append(f"  - Open ports: {', '.join(map(str, result['open_ports']))}")
            
            # Show camera access URLs
            if result["camera_endpoints"]:
                output.append("  - Camera URLs:")
                for url in result["camera_endpoints"]:
                    output.append(f"    - {url}")
            
            # If no specific endpoints but has RTSP ports
            rtsp_ports = [p for p in result["open_ports"] if p in [554, 8554, 10554]]
            if rtsp_ports and not result["camera_endpoints"]:
                output.append("  - Potential RTSP URLs:")
                for port in rtsp_ports:
                    output.append(f"    - rtsp://{ip}:{port}/")
                    
            output.append("")
        
        output.append("")
    
    # Then show other devices
    other_devices = [r for r in results if not r["is_camera"] and r["open_ports"]]
    if other_devices:
        output.append("OTHER NETWORK DEVICES:")
        output.append("-" * 70)
        
        for result in sorted(other_devices, key=lambda x: x["ip"]):
            ip = result["ip"]
            hostname = f" ({result['hostname']})" if result["hostname"] and result["hostname"] != ip else ""
            ports = ", ".join(map(str, result["open_ports"]))
            output.append(f"{ip}{hostname} - Ports: {ports}")
        
        output.append("")
    
    return "\n".join(output)

def save_results_to_file(results: List[Dict], filename: str = "camera_scan_results.json") -> None:
    """Save scan results to a JSON file."""
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving results to file: {e}")

def capture_test_images(results: List[Dict], output_dir: str = "camera_test_images") -> None:
    """
    Attempt to capture a test image from each detected camera.
    
    Args:
        results: List of scan results containing camera information
        output_dir: Directory to save captured images
    """
    import os
    from datetime import datetime
    
    # Create output directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create output directory: {e}")
        return

    # Filter for cameras only
    cameras = [r for r in results if r["is_camera"]]
    if not cameras:
        logger.info("No cameras found to capture images from")
        return

    logger.info(f"Attempting to capture images from {len(cameras)} cameras...")

    for camera in cameras:
        ip = camera["ip"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Try each camera endpoint that might provide an image
        for endpoint in camera["camera_endpoints"]:
            if any(img_path in endpoint.lower() for img_path in ['.jpg', '.jpeg', '.mjpg', 'snapshot']):
                try:
                    # Make request with timeout
                    response = requests.get(endpoint, timeout=5, verify=False)
                    
                    if response.status_code == 200 and response.content:
                        # Save the image
                        filename = f"{ip.replace('.','_')}_{timestamp}.jpg"
                        filepath = os.path.join(output_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                            
                        logger.info(f"Successfully captured image from {ip} - saved to {filename}")
                        # Break after first successful capture for this camera
                        break
                except Exception as e:
                    logger.debug(f"Failed to capture from {ip} at {endpoint}: {e}")
            
    logger.info(f"Image capture complete. Check {output_dir} directory for results")

def main():
    """Main function to run the camera scanner."""
    parser = argparse.ArgumentParser(description="Network Camera Scanner")
    parser.add_argument("-n", "--network", help="Network range to scan (CIDR notation, e.g., 192.168.1.0/24)")
    parser.add_argument("-o", "--output", help="Output file for JSON results", default="camera_scan_results.json")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("-i", "--images", help="Directory to save test images", default="camera_test_images")
    args = parser.parse_args()
    
    # Set log level based on verbosity
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Print banner
    print("\n" + "=" * 70)
    print(" NETWORK CAMERA SCANNER FOR THE EYES ".center(70, "="))
    print("=" * 70)
    
    # Get local IP if network not specified
    if not args.network:
        local_ip = get_local_ip()
        network = discover_network_range(local_ip)
        print(f"\nLocal IP: {local_ip}")
        print(f"Using network range: {network}")
    else:
        network = args.network
        print(f"\nUsing specified network range: {network}")
    
    # Perform the scan
    try:
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        start_time = time.time()
        print(f"\nScanning network for cameras. This may take a few minutes...")
        results = scan_network(network)
        
        if not results:
            print("\nNo devices found on the network.")
            return
        
        # Format and display results
        formatted_results = format_scan_results(results)
        print(formatted_results)
        
        # Save results to file
        save_results_to_file(results, args.output)
        
        # Try to capture test images from detected cameras
        capture_test_images(results, args.images)
        
        # Print summary
        elapsed = time.time() - start_time
        camera_count = sum(1 for r in results if r["is_camera"])
        print(f"Scan completed in {elapsed:.1f} seconds.")
        print(f"Found {len(results)} devices, including {camera_count} potential cameras.")
        print(f"Results saved to {args.output}")
        print(f"Test images saved to {args.images}")
        
        # Open the images folder for viewing
        try:
            if sys.platform == "win32":
                subprocess.run(['explorer', args.images])
            elif sys.platform == "darwin":
                subprocess.run(['open', args.images])
            else:
                subprocess.run(['xdg-open', args.images])
            print(f"\nOpening captured images folder: {args.images}")
        except Exception as e:
            print(f"\nCould not automatically open images folder: {e}")
            print(f"Please manually check the folder: {args.images}")
            
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as e:
        logger.error(f"Error during scan: {e}")
        print(f"\nError during scan: {e}")

if __name__ == "__main__":
    main() 