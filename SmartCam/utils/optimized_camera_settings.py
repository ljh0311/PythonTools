#!/usr/bin/env python3
"""
Optimized Camera Settings for SmartCam

This module provides optimized camera settings to fix low FPS and laggy camera feed issues.
"""

import cv2
import time
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

class OptimizedCameraSettings:
    """Optimized camera settings for better performance."""
    
    # Performance-optimized settings
    OPTIMAL_SETTINGS = {
        'resolution': (640, 480),
        'fps': 30,
        'buffer_size': 1,
        'auto_focus': False,
        'exposure': -1,  # Auto exposure
        'gain': -1,      # Auto gain
        'brightness': -1, # Auto brightness
        'contrast': -1,   # Auto contrast
    }
    
    # AI detection intervals (frames)
    AI_INTERVALS = {
        'face_detection': 5,      # Every 5 frames
        'motion_detection': 3,     # Every 3 frames  
        'object_detection': 10,    # Every 10 frames
        'enhancement': 15,         # Every 15 frames
    }
    
    @staticmethod
    def optimize_camera(camera_id: int = 0) -> Dict[str, Any]:
        """Optimize camera settings for maximum performance."""
        try:
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                raise Exception(f"Failed to open camera {camera_id}")
            
            # Get current settings
            current_settings = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'buffer_size': int(cap.get(cv2.CAP_PROP_BUFFERSIZE))
            }
            
            logger.info(f"Current camera settings: {current_settings['width']}x{current_settings['height']} @ {current_settings['fps']:.1f}fps")
            
            # Apply optimized settings
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, OptimizedCameraSettings.OPTIMAL_SETTINGS['resolution'][0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, OptimizedCameraSettings.OPTIMAL_SETTINGS['resolution'][1])
            cap.set(cv2.CAP_PROP_FPS, OptimizedCameraSettings.OPTIMAL_SETTINGS['fps'])
            cap.set(cv2.CAP_PROP_BUFFERSIZE, OptimizedCameraSettings.OPTIMAL_SETTINGS['buffer_size'])
            
            # Disable auto-focus for better performance
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            # Set auto exposure and gain
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Auto exposure
            cap.set(cv2.CAP_PROP_GAIN, -1)  # Auto gain
            
            # Verify optimized settings
            optimized_settings = {
                'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': cap.get(cv2.CAP_PROP_FPS),
                'buffer_size': int(cap.get(cv2.CAP_PROP_BUFFERSIZE))
            }
            
            logger.info(f"Optimized camera settings: {optimized_settings['width']}x{optimized_settings['height']} @ {optimized_settings['fps']:.1f}fps")
            
            cap.release()
            return optimized_settings
            
        except Exception as e:
            logger.error(f"Camera optimization failed: {e}")
            return {}
    
    @staticmethod
    def create_optimized_camera_class():
        """Create an optimized SmartCamera class with better performance."""
        
        class OptimizedSmartCamera:
            """Optimized SmartCamera with better FPS performance."""
            
            def __init__(self, camera_id: int = 0):
                self.camera_id = camera_id
                self.cap = None
                self.is_capturing = False
                self.frame_count = 0
                self.last_ai_detection = {
                    'face': 0,
                    'motion': 0,
                    'object': 0,
                    'enhancement': 0
                }
                
                # Initialize with optimized settings
                self._initialize_optimized_camera()
            
            def _initialize_optimized_camera(self):
                """Initialize camera with optimized settings."""
                try:
                    self.cap = cv2.VideoCapture(self.camera_id)
                    
                    if not self.cap.isOpened():
                        raise Exception(f"Failed to open camera {self.camera_id}")
                    
                    # Apply optimized settings
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, OptimizedCameraSettings.OPTIMAL_SETTINGS['resolution'][0])
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, OptimizedCameraSettings.OPTIMAL_SETTINGS['resolution'][1])
                    self.cap.set(cv2.CAP_PROP_FPS, OptimizedCameraSettings.OPTIMAL_SETTINGS['fps'])
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, OptimizedCameraSettings.OPTIMAL_SETTINGS['buffer_size'])
                    self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
                    
                    logger.info(f"Optimized camera {self.camera_id} initialized successfully")
                    
                except Exception as e:
                    logger.error(f"Optimized camera initialization failed: {e}")
                    raise
            
            def read_frame(self) -> Tuple[bool, any]:
                """Read frame with optimized performance."""
                if not self.cap or not self.cap.isOpened():
                    return False, None
                
                ret, frame = self.cap.read()
                self.frame_count += 1
                return ret, frame
            
            def should_run_ai_detection(self, detection_type: str) -> bool:
                """Check if AI detection should run based on frame interval."""
                interval = OptimizedCameraSettings.AI_INTERVALS.get(detection_type, 5)
                return self.frame_count % interval == 0
            
            def get_performance_info(self) -> Dict[str, Any]:
                """Get current performance information."""
                if not self.cap:
                    return {}
                
                return {
                    'resolution': (
                        int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                        int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    ),
                    'fps': self.cap.get(cv2.CAP_PROP_FPS),
                    'buffer_size': int(self.cap.get(cv2.CAP_PROP_BUFFERSIZE)),
                    'frame_count': self.frame_count
                }
            
            def cleanup(self):
                """Clean up camera resources."""
                if self.cap:
                    self.cap.release()
                    self.cap = None
        
        return OptimizedSmartCamera


def get_performance_tips() -> Dict[str, list]:
    """Get performance optimization tips."""
    return {
        'immediate_actions': [
            'Close other applications using the camera',
            'Disable auto-enhancement in SmartCam settings',
            'Disable object detection for preview',
            'Reduce face detection frequency',
            'Enable performance mode'
        ],
        'system_optimizations': [
            'Update camera drivers to latest version',
            'Use USB 3.0 port for external cameras',
            'Ensure at least 4GB RAM available',
            'Close unnecessary background applications',
            'Disable Windows camera privacy settings if needed'
        ],
        'smartcam_settings': [
            'Set resolution to 640x480',
            'Set FPS to 30',
            'Enable frame skipping',
            'Disable debug mode',
            'Reduce AI detection intervals'
        ]
    }


def apply_quick_fixes():
    """Apply quick fixes for immediate performance improvement."""
    print("🚀 SmartCam Performance Quick Fixes")
    print("=" * 40)
    
    tips = get_performance_tips()
    
    print("\n⚡ Immediate Actions:")
    for action in tips['immediate_actions']:
        print(f"  • {action}")
    
    print("\n🔧 System Optimizations:")
    for optimization in tips['system_optimizations']:
        print(f"  • {optimization}")
    
    print("\n⚙️ SmartCam Settings:")
    for setting in tips['smartcam_settings']:
        print(f"  • {setting}")
    
    print("\n💡 Quick Fix Steps:")
    print("  1. Close SmartCam application")
    print("  2. Close any other camera applications")
    print("  3. Restart SmartCam with: python launch_smartcam.py")
    print("  4. Go to Settings → Performance Mode → Enable")
    print("  5. Disable auto-enhancement and object detection")
    print("  6. Set resolution to 640x480")


if __name__ == "__main__":
    apply_quick_fixes() 