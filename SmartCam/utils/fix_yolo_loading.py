#!/usr/bin/env python3
"""
Script to fix YOLO model loading issues.
"""

import os
import sys
import torch
import subprocess
import shutil

def check_yolo_installation():
    """Check if YOLO is properly installed."""
    print("🔍 Checking YOLO installation...")
    
    try:
        if TORCH_AVAILABLE:
            import torch
            print(f"✅ PyTorch version: {torch.__version__}")
        else:
            print("❌ PyTorch not found")
            return False
        
        # Try to import ultralytics
        try:
            import ultralytics
            print(f"✅ Ultralytics version: {ultralytics.__version__}")
            return True
        except ImportError:
            print("❌ Ultralytics not found")
            return False
            
    except ImportError:
        print("❌ PyTorch not found")
        return False

def install_yolo():
    """Install YOLO using pip."""
    print("\n📦 Installing YOLO...")
    
    try:
        # Install ultralytics
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ultralytics"])
        print("✅ YOLO installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install YOLO: {e}")
        return False

def test_yolo_loading():
    """Test YOLO model loading."""
    print("\n🧪 Testing YOLO model loading...")
    
    try:
        # Method 1: Try ultralytics directly
        try:
            from ultralytics import YOLO
            model = YOLO('yolov8n.pt')  # Use YOLOv8 nano as fallback
            print("✅ YOLO loaded successfully using ultralytics")
            return True
        except Exception as e:
            print(f"❌ Ultralytics method failed: {e}")
        
        # Method 2: Try torch hub with trust_repo
        try:
            model = torch.hub.load('ultralytics/yolov5', 'yolov5s', trust_repo=True)
            print("✅ YOLO loaded successfully using torch hub")
            return True
        except Exception as e:
            print(f"❌ Torch hub method failed: {e}")
        
        # Method 3: Try with pretrained=False
        try:
            model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=False, trust_repo=True)
            print("✅ YOLO loaded successfully (without pretrained weights)")
            return True
        except Exception as e:
            print(f"❌ Non-pretrained method failed: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ YOLO loading test failed: {e}")
        return False

def create_yolo_fallback():
    """Create a fallback YOLO implementation."""
    print("\n🔧 Creating YOLO fallback...")
    
    fallback_code = '''
import cv2
import numpy as np
from typing import List, Dict, Any

class YOLOFallback:
    """Fallback object detection when YOLO is not available."""
    
    def __init__(self):
        self.classes = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat']
        print("⚠️  Using YOLO fallback - limited detection capabilities")
    
    def __call__(self, img):
        """Simulate YOLO detection with basic contour detection."""
        class MockResults:
            def __init__(self, detections):
                self.xyxy = [detections]
                self.names = {i: name for i, name in enumerate(self.classes)}
        
        # Convert to grayscale for simple detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Simple edge detection
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        for contour in contours[:5]:  # Limit to 5 detections
            area = cv2.contourArea(contour)
            if area > 1000:  # Filter small contours
                x, y, w, h = cv2.boundingRect(contour)
                detections.append([x, y, x+w, y+h, 0.5, 0])  # [x1, y1, x2, y2, conf, class]
        
        return MockResults(np.array(detections))

# Create global fallback instance
yolo_fallback = YOLOFallback()
'''
    
    try:
        # Create yolo_fallback.py in parent directory
        parent_dir = os.path.dirname(os.path.dirname(__file__))
        fallback_path = os.path.join(parent_dir, 'yolo_fallback.py')
        
        with open(fallback_path, 'w') as f:
            f.write(fallback_code)
        print(f"✅ YOLO fallback created: {fallback_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create fallback: {e}")
        return False

def update_main_py():
    """Update main.py to use YOLO fallback."""
    print("\n🔧 Updating main.py for YOLO fallback...")
    
    try:
        # Read main.py (from parent directory)
        main_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Add fallback import
        if 'from yolo_fallback import yolo_fallback' not in content:
            # Find the imports section
            import_section = content.find('import torch')
            if import_section != -1:
                # Add fallback import after torch import
                content = content[:import_section] + '''# YOLO fallback
try:
    from yolo_fallback import yolo_fallback
    YOLO_FALLBACK_AVAILABLE = True
except ImportError:
    YOLO_FALLBACK_AVAILABLE = False

''' + content[import_section:]
        
        # Update YOLO loading section
        yolo_loading_pattern = '''# Load YOLO object detection model with better error handling
            try:
                model_file = os.path.join(self.model_path, "yolov5s.pt")
                if os.path.exists(model_file):
                    self.object_detector = torch.hub.load('ultralytics/yolov5', 'custom', path=model_file)
                    logger.info("Object detection model loaded")
                else:
                    logger.warning("Object detection model not found, using default YOLO")
                    # Use a more reliable method to load YOLO
                    try:
                        self.object_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, trust_repo=True)
                    except Exception as yolo_error:
                        logger.warning(f"Failed to load YOLO model: {yolo_error}")
                        # Fallback: try to load without pretrained weights
                        try:
                            self.object_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', trust_repo=True)
                        except Exception as fallback_error:
                            logger.error(f"YOLO model loading completely failed: {fallback_error}")
                            self.object_detector = None
            except Exception as e:
                logger.error(f"YOLO model loading error: {str(e)}")
                self.object_detector = None'''
        
        yolo_loading_updated = '''# Load YOLO object detection model with better error handling
            try:
                model_file = os.path.join(self.model_path, "yolov5s.pt")
                if os.path.exists(model_file):
                    self.object_detector = torch.hub.load('ultralytics/yolov5', 'custom', path=model_file)
                    logger.info("Object detection model loaded")
                else:
                    logger.warning("Object detection model not found, using default YOLO")
                    # Use a more reliable method to load YOLO
                    try:
                        self.object_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True, trust_repo=True)
                    except Exception as yolo_error:
                        logger.warning(f"Failed to load YOLO model: {yolo_error}")
                        # Fallback: try to load without pretrained weights
                        try:
                            self.object_detector = torch.hub.load('ultralytics/yolov5', 'yolov5s', trust_repo=True)
                        except Exception as fallback_error:
                            logger.warning(f"YOLO model loading failed: {fallback_error}")
                            # Use fallback if available
                            if YOLO_FALLBACK_AVAILABLE:
                                self.object_detector = yolo_fallback
                                logger.info("Using YOLO fallback for object detection")
                            else:
                                logger.error("YOLO model loading completely failed")
                                self.object_detector = None
            except Exception as e:
                logger.error(f"YOLO model loading error: {str(e)}")
                # Use fallback if available
                if YOLO_FALLBACK_AVAILABLE:
                    self.object_detector = yolo_fallback
                    logger.info("Using YOLO fallback for object detection")
                else:
                    self.object_detector = None'''
        
        content = content.replace(yolo_loading_pattern, yolo_loading_updated)
        
        # Write updated content
        with open('main.py', 'w') as f:
            f.write(content)
        
        print("✅ main.py updated with YOLO fallback support")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update main.py: {e}")
        return False

def main():
    """Main function to fix YOLO issues."""
    print("🔧 YOLO Loading Fix Script")
    print("=" * 40)
    
    # Check current installation
    if not check_yolo_installation():
        print("\n📦 Installing YOLO...")
        if not install_yolo():
            print("❌ Failed to install YOLO")
            return
    
    # Test YOLO loading
    if not test_yolo_loading():
        print("\n⚠️  YOLO loading failed, creating fallback...")
        
        # Create fallback
        if create_yolo_fallback():
            # Update main.py
            if update_main_py():
                print("\n✅ YOLO fallback system created successfully!")
                print("The application will now use a basic object detection fallback")
                print("when YOLO is not available.")
            else:
                print("❌ Failed to update main.py")
        else:
            print("❌ Failed to create YOLO fallback")
    else:
        print("\n✅ YOLO is working correctly!")
    
    print("\n🎉 YOLO fix process completed!")

if __name__ == "__main__":
    main() 