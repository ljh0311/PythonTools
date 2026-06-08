#!/usr/bin/env python3
"""
Test script for improved camera detection functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import SmartCamera
import cv2

def test_camera_detection():
    """Test the camera detection functionality."""
    print("🔍 Testing Camera Detection")
    print("=" * 50)
    
    # Detect available cameras
    print("Detecting available cameras...")
    cameras = SmartCamera.detect_available_cameras()
    
    if not cameras:
        print("❌ No cameras detected")
        return
    
    print(f"\n📹 Found {len(cameras)} camera(s):")
    print("-" * 50)
    
    for i, camera in enumerate(cameras):
        if camera['available']:
            print(f"{i+1}. {camera['name']}")
            print(f"   ID: {camera['camera_id']}")
            print(f"   Resolution: {camera['resolution'][0]}x{camera['resolution'][1]}")
            print(f"   FPS: {camera['fps']:.1f}")
            if 'backend' in camera:
                print(f"   Backend: {camera['backend']}")
            print()
    
    # Test camera initialization
    available_cameras = [c for c in cameras if c['available']]
    if available_cameras:
        print("🧪 Testing camera initialization...")
        test_camera = available_cameras[0]
        print(f"Testing with: {test_camera['name']}")
        
        try:
            camera = SmartCamera(camera_id=test_camera['camera_id'])
            print("✅ Camera initialized successfully!")
            
            # Get camera info
            info = camera.get_camera_info()
            print("\n📋 Camera Information:")
            for key, value in info.items():
                print(f"   {key.title()}: {value}")
            
            camera.cleanup()
            print("\n✅ Camera test completed successfully!")
            
        except Exception as e:
            print(f"❌ Camera initialization failed: {str(e)}")
    else:
        print("❌ No available cameras to test")

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

def test_camera_preview():
    """Test camera preview functionality (GUI version)."""
    def run_preview():
        cameras = SmartCamera.detect_available_cameras()
        available_cameras = [c for c in cameras if c['available']]

        if not available_cameras:
            messagebox.showerror("Camera Preview", "❌ No available cameras for preview test")
            root.destroy()
            return

        test_camera = available_cameras[0]
        status_label.config(text=f"Testing preview with: {test_camera['name']}")

        try:
            cap = cv2.VideoCapture(test_camera['camera_id'])
            if cap.isOpened():
                status_label.config(text="✅ Camera opened for preview")
                frames = []
                for i in range(5):
                    ret, frame = cap.read()
                    if ret:
                        frames.append(frame)
                        frame_status = f"Frame {i+1}: {frame.shape}"
                    else:
                        frame_status = f"Frame {i+1}: Failed to read"
                    frame_listbox.insert(tk.END, frame_status)
                cap.release()
                status_label.config(text="✅ Preview test completed")
                # Show the last frame in the preview
                if frames:
                    frame_rgb = cv2.cvtColor(frames[-1], cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    img = img.resize((320, 240))
                    imgtk = ImageTk.PhotoImage(image=img)
                    preview_label.imgtk = imgtk
                    preview_label.config(image=imgtk)
            else:
                status_label.config(text="❌ Failed to open camera for preview")
                messagebox.showerror("Camera Preview", "❌ Failed to open camera for preview")
        except Exception as e:
            status_label.config(text=f"❌ Preview test failed: {str(e)}")
            messagebox.showerror("Camera Preview", f"❌ Preview test failed: {str(e)}")

    # GUI setup
    root = tk.Toplevel() if tk._default_root else tk.Tk()
    root.title("Camera Preview Test")
    root.geometry("400x400")
    root.resizable(False, False)

    ttk.Label(root, text="🎬 Testing Camera Preview", font=("Segoe UI", 14, "bold")).pack(pady=(10, 5))
    status_label = ttk.Label(root, text="Initializing...", font=("Segoe UI", 10))
    status_label.pack(pady=(0, 10))

    frame_listbox = tk.Listbox(root, width=45, height=7)
    frame_listbox.pack(pady=(0, 10))

    preview_label = ttk.Label(root)
    preview_label.pack(pady=(0, 10))

    ttk.Button(root, text="Run Preview Test", command=run_preview).pack(pady=(0, 10))
    ttk.Button(root, text="Close", command=root.destroy).pack()

    root.mainloop()

def main():
    """Run all tests."""
    print("🤖 Smart Camera Detection Test")
    print("=" * 50)
    
    try:
        test_camera_detection()
        test_camera_preview()
        
        print("\n✅ All tests completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test error: {str(e)}")

if __name__ == "__main__":
    main() 