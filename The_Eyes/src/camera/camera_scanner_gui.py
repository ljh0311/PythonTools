#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network Camera Scanner GUI

A graphical application to scan the network for devices, 
identify IP cameras, and view their live feeds.
Also detects locally connected cameras (webcams).
"""

import os
import sys
import json
import socket
import subprocess
import threading
import time
import logging
import ipaddress
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.scrolledtext import ScrolledText
import cv2
import numpy as np
import requests
from PIL import Image, ImageTk
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Set
import urllib3

# Suppress warnings for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('camera_scanner_gui.log')
    ]
)

logger = logging.getLogger("camera_scanner_gui")

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

# Scanning functions from original script

def get_local_ip() -> str:
    """Get the local IP address of this computer."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "127.0.0.1"

def discover_network_range(local_ip: str) -> str:
    """Determine the network range based on local IP."""
    try:
        ip_parts = local_ip.split('.')
        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
        return network
    except Exception as e:
        logger.error(f"Error determining network range: {e}")
        return "192.168.1.0/24"  # Default fallback

def scan_host(ip: str, ports: List[int], timeout: float = 0.5) -> Dict:
    """Scan a host for open ports that might indicate a camera."""
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

def ping_sweep(network: str, callback=None) -> List[str]:
    """Perform a ping sweep to find live hosts on the network."""
    live_hosts = []
    network_obj = ipaddress.IPv4Network(network)
    total_hosts = network_obj.num_addresses - 2  # Subtract network and broadcast addresses
    processed = 0
    
    # Use different ping commands based on OS
    if sys.platform == "win32":
        ping_cmd = "ping -n 1 -w 200 {}"
        ping_success = "TTL="
    else:  # Linux/Mac
        ping_cmd = "ping -c 1 -W 1 {}"
        ping_success = "1 received"
    
    def ping_host(ip):
        nonlocal processed
        try:
            result = subprocess.run(
                ping_cmd.format(ip), 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            is_alive = ping_success in result.stdout
            processed += 1
            
            if callback:
                # Calculate progress as percentage
                progress = (processed / total_hosts) * 100
                callback(progress, f"Pinging {ip}... {'Success' if is_alive else 'Failed'}")
                
            if is_alive:
                return str(ip)
            return None
        except:
            processed += 1
            if callback:
                progress = (processed / total_hosts) * 100
                callback(progress, f"Pinging {ip}... Error")
            return None
    
    logger.info(f"Starting ping sweep of {network}...")
    
    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=50) as executor:
        results = list(executor.map(ping_host, network_obj.hosts()))
    
    # Filter out None values
    live_hosts = [ip for ip in results if ip]
    
    logger.info(f"Ping sweep complete. Found {len(live_hosts)} live hosts.")
    return live_hosts

def extract_camera_url(camera: Dict) -> Dict:
    """Extract the best URLs for a camera from scan results."""
    urls = {
        "rtsp": [],
        "http": [],
        "snapshot": []
    }
    
    # Check for detected camera endpoints
    if camera.get("camera_endpoints"):
        for url in camera["camera_endpoints"]:
            if url.startswith("rtsp://"):
                urls["rtsp"].append(url)
            elif any(img_path in url.lower() for img_path in ['.jpg', '.jpeg', 'snapshot']):
                urls["snapshot"].append(url)
            elif any(vid_path in url.lower() for vid_path in ['.mjpg', 'video', 'stream']):
                urls["http"].append(url)
    
    # Check for RTSP ports
    rtsp_ports = [p for p in camera.get("open_ports", []) if p in [554, 8554, 10554]]
    for port in rtsp_ports:
        urls["rtsp"].append(f"rtsp://{camera['ip']}:{port}/")
    
    # Check for HTTP ports
    http_ports = [p for p in camera.get("open_ports", []) if p in [80, 8000, 8080]]
    for port in http_ports:
        # Add potential HTTP video streams
        urls["http"].append(f"http://{camera['ip']}:{port}/video")
        
        # Add potential snapshot URLs
        urls["snapshot"].append(f"http://{camera['ip']}:{port}/snapshot.jpg")
    
    return urls

class CameraStreamReader:
    """Class to handle camera stream reading and processing."""
    
    def __init__(self, camera_url):
        self.camera_url = camera_url
        self.cap = None
        self.is_running = False
        self.current_frame = None
        self.lock = threading.Lock()
        self.error = None
        
    def start(self):
        """Start the camera stream."""
        if self.is_running:
            return
            
        self.error = None
        self.is_running = True
        threading.Thread(target=self._read_stream, daemon=True).start()
        
    def stop(self):
        """Stop the camera stream."""
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def get_frame(self):
        """Get the current frame from the camera."""
        with self.lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
            
    def _read_stream(self):
        """Read frames from the camera stream in a separate thread."""
        try:
            # Check if it's a local camera (integer index) or URL string
            if isinstance(self.camera_url, int) or (isinstance(self.camera_url, str) and self.camera_url.isdigit()):
                # Convert to integer if it's a string
                camera_index = int(self.camera_url) if isinstance(self.camera_url, str) else self.camera_url
                self.cap = cv2.VideoCapture(camera_index)
                
                if not self.cap.isOpened():
                    self.error = f"Failed to open local camera at index {camera_index}"
                    self.is_running = False
                    return
                    
                # Try to set some properties to ensure good quality
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                while self.is_running:
                    ret, frame = self.cap.read()
                    if not ret:
                        continue
                        
                    with self.lock:
                        self.current_frame = frame
                        
                    # Don't overload the CPU
                    time.sleep(0.033)  # ~30 FPS
                
            # For RTSP and HTTP streams
            elif isinstance(self.camera_url, str) and self.camera_url.startswith(('rtsp://', 'http://', 'https://')):
                self.cap = cv2.VideoCapture(self.camera_url)
                
                if not self.cap.isOpened():
                    self.error = f"Failed to open camera stream: {self.camera_url}"
                    self.is_running = False
                    return
                    
                while self.is_running:
                    ret, frame = self.cap.read()
                    if not ret:
                        continue
                        
                    with self.lock:
                        self.current_frame = frame
                        
                    # Don't overload the CPU
                    time.sleep(0.033)  # ~30 FPS
            else:
                self.error = f"Unsupported camera URL format: {self.camera_url}"
                self.is_running = False
            
        except Exception as e:
            self.error = f"Error reading camera stream: {e}"
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False

class CameraScannerGUI(tk.Tk):
    """GUI Application for Network Camera Scanner."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Network Camera Scanner")
        self.geometry("1024x768")
        self.minsize(800, 600)
        
        # Application state
        self.scan_results = []
        self.selected_camera = None
        self.scanning_in_progress = False
        self.active_streams = {}
        self.scan_local_cams = tk.BooleanVar(value=True)  # New variable for local camera scanning
        
        # Create UI elements
        self._create_menu()
        self._create_main_layout()
        
        # Initialize network info
        self._initialize_network_info()
        
    def _create_menu(self):
        """Create the application menu bar."""
        menu_bar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Save Scan Results", command=self._save_results)
        file_menu.add_command(label="Load Scan Results", command=self._load_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menu_bar, tearoff=0)
        tools_menu.add_command(label="Scan Network", command=self._start_scan)
        tools_menu.add_command(label="Scan Local Cameras Only", command=self._scan_local_only)  # New command
        tools_menu.add_command(label="Stop Scan", command=self._stop_scan, state=tk.DISABLED)
        menu_bar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menu_bar)
        self.menu_bar = menu_bar
        self.tools_menu = tools_menu
        
    def _create_main_layout(self):
        """Create the main application layout."""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top frame for network settings
        top_frame = ttk.LabelFrame(main_frame, text="Network Settings", padding=5)
        top_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Network settings controls
        net_controls = ttk.Frame(top_frame)
        net_controls.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(net_controls, text="Local IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.local_ip_var = tk.StringVar()
        ttk.Entry(net_controls, textvariable=self.local_ip_var, width=15, state="readonly").grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(net_controls, text="Network Range:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.network_range_var = tk.StringVar()
        self.network_entry = ttk.Entry(net_controls, textvariable=self.network_range_var, width=20)
        self.network_entry.grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
        
        # Add checkbox for local camera scanning
        local_cam_check = ttk.Checkbutton(net_controls, text="Include Local Cameras", variable=self.scan_local_cams)
        local_cam_check.grid(row=0, column=4, padx=5, pady=2, sticky=tk.W)
        
        self.scan_btn = ttk.Button(net_controls, text="Scan Network", command=self._start_scan)
        self.scan_btn.grid(row=0, column=5, padx=5, pady=2)
        
        # Scan progress
        progress_frame = ttk.Frame(top_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=5)
        
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.status_var).pack(side=tk.RIGHT, padx=5)
        
        # Paned window for devices and camera view
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left frame for device list
        devices_frame = ttk.LabelFrame(paned_window, text="Detected Devices")
        
        # Device list with scrollbar
        device_list_frame = ttk.Frame(devices_frame)
        device_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview for devices
        self.device_tree = ttk.Treeview(device_list_frame, columns=("hostname", "ports", "camera"), show="headings")
        self.device_tree.heading("hostname", text="Hostname")
        self.device_tree.heading("ports", text="Ports")
        self.device_tree.heading("camera", text="Camera")
        
        self.device_tree.column("hostname", width=100)
        self.device_tree.column("ports", width=100)
        self.device_tree.column("camera", width=50)
        
        self.device_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar to treeview
        scrollbar = ttk.Scrollbar(device_list_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind device selection event
        self.device_tree.bind("<<TreeviewSelect>>", self._on_device_selected)
        
        # Right frame for camera view
        camera_frame = ttk.LabelFrame(paned_window, text="Camera View")
        
        # Camera video frame
        self.video_frame = ttk.Frame(camera_frame)
        self.video_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for video display
        self.video_canvas = tk.Canvas(self.video_frame, bg="black")
        self.video_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Camera controls
        controls_frame = ttk.Frame(camera_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stream_var = tk.StringVar(value="")
        ttk.Label(controls_frame, text="Stream URL:").pack(side=tk.LEFT, padx=2)
        self.stream_combo = ttk.Combobox(controls_frame, textvariable=self.stream_var, width=40)
        self.stream_combo.pack(side=tk.LEFT, padx=2)
        
        self.connect_btn = ttk.Button(controls_frame, text="Connect", command=self._connect_to_camera)
        self.connect_btn.pack(side=tk.LEFT, padx=2)
        
        self.disconnect_btn = ttk.Button(controls_frame, text="Disconnect", command=self._disconnect_camera, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=2)
        
        # Add frames to paned window
        paned_window.add(devices_frame, weight=1)
        paned_window.add(camera_frame, weight=2)
        
        # Status bar at bottom
        status_bar = ttk.Frame(main_frame, relief=tk.SUNKEN, padding=(2, 2))
        status_bar.pack(fill=tk.X, side=tk.BOTTOM, padx=5)
        
        self.status_label = ttk.Label(status_bar, text="Ready")
        self.status_label.pack(side=tk.LEFT)
        
        # Store important UI elements for later access
        self.paned_window = paned_window
        self.controls_frame = controls_frame
        
    def _initialize_network_info(self):
        """Initialize network information."""
        try:
            local_ip = get_local_ip()
            network_range = discover_network_range(local_ip)
            
            self.local_ip_var.set(local_ip)
            self.network_range_var.set(network_range)
        except Exception as e:
            logger.error(f"Error initializing network info: {e}")
            messagebox.showerror("Error", f"Failed to determine network information: {e}")
    
    def _update_progress(self, value, status_text=None):
        """Update progress bar and status text."""
        self.progress_var.set(value)
        
        if status_text:
            self.status_var.set(status_text)
            self.status_label.config(text=status_text)
            
        # Force UI update
        self.update_idletasks()
    
    def _scan_local_only(self):
        """Scan only for locally connected cameras."""
        if self.scanning_in_progress:
            return
            
        # Clear previous results
        self.device_tree.delete(*self.device_tree.get_children())
        self.scan_results = []
        self._disconnect_camera()
        
        # Update UI state
        self.scanning_in_progress = True
        self.scan_btn.config(state=tk.DISABLED)
        self.tools_menu.entryconfigure("Scan Network", state=tk.DISABLED)
        self.tools_menu.entryconfigure("Scan Local Cameras Only", state=tk.DISABLED)
        self.tools_menu.entryconfigure("Stop Scan", state=tk.NORMAL)
        
        # Reset progress
        self._update_progress(0, "Scanning for local cameras...")
        
        # Start scan in a separate thread
        threading.Thread(target=self._run_local_scan, daemon=True).start()
    
    def _run_local_scan(self):
        """Run the local camera scan in a background thread."""
        try:
            # Scan for local cameras
            self._update_progress(0, "Scanning for locally connected cameras...")
            local_cameras = detect_local_cameras()
            
            # Add to scan results
            self.scan_results.extend(local_cameras)
            
            # Update the tree view
            for camera in local_cameras:
                # Create a nice display name
                display_name = f"{camera['hostname']} ({camera['resolution']})"
                
                # Add to tree view
                item_id = camera["ip"]
                self.device_tree.insert("", tk.END, iid=item_id, 
                                      values=(display_name, "Local", "Yes"))
                
                # Highlight cameras
                self.device_tree.item(item_id, tags=("camera",))
            
            # Configure tag for cameras to show in a different color
            self.device_tree.tag_configure("camera", background="#E0F0E0")
            
            # Scan complete
            self._update_progress(100, f"Scan complete. Found {len(local_cameras)} local cameras")
            
            if len(local_cameras) == 0:
                messagebox.showinfo("Scan Complete", "No local cameras were detected.")
            else:
                messagebox.showinfo("Scan Complete", f"Found {len(local_cameras)} local cameras.")
                
        except Exception as e:
            logger.error(f"Error during local scan: {e}")
            self._update_progress(100, f"Error: {e}")
            messagebox.showerror("Scan Error", f"An error occurred during the scan: {e}")
            
        finally:
            # Reset UI state
            self.scanning_in_progress = False
            self.scan_btn.config(state=tk.NORMAL)
            self.tools_menu.entryconfigure("Scan Network", state=tk.NORMAL)
            self.tools_menu.entryconfigure("Scan Local Cameras Only", state=tk.NORMAL)
            self.tools_menu.entryconfigure("Stop Scan", state=tk.DISABLED)
    
    def _start_scan(self):
        """Start the network scan."""
        if self.scanning_in_progress:
            return
            
        # Clear previous results
        self.device_tree.delete(*self.device_tree.get_children())
        self.scan_results = []
        self._disconnect_camera()
        
        network = self.network_range_var.get()
        scan_local = self.scan_local_cams.get()
        
        try:
            # Validate the network range
            ipaddress.IPv4Network(network)
        except ValueError as e:
            messagebox.showerror("Invalid Network", f"The network range {network} is invalid: {e}")
            return
            
        # Update UI state
        self.scanning_in_progress = True
        self.scan_btn.config(state=tk.DISABLED)
        self.tools_menu.entryconfigure("Scan Network", state=tk.DISABLED)
        self.tools_menu.entryconfigure("Scan Local Cameras Only", state=tk.DISABLED)
        self.tools_menu.entryconfigure("Stop Scan", state=tk.NORMAL)
        
        # Reset progress
        self._update_progress(0, f"Starting scan of {network}...")
        
        # Start scan in a separate thread
        threading.Thread(target=self._run_scan, args=(network, scan_local), daemon=True).start()
    
    def _stop_scan(self):
        """Stop the network scan."""
        if not self.scanning_in_progress:
            return
            
        self.scanning_in_progress = False
        self._update_progress(100, "Scan stopped by user")
        
        # Update UI state
        self.scan_btn.config(state=tk.NORMAL)
        self.tools_menu.entryconfigure("Scan Network", state=tk.NORMAL)
        self.tools_menu.entryconfigure("Scan Local Cameras Only", state=tk.NORMAL)
        self.tools_menu.entryconfigure("Stop Scan", state=tk.DISABLED)
    
    def _run_scan(self, network, scan_local=True):
        """Run the network scan in a background thread."""
        try:
            # Scan for local cameras first if requested
            local_cameras = []
            if scan_local:
                self._update_progress(0, "Scanning for locally connected cameras...")
                local_cameras = detect_local_cameras()
                self.scan_results.extend(local_cameras)
                
                # Add to tree view
                for camera in local_cameras:
                    # Create a nice display name
                    display_name = f"{camera['hostname']} ({camera['resolution']})"
                    
                    # Add to tree view
                    item_id = camera["ip"]
                    self.device_tree.insert("", tk.END, iid=item_id, 
                                          values=(display_name, "Local", "Yes"))
                    
                    # Highlight cameras
                    self.device_tree.item(item_id, tags=("camera",))
            
            # Phase 1: Ping sweep
            progress_start = 10 if scan_local else 0
            self._update_progress(progress_start, "Performing ping sweep...")
            live_hosts = ping_sweep(network, callback=self._update_progress)
            
            if not self.scanning_in_progress:
                return
                
            if not live_hosts and not local_cameras:
                self._update_progress(100, "No devices found on the network")
                messagebox.showinfo("Scan Complete", "No devices found")
                self._stop_scan()
                return
                
            if not live_hosts:
                # We have local cameras but no network devices
                progress_adjustment = 100
                self._update_progress(progress_adjustment, f"No network devices found. Scan complete with {len(local_cameras)} local cameras.")
                messagebox.showinfo("Scan Complete", f"No network devices found, but detected {len(local_cameras)} local cameras.")
                self._stop_scan()
                return
                
            # Phase 2: Port scan on live hosts
            progress_mid = 50 if scan_local else 40
            self._update_progress(progress_mid, f"Scanning {len(live_hosts)} hosts for camera ports...")
            total_hosts = len(live_hosts)
            completed = 0
            
            # Prepare TreeView for updates
            for ip in live_hosts:
                self.device_tree.insert("", tk.END, iid=ip, values=(ip, "", "Scanning..."))
            
            # Scan each host for camera ports
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {executor.submit(scan_host, ip, CAMERA_PORTS): ip for ip in live_hosts}
                
                for future in futures:
                    if not self.scanning_in_progress:
                        executor.shutdown(wait=False)
                        return
                        
                    try:
                        ip = futures[future]
                        result = future.result()
                        self.scan_results.append(result)
                        
                        # Update TreeView with result
                        ports = ", ".join(map(str, result["open_ports"])) if result["open_ports"] else "None"
                        is_camera = "Yes" if result["is_camera"] else "No"
                        
                        # Update the existing item
                        self.device_tree.item(ip, values=(result["hostname"] or ip, ports, is_camera))
                        
                        # Highlight cameras
                        if result["is_camera"]:
                            self.device_tree.item(ip, tags=("camera",))
                        
                        # Update progress
                        completed += 1
                        progress = progress_mid + (completed / total_hosts) * (100 - progress_mid)
                        self._update_progress(progress, f"Scanning {ip}...")
                        
                    except Exception as e:
                        logger.error(f"Error scanning {futures[future]}: {e}")
            
            # Configure tag for cameras to show in a different color
            self.device_tree.tag_configure("camera", background="#E0F0E0")
            
            # Scan complete
            network_cameras = sum(1 for r in self.scan_results if r["is_camera"] and not r.get("is_local", False))
            total_cameras = network_cameras + len(local_cameras)
            self._update_progress(100, f"Scan complete. Found {len(self.scan_results)} devices, {total_cameras} cameras")
            
            # Construct appropriate message
            if local_cameras and network_cameras:
                msg = f"Found {len(live_hosts)} network devices with {network_cameras} cameras, and {len(local_cameras)} local cameras."
            elif local_cameras:
                msg = f"Found {len(live_hosts)} network devices (no network cameras), and {len(local_cameras)} local cameras."
            elif network_cameras:
                msg = f"Found {len(live_hosts)} network devices with {network_cameras} cameras."
            else:
                msg = f"Found {len(live_hosts)} network devices, but no cameras were detected."
            
            messagebox.showinfo("Scan Complete", msg)
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            self._update_progress(100, f"Error: {e}")
            messagebox.showerror("Scan Error", f"An error occurred during the scan: {e}")
            
        finally:
            # Reset UI state
            self.scanning_in_progress = False
            self.scan_btn.config(state=tk.NORMAL)
            self.tools_menu.entryconfigure("Scan Network", state=tk.NORMAL)
            self.tools_menu.entryconfigure("Scan Local Cameras Only", state=tk.NORMAL)
            self.tools_menu.entryconfigure("Stop Scan", state=tk.DISABLED)
    
    def _on_device_selected(self, event):
        """Handle device selection in the TreeView."""
        selected_items = self.device_tree.selection()
        if not selected_items:
            return
            
        selected_ip = selected_items[0]
        self.selected_camera = None
        
        # Find the selected camera in scan results
        for camera in self.scan_results:
            if camera["ip"] == selected_ip:
                self.selected_camera = camera
                break
                
        if not self.selected_camera:
            return
            
        # Disconnect any existing stream
        self._disconnect_camera()
        
        # Check if this is a local camera or network camera
        if self.selected_camera.get("is_local", False):
            # For local cameras, we create a simple URL
            self.stream_combo["values"] = [f"Local: Webcam {self.selected_camera['index']}"]
            self.stream_combo.current(0)
            self.connect_btn.config(state=tk.NORMAL)
        elif self.selected_camera["is_camera"]:
            # For network cameras, get potential URLs
            urls = extract_camera_url(self.selected_camera)
            
            # Combine all URL types for the combobox
            all_urls = []
            all_urls.extend([f"RTSP: {url}" for url in urls["rtsp"]])
            all_urls.extend([f"HTTP: {url}" for url in urls["http"]])
            all_urls.extend([f"Snapshot: {url}" for url in urls["snapshot"]])
            
            # Update the combobox
            self.stream_combo["values"] = all_urls
            
            if all_urls:
                self.stream_combo.current(0)
                self.connect_btn.config(state=tk.NORMAL)
            else:
                self.stream_var.set("")
                self.connect_btn.config(state=tk.DISABLED)
        else:
            # Not a camera
            self.stream_combo["values"] = []
            self.stream_var.set("")
            self.connect_btn.config(state=tk.DISABLED)
    
    def _connect_to_camera(self):
        """Connect to the selected camera stream."""
        if not self.selected_camera:
            return
            
        stream_text = self.stream_var.get()
        if not stream_text:
            return
            
        # Disconnect any existing stream
        self._disconnect_camera()
        
        try:
            # Check if this is a local camera
            if self.selected_camera.get("is_local", False):
                # Connect to local webcam
                camera_index = self.selected_camera["index"]
                self._update_progress(0, f"Connecting to local webcam {camera_index}...")
                self.connect_btn.config(state=tk.DISABLED)
                
                # Start the camera stream
                camera_stream = CameraStreamReader(camera_index)  # Pass camera index directly
                camera_stream.start()
                
                # Wait a bit for the connection to establish
                time.sleep(1)
                
                if camera_stream.error:
                    messagebox.showerror("Connection Error", camera_stream.error)
                    camera_stream.stop()
                    self.connect_btn.config(state=tk.NORMAL)
                    return
                    
                # Start the video display update loop
                stream_id = f"local:{camera_index}"
                self.active_streams[stream_id] = camera_stream
                self.after(30, lambda: self._update_video_frame(stream_id))
                
                self._update_progress(100, f"Connected to local webcam {camera_index}")
                self.disconnect_btn.config(state=tk.NORMAL)
                return
                
            # For network cameras, extract URL from combobox selection
            url_parts = stream_text.split(": ", 1)
            if len(url_parts) != 2:
                return
                
            stream_type, url = url_parts
            
            # Display connecting message
            self._update_progress(0, f"Connecting to camera at {url}...")
            self.connect_btn.config(state=tk.DISABLED)
            
            # For snapshot URLs, just display the image
            if stream_type == "Snapshot":
                try:
                    response = requests.get(url, timeout=3, verify=False)
                    if response.status_code == 200:
                        # Convert the image data to a PhotoImage
                        image = Image.open(BytesIO(response.content))
                        photo = ImageTk.PhotoImage(image)
                        
                        # Display on canvas
                        self.video_canvas.create_image(0, 0, anchor=tk.NW, image=photo)
                        self.video_canvas.image = photo  # Keep a reference
                        
                        self._update_progress(100, f"Connected to snapshot at {url}")
                        self.disconnect_btn.config(state=tk.NORMAL)
                    else:
                        messagebox.showerror("Connection Error", f"Failed to get snapshot: HTTP {response.status_code}")
                        self.connect_btn.config(state=tk.NORMAL)
                except Exception as e:
                    messagebox.showerror("Connection Error", f"Failed to get snapshot: {e}")
                    self.connect_btn.config(state=tk.NORMAL)
            else:
                # For RTSP/HTTP streams, start a video reader
                camera_stream = CameraStreamReader(url)
                camera_stream.start()
                
                # Wait a bit for the connection to establish
                time.sleep(1)
                
                if camera_stream.error:
                    messagebox.showerror("Connection Error", camera_stream.error)
                    camera_stream.stop()
                    self.connect_btn.config(state=tk.NORMAL)
                    return
                    
                # Start the video display update loop
                self.active_streams[url] = camera_stream
                self.after(30, lambda: self._update_video_frame(url))
                
                self._update_progress(100, f"Connected to stream at {url}")
                self.disconnect_btn.config(state=tk.NORMAL)
                
        except Exception as e:
            logger.error(f"Error connecting to camera: {e}")
            messagebox.showerror("Connection Error", f"Failed to connect to camera: {e}")
            self.connect_btn.config(state=tk.NORMAL)
    
    def _disconnect_camera(self):
        """Disconnect from the current camera stream."""
        # Stop all active streams
        for url, stream in self.active_streams.items():
            stream.stop()
            
        self.active_streams = {}
        
        # Clear the canvas
        self.video_canvas.delete("all")
        
        # Reset UI state
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self._update_progress(0, "Disconnected from camera")
    
    def _update_video_frame(self, url):
        """Update the video frame from the camera stream."""
        if url not in self.active_streams:
            return
            
        stream = self.active_streams[url]
        
        if not stream.is_running:
            if stream.error:
                messagebox.showerror("Stream Error", stream.error)
            self._disconnect_camera()
            return
            
        # Get the current frame
        frame = stream.get_frame()
        
        if frame is not None:
            # Convert frame to a format suitable for tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
            # Resize image to fit canvas while maintaining aspect ratio
            canvas_width = self.video_canvas.winfo_width()
            canvas_height = self.video_canvas.winfo_height()
            
            if canvas_width > 1 and canvas_height > 1:
                img_width, img_height = img.size
                
                # Calculate scaling factor to fit the canvas
                scale_width = canvas_width / img_width
                scale_height = canvas_height / img_height
                scale = min(scale_width, scale_height)
                
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                if new_width > 0 and new_height > 0:
                    img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage and display
            photo = ImageTk.PhotoImage(image=img)
            
            # Clear previous image and display new one
            self.video_canvas.delete("all")
            self.video_canvas.create_image(
                canvas_width // 2, canvas_height // 2,
                image=photo, anchor=tk.CENTER
            )
            self.video_canvas.image = photo  # Keep a reference
        
        # Schedule the next update
        self.after(30, lambda: self._update_video_frame(url))
    
    def _save_results(self):
        """Save scan results to a file."""
        if not self.scan_results:
            messagebox.showinfo("No Results", "No scan results to save.")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Save Scan Results"
            )
            
            if not filename:
                return
                
            with open(filename, 'w') as f:
                json.dump(self.scan_results, f, indent=2)
                
            self._update_progress(100, f"Results saved to {filename}")
            messagebox.showinfo("Save Complete", f"Scan results saved to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            messagebox.showerror("Save Error", f"Failed to save results: {e}")
    
    def _load_results(self):
        """Load scan results from a file."""
        try:
            filename = filedialog.askopenfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                title="Load Scan Results"
            )
            
            if not filename:
                return
                
            with open(filename, 'r') as f:
                results = json.load(f)
                
            # Clear existing results
            self.device_tree.delete(*self.device_tree.get_children())
            self._disconnect_camera()
            
            # Add loaded results
            self.scan_results = results
            
            for result in results:
                ip = result["ip"]
                ports = ", ".join(map(str, result["open_ports"])) if result["open_ports"] else "None"
                is_camera = "Yes" if result["is_camera"] else "No"
                
                item_id = self.device_tree.insert("", tk.END, iid=ip, values=(result["hostname"] or ip, ports, is_camera))
                
                if result["is_camera"]:
                    self.device_tree.item(item_id, tags=("camera",))
            
            # Configure tag for cameras
            self.device_tree.tag_configure("camera", background="#E0F0E0")
            
            camera_count = sum(1 for r in results if r["is_camera"])
            self._update_progress(100, f"Loaded {len(results)} devices, {camera_count} cameras")
            messagebox.showinfo("Load Complete", f"Loaded {len(results)} devices, including {camera_count} cameras.")
            
        except Exception as e:
            logger.error(f"Error loading results: {e}")
            messagebox.showerror("Load Error", f"Failed to load results: {e}")
    
    def _show_about(self):
        """Show the about dialog."""
        about_text = """
Network Camera Scanner

A graphical application to scan the network for devices,
identify IP cameras, and view their live feeds.
Also supports locally connected webcams.

Features:
- Network device discovery
- Camera detection (network & local)
- Live camera viewing
- Support for RTSP, HTTP, and snapshot URLs
- Local webcam support

© 2023 The Eyes Project
        """
        
        messagebox.showinfo("About", about_text)
        
    def on_closing(self):
        """Handle window closing event."""
        # Clean up any active streams
        for url, stream in self.active_streams.items():
            stream.stop()
            
        self.destroy()

# Function to detect locally connected cameras
def detect_local_cameras(max_cameras=10) -> List[Dict]:
    """
    Detect locally connected cameras (webcams) using OpenCV.
    
    Args:
        max_cameras: Maximum number of camera indices to check
        
    Returns:
        List of dictionaries with local camera information
    """
    logger.info("Scanning for locally connected cameras...")
    local_cameras = []
    
    for i in range(max_cameras):
        try:
            # Try to open the camera
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Camera is available, get its properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                
                # Read a test frame to verify it's working
                ret, frame = cap.read()
                is_working = ret and frame is not None and frame.size > 0
                
                # Create camera info dictionary
                camera_info = {
                    "id": f"local_{i}",
                    "ip": f"local:{i}",
                    "hostname": f"Webcam {i}",
                    "is_camera": True,
                    "is_local": True,
                    "index": i,
                    "resolution": f"{width}x{height}",
                    "fps": fps,
                    "is_working": is_working,
                    "open_ports": [],
                    "camera_endpoints": []
                }
                
                local_cameras.append(camera_info)
                logger.info(f"Found local camera at index {i}: {width}x{height}@{fps}fps")
            
            # Always release the camera
            cap.release()
            
        except Exception as e:
            logger.debug(f"Error checking local camera at index {i}: {e}")
    
    logger.info(f"Found {len(local_cameras)} locally connected cameras")
    return local_cameras

# Main function
def main():
    # Check for required packages
    try:
        import cv2
    except ImportError:
        print("ERROR: OpenCV (cv2) is required but not installed.")
        print("Please install it using: pip install opencv-python")
        return
        
    try:
        import requests
    except ImportError:
        print("ERROR: Requests library is required but not installed.")
        print("Please install it using: pip install requests")
        return
    
    # Print startup message
    print("Starting Network Camera Scanner GUI...")
    print("This application now supports both network IP cameras and local webcams.")
    print("Use the 'Include Local Cameras' checkbox to enable/disable local camera detection.")
        
    # Start the application
    app = CameraScannerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main() 