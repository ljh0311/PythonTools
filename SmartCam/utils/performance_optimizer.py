#!/usr/bin/env python3
"""
SmartCam Performance Optimizer

This script optimizes camera performance by:
1. Adjusting camera settings for better FPS
2. Optimizing AI detection frequency
3. Implementing frame skipping for smooth preview
4. Reducing processing overhead
"""

import cv2
import time
import threading
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Optimizes SmartCam performance for better FPS and reduced lag."""
    
    def __init__(self):
        self.optimization_settings = {
            'target_fps': 30,
            'frame_skip_interval': 2,  # Process every 2nd frame for AI
            'preview_resolution': (640, 480),
            'ai_detection_interval': 5,  # Run AI detection every 5 frames
            'enable_frame_skipping': True,
            'reduce_processing_overhead': True,
            'optimize_camera_settings': True
        }
    
    def optimize_camera_settings(self, camera_id: int = 0) -> Dict[str, Any]:
        """Optimize camera settings for better performance."""
        try:
            cap = cv2.VideoCapture(camera_id)
            
            if not cap.isOpened():
                raise Exception(f"Failed to open camera {camera_id}")
            
            # Get current camera capabilities
            current_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            current_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            current_fps = cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Current camera settings: {current_width}x{current_height} @ {current_fps:.1f}fps")
            
            # Optimize camera settings
            optimized_settings = {}
            
            # Set optimal resolution for performance
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.optimization_settings['preview_resolution'][0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.optimization_settings['preview_resolution'][1])
            
            # Set optimal FPS
            cap.set(cv2.CAP_PROP_FPS, self.optimization_settings['target_fps'])
            
            # Disable auto-focus for better performance (if available)
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)
            
            # Set buffer size to minimum for lower latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Verify optimized settings
            optimized_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            optimized_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            optimized_fps = cap.get(cv2.CAP_PROP_FPS)
            
            optimized_settings = {
                'resolution': (optimized_width, optimized_height),
                'fps': optimized_fps,
                'buffer_size': 1,
                'auto_focus': False
            }
            
            logger.info(f"Optimized camera settings: {optimized_width}x{optimized_height} @ {optimized_fps:.1f}fps")
            
            cap.release()
            return optimized_settings
            
        except Exception as e:
            logger.error(f"Camera optimization failed: {e}")
            return {}
    
    def create_optimized_display_loop(self, camera, gui_instance):
        """Create an optimized display loop with better performance."""
        
        def optimized_display_loop():
            fps_counter = 0
            fps_start_time = time.time()
            frame_count = 0
            last_ai_detection_time = 0
            ai_detection_interval = self.optimization_settings['ai_detection_interval']
            
            # Performance monitoring
            frame_times = []
            max_frame_times = 30  # Keep last 30 frame times for averaging
            
            while gui_instance.is_capturing and camera:
                try:
                    loop_start_time = time.time()
                    
                    ret, frame = camera.cap.read()
                    if not ret or frame is None:
                        time.sleep(0.01)  # Short sleep on error
                        continue
                    
                    frame_count += 1
                    
                    # Frame skipping for AI processing
                    should_run_ai = (frame_count % ai_detection_interval == 0)
                    current_time = time.time()
                    
                    # Always update display frame
                    display_frame = frame.copy()
                    
                    # Run AI detection less frequently
                    if should_run_ai and (current_time - last_ai_detection_time) > 0.1:
                        try:
                            # Face detection (optimized)
                            if gui_instance.face_detection_var.get() and camera.face_analyzer:
                                faces = camera.face_analyzer.detect_faces(display_frame)
                                for face in faces:
                                    x, y, w, h = face["bbox"]
                                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            
                            # Motion detection (optimized)
                            if gui_instance.motion_detection_var.get() and camera.motion_detector:
                                motion = camera.motion_detector.detect_motion(display_frame)
                                if motion:
                                    h, w = display_frame.shape[:2]
                                    cv2.rectangle(display_frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)
                            
                            last_ai_detection_time = current_time
                            
                        except Exception as e:
                            logger.warning(f"AI detection error: {e}")
                    
                    # Update display (optimized)
                    try:
                        # Convert frame to RGB for tkinter
                        frame_rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                        
                        # Resize for display if needed
                        display_height, display_width = frame_rgb.shape[:2]
                        max_display_width = 800
                        max_display_height = 600
                        
                        if display_width > max_display_width or display_height > max_display_height:
                            scale = min(max_display_width / display_width, max_display_height / display_height)
                            new_width = int(display_width * scale)
                            new_height = int(display_height * scale)
                            frame_rgb = cv2.resize(frame_rgb, (new_width, new_height))
                        
                        # Update GUI in main thread
                        gui_instance.root.after(0, lambda: gui_instance._update_preview_frame(frame_rgb))
                        
                    except Exception as e:
                        logger.warning(f"Display update error: {e}")
                    
                    # FPS calculation
                    fps_counter += 1
                    if fps_counter >= 30:  # Update FPS every 30 frames
                        current_time = time.time()
                        elapsed_time = current_time - fps_start_time
                        fps = fps_counter / elapsed_time
                        
                        # Update FPS display
                        gui_instance.root.after(0, lambda: gui_instance._update_fps_display(fps))
                        
                        fps_counter = 0
                        fps_start_time = current_time
                    
                    # Performance monitoring
                    frame_time = time.time() - loop_start_time
                    frame_times.append(frame_time)
                    if len(frame_times) > max_frame_times:
                        frame_times.pop(0)
                    
                    # Adaptive frame skipping
                    avg_frame_time = sum(frame_times) / len(frame_times) if frame_times else 0
                    target_frame_time = 1.0 / self.optimization_settings['target_fps']
                    
                    if avg_frame_time > target_frame_time and self.optimization_settings['enable_frame_skipping']:
                        # Skip frames to maintain target FPS
                        skip_frames = max(1, int(avg_frame_time / target_frame_time) - 1)
                        for _ in range(skip_frames):
                            camera.cap.read()  # Skip frame
                    
                    # Small sleep to prevent CPU overload
                    time.sleep(0.001)
                    
                except Exception as e:
                    logger.error(f"Display loop error: {e}")
                    time.sleep(0.01)
        
        return optimized_display_loop
    
    def optimize_gui_settings(self, gui_instance):
        """Optimize GUI settings for better performance."""
        try:
            # Disable heavy processing by default
            if hasattr(gui_instance, 'auto_enhancement_var'):
                gui_instance.auto_enhancement_var.set(False)
            
            if hasattr(gui_instance, 'object_detection_var'):
                gui_instance.object_detection_var.set(False)
            
            # Enable performance mode
            if hasattr(gui_instance, 'settings'):
                gui_instance.settings['performance_mode'] = True
                gui_instance.settings['debug_mode_enabled'] = False
            
            logger.info("GUI settings optimized for performance")
            
        except Exception as e:
            logger.error(f"GUI optimization failed: {e}")
    
    def get_performance_recommendations(self) -> Dict[str, Any]:
        """Get performance optimization recommendations."""
        return {
            'camera_settings': {
                'resolution': '640x480',
                'fps': 30,
                'buffer_size': 1,
                'auto_focus': False
            },
            'ai_settings': {
                'face_detection_interval': 5,
                'motion_detection_interval': 3,
                'object_detection_interval': 10,
                'enable_enhancement': False
            },
            'gui_settings': {
                'performance_mode': True,
                'debug_mode': False,
                'frame_skipping': True
            },
            'system_recommendations': [
                'Close other applications using the camera',
                'Ensure sufficient RAM (4GB+)',
                'Use USB 3.0 for external cameras',
                'Update camera drivers',
                'Disable unnecessary AI features for preview'
            ]
        }


def apply_performance_optimizations():
    """Apply performance optimizations to SmartCam."""
    optimizer = PerformanceOptimizer()
    
    print("SmartCam Performance Optimizer")
    print("=" * 40)
    
    # Get recommendations
    recommendations = optimizer.get_performance_recommendations()
    
    print("\n📋 Performance Recommendations:")
    print("-" * 30)
    
    print("\n🎥 Camera Settings:")
    for key, value in recommendations['camera_settings'].items():
        print(f"  {key}: {value}")
    
    print("\n🤖 AI Settings:")
    for key, value in recommendations['ai_settings'].items():
        print(f"  {key}: {value}")
    
    print("\n🖥️ GUI Settings:")
    for key, value in recommendations['gui_settings'].items():
        print(f"  {key}: {value}")
    
    print("\n💡 System Recommendations:")
    for rec in recommendations['system_recommendations']:
        print(f"  • {rec}")
    
    return recommendations


if __name__ == "__main__":
    apply_performance_optimizations() 