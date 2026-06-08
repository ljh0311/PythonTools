"""
Test script for Pathfinder and AutonomousController with 2D visualization
Supports both matplotlib and pygame visualization backends

LOGGING FEATURES:
- Default: WARNING level (clean output, no debug spam)
- Debug mode: Toggle with 'debug' command or menu option 7
- Quiet mode: ERROR level only (ultra-clean, errors only)
- Normal mode: Back to WARNING level
- All modes can be changed during runtime

USAGE:
    python test.py                    # Use matplotlib (default)
    python test.py --backend pygame   # Use pygame backend
"""

import sys
import os
import time
import threading
import numpy as np
import argparse
from enum import Enum
from abc import ABC, abstractmethod
import matplotlib
matplotlib.use('TkAgg')  # Use TkAgg backend for better compatibility
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import matplotlib.transforms as transforms
import math
import cv2
import logging
import json

# Try to import pygame, but don't fail if it's not available
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    pygame = None

# Configure logging to reduce verbosity
logging.basicConfig(
    level=logging.WARNING,  # Only show WARNING and above by default
    format='%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Set root logger to WARNING to catch any unconfigured loggers
logging.getLogger().setLevel(logging.WARNING)

# Set specific loggers to WARNING to reduce noise
logging.getLogger('src.navigation.autonomous_controller').setLevel(logging.WARNING)
logging.getLogger('src.navigation.pathfinder').setLevel(logging.WARNING)
logging.getLogger('src.hardware.sensor_manager').setLevel(logging.WARNING)
logging.getLogger('src.hardware.motor_controller').setLevel(logging.WARNING)
logging.getLogger('src.vision').setLevel(logging.WARNING)
logging.getLogger('src.core').setLevel(logging.WARNING)

# Create logger for test script
logger = logging.getLogger('test')
logger.setLevel(logging.INFO)  # Show INFO and above for test messages

def toggle_debug_logging():
    """Toggle debug logging on/off for troubleshooting"""
    current_level = logging.getLogger('src.navigation.autonomous_controller').level
    if current_level == logging.DEBUG:
        # Turn off debug logging
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('src.navigation.autonomous_controller').setLevel(logging.WARNING)
        logging.getLogger('src.navigation.pathfinder').setLevel(logging.WARNING)
        logging.getLogger('src.hardware.sensor_manager').setLevel(logging.WARNING)
        logging.getLogger('src.hardware.motor_controller').setLevel(logging.WARNING)
        logging.getLogger('src.vision').setLevel(logging.WARNING)
        logging.getLogger('src.core').setLevel(logging.WARNING)
        logger.info("Debug logging disabled")
    else:
        # Turn on debug logging
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('src.navigation.autonomous_controller').setLevel(logging.DEBUG)
        logging.getLogger('src.navigation.pathfinder').setLevel(logging.DEBUG)
        logging.getLogger('src.hardware.sensor_manager').setLevel(logging.DEBUG)
        logging.getLogger('src.hardware.motor_controller').setLevel(logging.DEBUG)
        logging.getLogger('src.vision').setLevel(logging.DEBUG)
        logging.getLogger('src.core').setLevel(logging.DEBUG)
        logger.info("Debug logging enabled")

def set_quiet_mode():
    """Set logging to ERROR level only for ultra-clean output"""
    logging.getLogger().setLevel(logging.ERROR)
    logging.getLogger('src.navigation.autonomous_controller').setLevel(logging.ERROR)
    logging.getLogger('src.navigation.pathfinder').setLevel(logging.ERROR)
    logging.getLogger('src.hardware.sensor_manager').setLevel(logging.ERROR)
    logging.getLogger('src.hardware.motor_controller').setLevel(logging.ERROR)
    logging.getLogger('src.vision').setLevel(logging.ERROR)
    logging.getLogger('src.core').setLevel(logging.ERROR)
    logger.setLevel(logging.ERROR)
    print("Quiet mode enabled - only errors will be shown")

def set_normal_mode():
    """Set logging back to normal levels"""
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('src.navigation.autonomous_controller').setLevel(logging.WARNING)
    logging.getLogger('src.navigation.pathfinder').setLevel(logging.WARNING)
    logging.getLogger('src.hardware.sensor_manager').setLevel(logging.WARNING)
    logging.getLogger('src.hardware.motor_controller').setLevel(logging.WARNING)
    logging.getLogger('src.vision').setLevel(logging.WARNING)
    logging.getLogger('src.core').setLevel(logging.WARNING)
    logger.setLevel(logging.INFO)
    print("Normal mode enabled")

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.navigation.pathfinder import Pathfinder, PathPoint, NodeType
from src.navigation.autonomous_controller import AutonomousController, NavigationState, NavigationGoal
from src.core.robot_state import RobotState, Position, SensorData
from src.core.robo_mind import RobotMind
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager, SensorReading
from src.vision.visual_odometry import VisualOdometry
from src.vision.dynamic_obstacle_predictor import DynamicObstaclePredictor
from src.vision.scene_understanding import SceneUnderstanding

plt.ion()


class VisualizationBackend(Enum):
    """Visualization backend selection"""
    MATPLOTLIB = "matplotlib"
    PYGAME = "pygame"

@dataclass
class TestConfig:
    """Configuration for testing"""
    # Map settings
    map_width: float = 9.7  # meters (sqrt(94))
    map_height: float = 9.7  # meters (sqrt(94))
    grid_size: float = 0.2   # meters
    
    # Robot settings
    robot_width: float = 0.3
    robot_length: float = 0.4
    max_speed: float = 0.83  # m/s (3 km/h)
    turn_speed: float = 0.3
    
    # Safety distances
    comfortable: float = 0.5
    warning: float = 0.3
    critical: float = 0.15
    
    # Camera settings
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    camera_fps: int = 30
    enable_camera: bool = True
    
    # Model paths
    object_detection_model: str = 'efficientdet.tflite'
    max_detections: int = 5
    detection_threshold: float = 0.25
    
    # Sensor fusion weights
    ultrasonic_weight: float = 0.6
    visual_weight: float = 0.4
    
    # Visualization options
    show_camera_feed: bool = True
    show_detections: bool = True
    show_optical_flow: bool = True
    show_motor_indicators: bool = True


class EnhancedMockMotorController:
    """Enhanced mock motor controller with realistic response curves and calibration"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False
        
        # Motor parameters
        self.max_acceleration = 0.5  # m/s²
        self.max_deceleration = 0.8  # m/s²
        self.response_time = 0.1  # seconds
        self.wheel_base = 0.25  # meters
        
        # Calibration parameters
        self.left_calibration = 1.0  # Speed multiplier
        self.right_calibration = 1.0
        self.speed_noise = 0.02  # Random noise factor
        
        # Performance tracking
        self.command_history = []
        self.last_update_time = time.time()
    
    def set_speeds(self, left: float, right: float):
        """Set target speeds with acceleration limits"""
        self.left_target = np.clip(left, -100.0, 100.0)
        self.right_target = np.clip(right, -100.0, 100.0)
        self.is_running = True
        self.last_update_time = time.time()
    
    def _update_speeds(self, dt: float):
        """Update speeds with realistic acceleration/deceleration"""
        # Calculate acceleration needed
        left_diff = self.left_target - self.left_speed
        right_diff = self.right_target - self.right_speed
        
        # Apply acceleration limits
        max_change = self.max_acceleration * dt * 100  # Convert to speed units
        if abs(left_diff) > max_change:
            left_diff = np.sign(left_diff) * max_change
        if abs(right_diff) > max_change:
            right_diff = np.sign(right_diff) * max_change
        
        # Apply deceleration if stopping
        if abs(self.left_target) < abs(self.left_speed):
            max_change = self.max_deceleration * dt * 100
            if abs(left_diff) > max_change:
                left_diff = np.sign(left_diff) * max_change
        if abs(self.right_target) < abs(self.right_speed):
            max_change = self.max_deceleration * dt * 100
            if abs(right_diff) > max_change:
                right_diff = np.sign(right_diff) * max_change
        
        # Update speeds with calibration and noise
        self.left_speed += left_diff * self.left_calibration
        self.right_speed += right_diff * self.right_calibration
        
        # Add realistic noise
        # Use correlated noise when moving straight to prevent drift
        if abs(self.left_target - self.right_target) < 0.1:  # Moving straight
            # Use same noise for both motors to prevent drift
            noise = np.random.normal(0, self.speed_noise)
            self.left_speed += noise
            self.right_speed += noise
        else:
            # Independent noise for turning maneuvers
            self.left_speed += np.random.normal(0, self.speed_noise)
            self.right_speed += np.random.normal(0, self.speed_noise)
        
        # Clip to valid range
        self.left_speed = np.clip(self.left_speed, -100.0, 100.0)
        self.right_speed = np.clip(self.right_speed, -100.0, 100.0)
        
        # Record command
        self.command_history.append((time.time(), self.left_speed, self.right_speed))
        if len(self.command_history) > 1000:
            self.command_history.pop(0)
    
    def stop(self):
        """Stop motors with deceleration"""
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False
    
    def get_speeds(self):
        """Get current speeds, updating physics if needed"""
        current_time = time.time()
        dt = current_time - self.last_update_time
        if dt > 0:
            self._update_speeds(dt)
            self.last_update_time = current_time
        return self.left_speed, self.right_speed
    
    def get_current_speeds(self):
        """Get current speeds without updating"""
        return self.left_speed, self.right_speed
    
    def emergency_stop(self):
        """Immediate emergency stop"""
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False
    
    def get_status(self):
        """Get motor status with performance metrics"""
        return {
            'left_speed': self.left_speed,
            'right_speed': self.right_speed,
            'left_target': self.left_target,
            'right_target': self.right_target,
            'running': self.is_running,
            'left_calibration': self.left_calibration,
            'right_calibration': self.right_calibration
        }
    
    def calibrate(self, left_multiplier: float = 1.0, right_multiplier: float = 1.0):
        """Calibrate motor speeds"""
        self.left_calibration = left_multiplier
        self.right_calibration = right_multiplier


# Keep old class for backward compatibility
MockMotorController = EnhancedMockMotorController


class MockSensorManager:
    """Mock sensor manager for testing with simulated obstacle detection and 360-degree LIDAR scan"""
    def __init__(self):
        self.robot_pose = (0.0, 0.0, 0.0)  # x, y, theta
        self.obstacles = []  # List of (x, y, radius)
        self.sensor_angles = {
            'front': 0.0,
            'left': math.pi / 2,
            'right': -math.pi / 2
        }
        self.max_range = 2.0  # meters
        self.lidar_num_rays = 72  # 360/5
        self.lidar_angle_step = 5  # degrees

    def set_robot_pose(self, x, y, theta):
        self.robot_pose = (x, y, theta)

    def set_obstacles(self, obstacles):
        self.obstacles = obstacles

    def _distance_to_obstacle(self, angle_offset):
        x, y, theta = self.robot_pose
        angle = theta + angle_offset
        min_dist = self.max_range
        for ox, oy, r in self.obstacles:
            dx = math.cos(angle)
            dy = math.sin(angle)
            fx = ox - x
            fy = oy - y
            proj = fx * dx + fy * dy
            if proj < 0:
                continue
            closest_x = x + proj * dx
            closest_y = y + proj * dy
            dist_to_center = math.hypot(closest_x - ox, closest_y - oy)
            if dist_to_center < r:
                dist = proj - math.sqrt(r**2 - dist_to_center**2)
                if 0 < dist < min_dist:
                    min_dist = dist
        return min_dist

    def get_lidar_scan(self):
        x, y, theta = self.robot_pose
        scan = []
        for i in range(self.lidar_num_rays):
            angle_deg = i * self.lidar_angle_step
            angle_rad = math.radians(angle_deg)
            dist = self._distance_to_obstacle(angle_rad)
            scan.append((angle_deg, dist))
        return scan

    def get_sensor_data(self):
        readings = {}
        for name, angle in self.sensor_angles.items():
            dist = self._distance_to_obstacle(angle)
            readings[name] = SensorReading(value=dist, timestamp=time.time(), valid=True)
        # Add LIDAR scan to the returned data
        lidar_scan = self.get_lidar_scan()
        return {
            'ultrasonic': readings,
            'infrared': {'left': False, 'right': False},
            'bumper': {'left': False, 'right': False},
            'lidar_scan': lidar_scan
        }
    
    def collect(self):
        """Collect sensor data (compatibility method for RobotMind)"""
        # In a real implementation, this would trigger sensor readings
        # For mock, this is a no-op as get_sensor_data() already returns current readings
        pass


class VisualObstacleDetector:
    """Visual obstacle detection using EfficientDet model from MediaPipe"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.detector = None
        self.detection_result_list = []
        self.last_detections = []
        self.fps = 0.0
        self.frame_count = 0
        self.last_fps_time = time.time()
        
        # Try to initialize MediaPipe detector
        try:
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            
            self.mp = mp
            self.vision = vision
            
            # Check if model file exists
            model_path = config.object_detection_model
            if not os.path.exists(model_path):
                # Try to find in INF2009_VideoAnalytics directory
                alt_path = os.path.join('INF2009_VideoAnalytics', model_path)
                if os.path.exists(alt_path):
                    model_path = alt_path
                else:
                    logger.warning(f"Object detection model not found at {model_path}, visual detection disabled")
                    self.detector = None
                    return
            
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.ObjectDetectorOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.LIVE_STREAM,
                max_results=config.max_detections,
                score_threshold=config.detection_threshold,
                result_callback=self._save_result
            )
            self.detector = vision.ObjectDetector.create_from_options(options)
            logger.info("Visual obstacle detector initialized")
        except ImportError:
            logger.warning("MediaPipe not available, visual detection disabled")
            self.detector = None
        except Exception as e:
            logger.warning(f"Failed to initialize visual detector: {e}")
            self.detector = None
    
    def _save_result(self, result, unused_output_image, timestamp_ms):
        """Callback to save detection results"""
        self.detection_result_list.append(result)
    
    def detect(self, frame):
        """Detect obstacles in frame"""
        if self.detector is None or frame is None:
            return []
        
        try:
            # Convert BGR to RGB
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb_image)
            
            # Run detection
            self.detector.detect_async(mp_image, int(time.time_ns() // 1_000_000))
            
            # Process results
            detections = []
            if self.detection_result_list:
                for detection in self.detection_result_list[0].detections:
                    bbox = detection.bounding_box
                    category = detection.categories[0]
                    detections.append({
                        'bbox': (bbox.origin_x, bbox.origin_y, bbox.width, bbox.height),
                        'class': category.category_name,
                        'confidence': category.score,
                        'center': (bbox.origin_x + bbox.width/2, bbox.origin_y + bbox.height/2)
                    })
                self.detection_result_list.clear()
            
            self.last_detections = detections
            
            # Update FPS
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 1.0:
                self.fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            return detections
        except Exception as e:
            logger.error(f"Error in visual detection: {e}")
            return []
    
    def convert_to_world_coords(self, detection, camera_params):
        """Convert 2D detection to 3D world coordinates (simplified)"""
        # This is a simplified conversion - in reality would need camera calibration
        bbox = detection['bbox']
        center_x, center_y = detection['center']
        frame_width, frame_height = camera_params.get('width', 640), camera_params.get('height', 480)
        
        # Assume camera is at robot position, facing forward
        # Convert pixel coordinates to approximate world coordinates
        # This is a placeholder - real implementation would use camera intrinsics
        x_norm = (center_x / frame_width - 0.5) * 2.0  # -1 to 1
        y_norm = (center_y / frame_height - 0.5) * 2.0
        
        # Estimate distance based on bounding box size (simplified)
        bbox_area = bbox[2] * bbox[3]
        estimated_distance = max(0.3, 2.0 / (bbox_area / (frame_width * frame_height) + 0.1))
        
        return {
            'x': x_norm * estimated_distance * 0.5,  # Approximate
            'y': estimated_distance,
            'distance': estimated_distance,
            'confidence': detection['confidence']
        }


class OpticalFlowTracker:
    """Optical flow tracking for dynamic obstacle detection"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.old_gray = None
        self.mask = None
        self.p0 = None
        self.first_frame = True
        
        # Lucas-Kanade parameters
        self.feature_params = dict(
            maxCorners=100,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )
        
        # Farneback parameters
        self.step = 16
        self.flow_vectors = []
        self.moving_objects = []
    
    def initialize(self, frame):
        """Initialize with first frame"""
        if frame is None:
            return
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **self.feature_params)
        self.mask = np.zeros_like(frame)
        self.old_gray = frame_gray.copy()
        self.first_frame = False
    
    def track_lucas_kanade(self, frame):
        """Track using Lucas-Kanade optical flow"""
        if frame is None:
            return []
        
        if self.first_frame:
            self.initialize(frame)
            return []
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if self.p0 is None or len(self.p0) == 0:
            self.p0 = cv2.goodFeaturesToTrack(frame_gray, mask=None, **self.feature_params)
            if self.p0 is None:
                return []
        
        # Calculate optical flow
        p1, st, err = cv2.calcOpticalFlowPyrLK(
            self.old_gray, frame_gray, self.p0, None, **self.lk_params
        )
        
        if p1 is not None:
            # Select good points
            good_new = p1[st == 1]
            good_old = self.p0[st == 1]
            
            # Calculate flow vectors
            flow_vectors = []
            for i, (new, old) in enumerate(zip(good_new, good_old)):
                dx = new[0] - old[0]
                dy = new[1] - old[1]
                magnitude = np.sqrt(dx*dx + dy*dy)
                if magnitude > 2.0:  # Threshold for significant movement
                    flow_vectors.append({
                        'start': (old[0], old[1]),
                        'end': (new[0], new[1]),
                        'magnitude': magnitude,
                        'direction': np.arctan2(dy, dx)
                    })
            
            # Update for next frame
            self.old_gray = frame_gray.copy()
            self.p0 = good_new.reshape(-1, 1, 2)
            
            return flow_vectors
        
        return []
    
    def track_farneback(self, frame):
        """Track using Farneback dense optical flow"""
        if frame is None:
            return []
        
        if self.first_frame:
            self.initialize(frame)
            return []
        
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = frame_gray.shape[:2]
        
        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowFarneback(
            self.old_gray, frame_gray, None,
            0.5, 3, 15, 3, 5, 1.2, 0
        )
        
        # Sample flow vectors
        y, x = np.mgrid[self.step//2:h:self.step, self.step//2:w:self.step].reshape(2, -1).astype(int)
        fx, fy = flow[y, x].T
        
        # Extract significant movements
        flow_vectors = []
        for i in range(len(x)):
            magnitude = np.sqrt(fx[i]**2 + fy[i]**2)
            if magnitude > 2.0:  # Threshold
                flow_vectors.append({
                    'start': (x[i], y[i]),
                    'end': (x[i] + int(fx[i]), y[i] + int(fy[i])),
                    'magnitude': magnitude,
                    'direction': np.arctan2(fy[i], fx[i])
                })
        
        self.old_gray = frame_gray.copy()
        return flow_vectors


class EdgeModelManager:
    """Manager for edge-optimized deep learning models"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.model = None
        self.preprocess = None
        self.classes = None
        self.fps = 0.0
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.quantize = True
        
        try:
            import torch
            from torchvision import models, transforms
            from torchvision.models.quantization import MobileNet_V2_QuantizedWeights
            
            self.torch = torch
            
            # Set quantization engine
            if self.quantize:
                try:
                    self.torch.backends.quantized.engine = "qnnpack"
                except:
                    try:
                        self.torch.backends.quantized.engine = "onednn"
                    except:
                        logger.warning("Quantization not available, using regular model")
                        self.quantize = False
            
            # Load quantized MobileNet
            if self.quantize:
                weights = MobileNet_V2_QuantizedWeights.DEFAULT
                self.model = models.quantization.mobilenet_v2(weights=weights)
            else:
                self.model = models.mobilenet_v2(pretrained=True)
            
            self.model.eval()
            
            # Setup preprocessing
            self.preprocess = transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            
            # Get class names
            if self.quantize:
                self.classes = weights.meta["categories"]
            else:
                # Load ImageNet classes
                try:
                    with open('imagenet_classes.txt', 'r') as f:
                        self.classes = [line.strip() for line in f.readlines()]
                except:
                    self.classes = [f"class_{i}" for i in range(1000)]
            
            logger.info("Edge model manager initialized")
        except ImportError:
            logger.warning("PyTorch not available, edge models disabled")
            self.model = None
        except Exception as e:
            logger.warning(f"Failed to initialize edge model: {e}")
            self.model = None
    
    def classify_scene(self, frame):
        """Classify scene using MobileNet"""
        if self.model is None or frame is None:
            return None
        
        try:
            # Resize and preprocess
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (224, 224))
            
            # Convert to PIL Image then tensor
            from PIL import Image
            pil_image = Image.fromarray(frame_resized)
            input_tensor = self.preprocess(pil_image)
            input_batch = input_tensor.unsqueeze(0)
            
            # Run inference
            with self.torch.no_grad():
                output = self.model(input_batch)
                probabilities = self.torch.nn.functional.softmax(output[0], dim=0)
                top5_prob, top5_catid = self.torch.topk(probabilities, 5)
            
            # Get top predictions
            predictions = []
            for i in range(5):
                predictions.append({
                    'class': self.classes[top5_catid[i]],
                    'confidence': top5_prob[i].item()
                })
            
            # Update FPS
            self.frame_count += 1
            current_time = time.time()
            if current_time - self.last_fps_time >= 1.0:
                self.fps = self.frame_count / (current_time - self.last_fps_time)
                self.frame_count = 0
                self.last_fps_time = current_time
            
            return predictions
        except Exception as e:
            logger.error(f"Error in scene classification: {e}")
            return None


class SensorFusionManager:
    """Fuse data from ultrasonic and visual sensors"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.ultrasonic_weight = config.ultrasonic_weight
        self.visual_weight = config.visual_weight
        self.fused_obstacles = []
        self.confidence_scores = {}
    
    def fuse_detections(self, ultrasonic_data, visual_detections, robot_pose):
        """Fuse ultrasonic and visual detections"""
        fused = []
        
        # Process ultrasonic data
        ultrasonic_obstacles = []
        if ultrasonic_data:
            for name, reading in ultrasonic_data.items():
                if reading.valid and reading.value < 2.0:  # Within range
                    angle = 0.0  # Simplified - would need actual sensor angle
                    if name == 'left':
                        angle = math.pi / 2
                    elif name == 'right':
                        angle = -math.pi / 2
                    
                    x = robot_pose[0] + reading.value * math.cos(robot_pose[2] + angle)
                    y = robot_pose[1] + reading.value * math.sin(robot_pose[2] + angle)
                    
                    ultrasonic_obstacles.append({
                        'x': x,
                        'y': y,
                        'distance': reading.value,
                        'confidence': 0.8 * self.ultrasonic_weight,
                        'source': 'ultrasonic'
                    })
        
        # Process visual detections
        visual_obstacles = []
        if visual_detections:
            for det in visual_detections:
                # Convert to world coordinates (simplified)
                world_coords = self._convert_visual_to_world(det, robot_pose)
                if world_coords:
                    visual_obstacles.append({
                        'x': world_coords['x'],
                        'y': world_coords['y'],
                        'distance': world_coords['distance'],
                        'confidence': det['confidence'] * self.visual_weight,
                        'source': 'visual',
                        'class': det['class']
                    })
        
        # Fuse detections (simple approach - cluster nearby detections)
        all_obstacles = ultrasonic_obstacles + visual_obstacles
        fused = self._cluster_obstacles(all_obstacles)
        
        self.fused_obstacles = fused
        return fused
    
    def _convert_visual_to_world(self, detection, robot_pose):
        """Convert visual detection to world coordinates"""
        # Simplified conversion - would need proper camera calibration
        bbox = detection['bbox']
        center_x, center_y = detection['center']
        
        # Estimate distance from bbox size
        bbox_area = bbox[2] * bbox[3]
        frame_area = self.config.frame_width * self.config.frame_height
        area_ratio = bbox_area / frame_area
        
        # Rough distance estimation
        estimated_distance = max(0.3, 2.0 / (area_ratio + 0.1))
        
        # Convert pixel to angle (simplified)
        x_norm = (center_x / self.config.frame_width - 0.5) * 2.0
        angle_offset = x_norm * math.pi / 6  # Assume 60 degree FOV
        
        # Convert to world coordinates
        x = robot_pose[0] + estimated_distance * math.cos(robot_pose[2] + angle_offset)
        y = robot_pose[1] + estimated_distance * math.sin(robot_pose[2] + angle_offset)
        
        return {
            'x': x,
            'y': y,
            'distance': estimated_distance
        }
    
    def _cluster_obstacles(self, obstacles, cluster_radius=0.3):
        """Cluster nearby obstacles"""
        if not obstacles:
            return []
        
        clusters = []
        used = set()
        
        for i, obs in enumerate(obstacles):
            if i in used:
                continue
            
            cluster = [obs]
            used.add(i)
            
            for j, other in enumerate(obstacles):
                if j in used or i == j:
                    continue
                
                dist = math.sqrt((obs['x'] - other['x'])**2 + (obs['y'] - other['y'])**2)
                if dist < cluster_radius:
                    cluster.append(other)
                    used.add(j)
            
            # Merge cluster
            if len(cluster) > 1:
                # Weighted average
                total_conf = sum(o['confidence'] for o in cluster)
                x_avg = sum(o['x'] * o['confidence'] for o in cluster) / total_conf
                y_avg = sum(o['y'] * o['confidence'] for o in cluster) / total_conf
                dist_avg = sum(o['distance'] * o['confidence'] for o in cluster) / total_conf
                conf_avg = min(1.0, total_conf / len(cluster))
                
                clusters.append({
                    'x': x_avg,
                    'y': y_avg,
                    'distance': dist_avg,
                    'confidence': conf_avg,
                    'source': 'fused',
                    'count': len(cluster)
                })
            else:
                clusters.append(cluster[0])
        
        return clusters


class BaseVisualizer(ABC):
    """Abstract base class for visualization backends"""
    
    def __init__(self, config: TestConfig):
        self.config = config
    
    @abstractmethod
    def update_robot_position(self, x: float, y: float, orientation: float):
        """Update robot position and orientation"""
        pass
    
    @abstractmethod
    def update_path(self, path: List[PathPoint]):
        """Update path visualization"""
        pass
    
    @abstractmethod
    def update_goal(self, x: float, y: float):
        """Update goal marker"""
        pass
    
    @abstractmethod
    def add_obstacle(self, x: float, y: float, radius: float = 0.2):
        """Add obstacle to visualization"""
        pass
    
    @abstractmethod
    def update_grid(self, grid: np.ndarray):
        """Update grid visualization"""
        pass
    
    @abstractmethod
    def update_explored(self, explored_cells, grid_size):
        """Update explored cells visualization"""
        pass
    
    @abstractmethod
    def update_lidar_rays(self, robot_x, robot_y, robot_theta, sensor_distances, sensor_angles, lidar_scan=None):
        """Update LIDAR rays visualization"""
        pass
    
    @abstractmethod
    def update_learning_data_visualization(self, learning_data, grid_size):
        """Update learning data visualization"""
        pass
    
    def update_status_text(self, status: Dict[str, Any]):
        """Update status text (optional, default no-op)"""
        pass
    
    def update_camera_feed(self, frame, detections=None, flow_vectors=None):
        """Update camera feed display (optional, default no-op)"""
        pass
    
    def update_motor_indicators(self, left_speed, right_speed, left_target, right_target):
        """Update motor control indicators (optional, default no-op)"""
        pass
    
    def draw_navmesh(self, navmesh_edges, grid_size):
        """Draw navmesh edges (optional, default no-op)"""
        pass
    
    def redraw(self, navmesh_edges=None, grid_size=None):
        """Redraw the visualization"""
        pass
    
    def handle_events(self):
        """Handle window events (optional, default returns True)"""
        return True
    
    def quit(self):
        """Clean up resources"""
        try:
            if hasattr(self, 'fig'):
                plt.close(self.fig)
            # Close all matplotlib figures
            plt.close('all')
        except Exception as e:
            logger.debug(f"Error closing matplotlib: {e}")


class MatplotlibVisualizer(BaseVisualizer):
    """Matplotlib-based visualization for navigation testing"""
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        self.config = config
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        self.robot_patch = None
        self.path_line = None
        self.goal_marker = None
        self.obstacle_patches = []
        self.lidar_rays = []
        self.explored_cells = set()
        self.explored_overlay = None
        self.stuck_overlays = []
        self.navmesh_lines = []  # Store navmesh line artists
        self.learning_overlays = []  # Store learning data overlays
        
        # Visual detection overlays
        self.detection_boxes = []
        self.flow_vectors_artists = []
        self.camera_feed_ax = None
        self.motor_indicators = []
        
        # Setup plot
        self.ax.set_xlim(0, config.map_width)
        self.ax.set_ylim(0, config.map_height)
        self.ax.set_aspect('equal')
        self.ax.grid(True, alpha=0.3)
        self.ax.set_xlabel('X (meters)')
        self.ax.set_ylabel('Y (meters)')
        self.ax.set_title('Navigation Test Visualization')
        
        # Setup camera feed subplot if enabled
        if config.show_camera_feed:
            self.camera_feed_ax = self.fig.add_subplot(2, 2, 2)
            self.camera_feed_ax.set_title('Camera Feed')
            self.camera_feed_ax.axis('off')
    
    def update_robot_position(self, x: float, y: float, orientation: float):
        # Remove old robot patch
        if self.robot_patch:
            self.robot_patch.remove()
            self.robot_patch = None
        
        robot_width = self.config.robot_width
        robot_length = self.config.robot_length
        
        # Create rectangle centered at (x, y)
        rect = patches.Rectangle(
            (x - robot_length/2, y - robot_width/2),
            robot_length, robot_width,
            angle=0,  # No angle here
            color='blue', alpha=0.7
        )
        
        t = (transforms.Affine2D()
             .rotate_around(x, y, orientation)
             + self.ax.transData)
        rect.set_transform(t)
        
        self.robot_patch = self.ax.add_patch(rect)

        # Remove old arrows (if any)
        if hasattr(self, 'robot_arrows'):
            for arrow in self.robot_arrows:
                try:
                    arrow.remove()
                except Exception:
                    pass
        self.robot_arrows = []

        # Add direction indicator (arrow)
        arrow_length = robot_length * 0.6
        arrow = self.ax.arrow(
            x, y,
            arrow_length * np.cos(orientation),
            arrow_length * np.sin(orientation),
            head_width=0.1, head_length=0.1, fc='red', ec='red'
        )
        self.robot_arrows.append(arrow)
    
    def update_path(self, path: List[PathPoint]):
        """Update path visualization"""
        # Remove old path
        if self.path_line:
            self.path_line.remove()
        
        if path:
            x_coords = [point.x for point in path]
            y_coords = [point.y for point in path]
            self.path_line, = self.ax.plot(x_coords, y_coords, 'g--', linewidth=2, alpha=0.7)
    
    def update_goal(self, x: float, y: float):
        """Update goal marker"""
        # Remove old goal
        if self.goal_marker:
            self.goal_marker.remove()
        
        self.goal_marker = self.ax.scatter(x, y, c='red', s=200, marker='*', alpha=0.8)
    
    def add_obstacle(self, x: float, y: float, radius: float = 0.2):
        """Add obstacle to visualization"""
        obstacle = patches.Circle((x, y), radius, color='black', alpha=0.6)
        self.obstacle_patches.append(obstacle)
        self.ax.add_patch(obstacle)
    
    def update_grid(self, grid: np.ndarray):
        """Update grid visualization"""
        # Clear existing grid visualization
        for patch in self.ax.patches:
            if isinstance(patch, patches.Rectangle) and patch.get_facecolor() == (0.8, 0.8, 0.8, 1.0):
                patch.remove()
        
        # Draw grid
        grid_size = self.config.grid_size
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                if grid[i, j] == NodeType.OBSTACLE.value:
                    x = j * grid_size
                    y = (grid.shape[0] - 1 - i) * grid_size
                    rect = patches.Rectangle((x, y), grid_size, grid_size, 
                                           color='gray', alpha=0.3)
                    self.ax.add_patch(rect)
    
    def update_status_text(self, status: Dict[str, Any]):
        """Update status text on plot"""
        # Remove old text
        for text in self.ax.texts:
            text.remove()
        
        # Add status text
        status_str = f"State: {status.get('navigation_state', 'Unknown')}\n"
        status_str += f"Position: ({status.get('position', {}).get('x', 0):.2f}, {status.get('position', {}).get('y', 0):.2f})\n"
        status_str += f"Speed: {status.get('speed', {}).get('linear', 0):.2f} m/s\n"
        status_str += f"Waypoints: {status.get('total_waypoints', 0)}"
        
        # Add adaptive speed information if available
        adaptive_speed = status.get('adaptive_speed', {})
        if adaptive_speed:
            status_str += f"\nSpeed Scale: {adaptive_speed.get('current_scale', 1.0):.2f}"
            status_str += f"\nDistances - F:{adaptive_speed.get('front_distance', 0):.2f} L:{adaptive_speed.get('left_distance', 0):.2f} R:{adaptive_speed.get('right_distance', 0):.2f}"
        
        # Add performance metrics
        perf = status.get('performance', {})
        if perf:
            if 'detection_fps' in perf:
                status_str += f"\nDetection FPS: {perf['detection_fps']:.1f}"
            if 'model_fps' in perf:
                status_str += f"\nModel FPS: {perf['model_fps']:.1f}"
        
        self.ax.text(0.02, 0.98, status_str, transform=self.ax.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    def update_camera_feed(self, frame, detections=None, flow_vectors=None):
        """Update camera feed display with detections and flow"""
        if not self.config.show_camera_feed or self.camera_feed_ax is None or frame is None:
            return
        
        self.camera_feed_ax.clear()
        self.camera_feed_ax.axis('off')
        
        # Convert BGR to RGB for display
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Draw detections
        if detections and self.config.show_detections:
            for det in detections:
                bbox = det['bbox']
                x, y, w, h = bbox
                cv2.rectangle(frame_rgb, (x, y), (x+w, y+h), (255, 165, 0), 2)
                label = f"{det['class']} ({det['confidence']:.2f})"
                cv2.putText(frame_rgb, label, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 165, 0), 2)
        
        # Draw optical flow
        if flow_vectors and self.config.show_optical_flow:
            for vec in flow_vectors[:20]:  # Limit to 20 for performance
                start = vec['start']
                end = vec['end']
                cv2.arrowedLine(frame_rgb, 
                               (int(start[0]), int(start[1])),
                               (int(end[0]), int(end[1])),
                               (0, 255, 0), 1, tipLength=0.3)
        
        self.camera_feed_ax.imshow(frame_rgb)
        self.camera_feed_ax.set_title('Camera Feed')
    
    def update_motor_indicators(self, left_speed, right_speed, left_target, right_target):
        """Update motor control indicators"""
        if not self.config.show_motor_indicators:
            return
        
        # Remove old indicators
        for indicator in self.motor_indicators:
            try:
                indicator.remove()
            except:
                pass
        self.motor_indicators = []
        
        # Draw motor speed bars (simplified visualization)
        # This would be better as a separate subplot, but for now add to status area
        # Could be enhanced with actual bar charts
    
    def draw_navmesh(self, navmesh_edges, grid_size):
        """Draw navmesh edges as lines between cell centers or along waypoints."""
        # Remove old navmesh lines
        for line in getattr(self, 'navmesh_lines', []):
            try:
                line.remove()
            except Exception:
                pass
        self.navmesh_lines = []
        for (from_cell, to_cell), waypoints in navmesh_edges.items():
            if waypoints and len(waypoints) > 1:
                x_coords, y_coords = zip(*waypoints)
                line, = self.ax.plot(x_coords, y_coords, color='magenta', linewidth=2, alpha=0.5, label='Navmesh Edge' if not self.navmesh_lines else None)
                self.navmesh_lines.append(line)
            else:
                # Draw a line from cell center to cell center
                fx, fy = from_cell
                tx, ty = to_cell
                fxw = (fx + 0.5) * grid_size
                fyw = (fy + 0.5) * grid_size
                txw = (tx + 0.5) * grid_size
                tyw = (ty + 0.5) * grid_size
                line, = self.ax.plot([fxw, txw], [fyw, tyw], color='magenta', linewidth=2, alpha=0.5, label='Navmesh Edge' if not self.navmesh_lines else None)
                self.navmesh_lines.append(line)

    def redraw(self, navmesh_edges=None, grid_size=None):
        """Redraw the plot, including navmesh if provided."""
        if navmesh_edges is not None and grid_size is not None:
            self.draw_navmesh(navmesh_edges, grid_size)
        # Use draw() instead of draw_idle() for explicit control
        # Only flush events occasionally to reduce lag
        self.fig.canvas.draw()
        # Flush events less frequently - only every 5th call
        if not hasattr(self, '_flush_counter'):
            self._flush_counter = 0
        self._flush_counter += 1
        if self._flush_counter >= 5:
            try:
                self.fig.canvas.flush_events()
            except Exception:
                pass  # Ignore errors during flush
            self._flush_counter = 0

    def update_explored(self, explored_cells, grid_size):
        # Remove old overlay
        if self.explored_overlay:
            self.explored_overlay.remove()
            self.explored_overlay = None
        # Draw explored cells as semi-transparent squares
        for (i, j) in explored_cells:
            rect = patches.Rectangle((j * grid_size, i * grid_size), grid_size, grid_size, color='yellow', alpha=0.2)
            self.ax.add_patch(rect)
        self.explored_overlay = rect

    def update_lidar_rays(self, robot_x, robot_y, robot_theta, sensor_distances, sensor_angles, lidar_scan=None):
        # Remove old rays
        for ray in self.lidar_rays:
            ray.remove()
        self.lidar_rays = []
        # Draw classic 3-ray LIDAR if no scan
        if lidar_scan is None:
            for name, angle_offset in sensor_angles.items():
                dist = sensor_distances.get(name, 0.0)
                end_x = robot_x + dist * np.cos(robot_theta + angle_offset)
                end_y = robot_y + dist * np.sin(robot_theta + angle_offset)
                ray, = self.ax.plot([robot_x, end_x], [robot_y, end_y], 'r-', alpha=0.5)
                self.lidar_rays.append(ray)
        else:
            # Draw all LIDAR rays from scan
            for angle_deg, dist in lidar_scan:
                angle_rad = math.radians(angle_deg)
                end_x = robot_x + dist * np.cos(robot_theta + angle_rad)
                end_y = robot_y + dist * np.sin(robot_theta + angle_rad)
                ray, = self.ax.plot([robot_x, end_x], [robot_y, end_y], 'r-', alpha=0.25)
                self.lidar_rays.append(ray)

    def update_stuck_locations(self, stuck_locations, grid_size):
        # Remove old stuck overlays
        if hasattr(self, 'stuck_overlays'):
            for rect in self.stuck_overlays:
                rect.remove()
        self.stuck_overlays = []
        for location in stuck_locations:
            # Handle both new format (dict) and old format (tuple) for backward compatibility
            if isinstance(location, dict) and 'x' in location and 'y' in location:
                x, y = location['x'], location['y']
            elif isinstance(location, (list, tuple)) and len(location) >= 2:
                x, y = float(location[0]), float(location[1])
            else:
                continue
            rect = patches.Rectangle((x - grid_size/2, y - grid_size/2), grid_size, grid_size, color='red', alpha=0.4)
            self.stuck_overlays.append(self.ax.add_patch(rect))

    def update_learning_data_visualization(self, learning_data, grid_size):
        """Update visualization for all learning data including valid paths, areas of caution, and stuck locations"""
        # Remove old overlays
        if hasattr(self, 'learning_overlays'):
            for overlay in self.learning_overlays:
                overlay.remove()
        self.learning_overlays = []
        
        # Visualize stuck locations (red)
        stuck_locations = learning_data.get('stuck_locations', [])
        for location in stuck_locations:
            # Handle both new format (dict) and old format (tuple) for backward compatibility
            if isinstance(location, dict) and 'x' in location and 'y' in location:
                x, y = location['x'], location['y']
            elif isinstance(location, (list, tuple)) and len(location) >= 2:
                x, y = float(location[0]), float(location[1])
            else:
                continue
            rect = patches.Rectangle((x - grid_size/2, y - grid_size/2), grid_size, grid_size, 
                                   color='red', alpha=0.6, label='Stuck Location' if not self.learning_overlays else None)
            self.learning_overlays.append(self.ax.add_patch(rect))
        
        # Visualize areas of caution (orange)
        areas_of_caution = learning_data.get('areas_of_caution', [])
        for (i, j) in areas_of_caution:
            x = (j + 0.5) * grid_size
            y = (i + 0.5) * grid_size
            rect = patches.Rectangle((x - grid_size/2, y - grid_size/2), grid_size, grid_size, 
                                   color='orange', alpha=0.4, label='Area of Caution' if not self.learning_overlays else None)
            self.learning_overlays.append(self.ax.add_patch(rect))
        
        # Visualize valid paths (green lines) - FIXED VERSION
        valid_paths = learning_data.get('valid_paths', {}).copy()  # Create a copy to avoid iteration error
        for path_key, path_data in valid_paths.items():
            if isinstance(path_data, list) and len(path_data) > 1:
                x_coords, y_coords = zip(*path_data)
                line, = self.ax.plot(x_coords, y_coords, color='green', linewidth=1, alpha=0.7, 
                                   label='Valid Path' if not self.learning_overlays else None)
                self.learning_overlays.append(line)
        
        # Add legend if we have overlays
        if self.learning_overlays:
            self.ax.legend(loc='upper right', bbox_to_anchor=(1, 1))


class PygameVisualizer(BaseVisualizer):
    """Pygame-based visualization for navigation testing"""
    
    def __init__(self, config: TestConfig):
        super().__init__(config)
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame is not available. Install it with: pip install pygame")
        
        self.screen_width = 800
        self.screen_height = 600
        self.margin = 50
        
        # Initialize pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Robot Navigation Test - Pygame")
        self.clock = pygame.time.Clock()
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 165, 0)
        self.GRAY = (128, 128, 128)
        self.LIGHT_GRAY = (200, 200, 200)
        self.DARK_GRAY = (64, 64, 64)
        
        # Font
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Visualization state
        self.robot_pos = (0, 0)
        self.robot_angle = 0
        self.goal_pos = None
        self.path_points = []
        self.obstacles = []
        self.grid = None
        self.explored_cells = set()
        self.lidar_rays = []
        self.learning_overlays = []
        
        # Scale factors
        self.scale_x = (self.screen_width - 2 * self.margin) / config.map_width
        self.scale_y = (self.screen_height - 2 * self.margin) / config.map_height
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates"""
        screen_x = int(x * self.scale_x + self.margin)
        screen_y = int(self.screen_height - self.margin - y * self.scale_y)
        return screen_x, screen_y
    
    def screen_to_world(self, screen_x, screen_y):
        """Convert screen coordinates to world coordinates"""
        x = (screen_x - self.margin) / self.scale_x
        y = (self.screen_height - self.margin - screen_y) / self.scale_y
        return x, y
    
    def update_robot_position(self, x: float, y: float, orientation: float):
        """Update robot position and orientation"""
        self.robot_pos = (x, y)
        self.robot_angle = orientation
    
    def update_path(self, path: List[PathPoint]):
        """Update path visualization"""
        self.path_points = [(point.x, point.y) for point in path]
    
    def update_goal(self, x: float, y: float):
        """Update goal position"""
        self.goal_pos = (x, y)
    
    def add_obstacle(self, x: float, y: float, radius: float = 0.2):
        """Add obstacle to visualization"""
        self.obstacles.append((x, y, radius))
    
    def update_grid(self, grid: np.ndarray):
        """Update grid visualization"""
        self.grid = grid
    
    def update_explored(self, explored_cells, grid_size):
        """Update explored cells visualization"""
        self.explored_cells = explored_cells
    
    def update_lidar_rays(self, robot_x, robot_y, robot_theta, sensor_distances, sensor_angles, lidar_scan=None):
        """Update LIDAR rays visualization"""
        self.lidar_rays = []
        if lidar_scan:
            for angle_deg, dist in lidar_scan:
                angle_rad = math.radians(angle_deg) + robot_theta
                end_x = robot_x + dist * math.cos(angle_rad)
                end_y = robot_y + dist * math.sin(angle_rad)
                self.lidar_rays.append((robot_x, robot_y, end_x, end_y))
    
    def update_learning_data_visualization(self, learning_data, grid_size):
        """Update visualization for learning data"""
        # Create a copy of valid_paths to avoid iteration error
        valid_paths = learning_data.get('valid_paths', {}).copy()
        
        # Visualize stuck locations (red)
        stuck_locations = learning_data.get('stuck_locations', [])
        for location in stuck_locations:
            # Handle both new format (dict) and old format (tuple) for backward compatibility
            if isinstance(location, dict) and 'x' in location and 'y' in location:
                x, y = location['x'], location['y']
            elif isinstance(location, (list, tuple)) and len(location) >= 2:
                x, y = float(location[0]), float(location[1])
            else:
                continue
            screen_x, screen_y = self.world_to_screen(x, y)
            pygame.draw.circle(self.screen, self.RED, (screen_x, screen_y), 5)
        
        # Visualize areas of caution (orange)
        areas_of_caution = learning_data.get('areas_of_caution', [])
        for (i, j) in areas_of_caution:
            x = (j + 0.5) * grid_size
            y = (i + 0.5) * grid_size
            screen_x, screen_y = self.world_to_screen(x, y)
            pygame.draw.circle(self.screen, self.ORANGE, (screen_x, screen_y), 8)
        
        # Visualize valid paths (green lines)
        for path_key, path_data in valid_paths.items():
            if isinstance(path_data, list) and len(path_data) > 1:
                points = []
                for x, y in path_data:
                    screen_x, screen_y = self.world_to_screen(x, y)
                    points.append((screen_x, screen_y))
                if len(points) > 1:
                    pygame.draw.lines(self.screen, self.GREEN, False, points, 2)
    
    def draw(self):
        """Draw the complete visualization"""
        # Clear screen
        self.screen.fill(self.WHITE)
        
        # Draw grid
        if self.grid is not None:
            self._draw_grid()
        
        # Draw explored cells
        self._draw_explored_cells()
        
        # Draw obstacles
        self._draw_obstacles()
        
        # Draw LIDAR rays
        self._draw_lidar_rays()
        
        # Draw path
        self._draw_path()
        
        # Draw goal
        if self.goal_pos:
            self._draw_goal()
        
        # Draw robot
        self._draw_robot()
        
        # Draw status text
        self._draw_status_text()
        
        # Update display
        pygame.display.flip()
    
    def _draw_grid(self):
        """Draw the navigation grid"""
        if self.grid is None:
            return
        
        rows, cols = self.grid.shape
        for i in range(rows):
            for j in range(cols):
                x = (j + 0.5) * self.config.grid_size
                y = (i + 0.5) * self.config.grid_size
                screen_x, screen_y = self.world_to_screen(x, y)
                
                if self.grid[i, j] == 2:  # Obstacle
                    pygame.draw.circle(self.screen, self.DARK_GRAY, (screen_x, screen_y), 3)
                elif self.grid[i, j] == 1:  # Explored
                    pygame.draw.circle(self.screen, self.LIGHT_GRAY, (screen_x, screen_y), 1)
    
    def _draw_explored_cells(self):
        """Draw explored cells"""
        for i, j in self.explored_cells:
            x = (j + 0.5) * self.config.grid_size
            y = (i + 0.5) * self.config.grid_size
            screen_x, screen_y = self.world_to_screen(x, y)
            pygame.draw.circle(self.screen, self.LIGHT_GRAY, (screen_x, screen_y), 2)
    
    def _draw_obstacles(self):
        """Draw obstacles"""
        for x, y, radius in self.obstacles:
            screen_x, screen_y = self.world_to_screen(x, y)
            screen_radius = int(radius * self.scale_x)
            pygame.draw.circle(self.screen, self.DARK_GRAY, (screen_x, screen_y), screen_radius)
    
    def _draw_lidar_rays(self):
        """Draw LIDAR rays"""
        for start_x, start_y, end_x, end_y in self.lidar_rays:
            start_screen = self.world_to_screen(start_x, start_y)
            end_screen = self.world_to_screen(end_x, end_y)
            pygame.draw.line(self.screen, self.BLUE, start_screen, end_screen, 1)
    
    def _draw_path(self):
        """Draw navigation path"""
        if len(self.path_points) > 1:
            screen_points = []
            for x, y in self.path_points:
                screen_x, screen_y = self.world_to_screen(x, y)
                screen_points.append((screen_x, screen_y))
            pygame.draw.lines(self.screen, self.GREEN, False, screen_points, 3)
    
    def _draw_goal(self):
        """Draw goal position"""
        if self.goal_pos:
            screen_x, screen_y = self.world_to_screen(self.goal_pos[0], self.goal_pos[1])
            pygame.draw.circle(self.screen, self.RED, (screen_x, screen_y), 10)
            pygame.draw.circle(self.screen, self.BLACK, (screen_x, screen_y), 10, 2)
    
    def _draw_robot(self):
        """Draw robot"""
        screen_x, screen_y = self.world_to_screen(self.robot_pos[0], self.robot_pos[1])
        
        # Draw robot body
        robot_width = int(self.config.robot_width * self.scale_x)
        robot_length = int(self.config.robot_length * self.scale_y)
        
        # Create a surface for the robot
        robot_surface = pygame.Surface((robot_width, robot_length), pygame.SRCALPHA)
        pygame.draw.rect(robot_surface, self.BLUE, (0, 0, robot_width, robot_length))
        pygame.draw.rect(robot_surface, self.BLACK, (0, 0, robot_width, robot_length), 2)
        
        # Rotate the robot surface
        rotated_surface = pygame.transform.rotate(robot_surface, -math.degrees(self.robot_angle))
        rotated_rect = rotated_surface.get_rect(center=(screen_x, screen_y))
        
        # Draw the robot
        self.screen.blit(rotated_surface, rotated_rect)
        
        # Draw direction indicator
        direction_length = max(robot_width, robot_length) // 2
        end_x = screen_x + direction_length * math.cos(self.robot_angle)
        end_y = screen_y - direction_length * math.sin(self.robot_angle)
        pygame.draw.line(self.screen, self.YELLOW, (screen_x, screen_y), (end_x, end_y), 3)
    
    def _draw_status_text(self):
        """Draw status text"""
        status_lines = [
            f"Robot: ({self.robot_pos[0]:.1f}, {self.robot_pos[1]:.1f})",
            f"Angle: {math.degrees(self.robot_angle):.1f}°",
            f"Grid: {self.config.grid_size}m",
            f"Scale: {self.scale_x:.1f}px/m"
        ]
        
        y_offset = 10
        for line in status_lines:
            text_surface = self.small_font.render(line, True, self.BLACK)
            self.screen.blit(text_surface, (10, y_offset))
            y_offset += 20
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
        return True
    
    def redraw(self, navmesh_edges=None, grid_size=None):
        """Redraw the visualization"""
        self.draw()
        # Note: clock.tick should be called by the caller, not here
    
    def quit(self):
        """Clean up pygame"""
        pygame.quit()


class NavigationTester:
    """Main testing class for navigation system"""
    
    def __init__(self, backend: VisualizationBackend = VisualizationBackend.MATPLOTLIB):
        self.config = TestConfig()
        self.explored_cells = set()
        self.backend = backend
        
        # Create configuration dictionary
        config_dict = {
            'navigation': {
                'grid_size': self.config.grid_size,
                'map_width': self.config.map_width,
                'map_height': self.config.map_height
            },
            'robot': {
                'width': self.config.robot_width,
                'length': self.config.robot_length,
                'max_speed': self.config.max_speed,
                'turn_speed': self.config.turn_speed,
                'safety_distances': {
                    'comfortable': self.config.comfortable,
                    'warning': self.config.warning,
                    'critical': self.config.critical
                }
            }
        }
        
        # Initialize components
        self.robot_state = RobotState(config_dict)
        self.motor_controller = EnhancedMockMotorController(self.config)
        self.sensor_manager = MockSensorManager()
        self.pathfinder = Pathfinder(config_dict)
        self.autonomous_controller = AutonomousController(
            self.robot_state, self.motor_controller, 
            self.sensor_manager, self.pathfinder
        )
        
        # Initialize visualizer based on backend
        if backend == VisualizationBackend.MATPLOTLIB:
            self.visualizer = MatplotlibVisualizer(self.config)
        elif backend == VisualizationBackend.PYGAME:
            if not PYGAME_AVAILABLE:
                logger.warning("Pygame not available, falling back to matplotlib")
                self.visualizer = MatplotlibVisualizer(self.config)
                self.backend = VisualizationBackend.MATPLOTLIB
            else:
                self.visualizer = PygameVisualizer(self.config)
        else:
            logger.warning(f"Unknown backend {backend}, using matplotlib")
            self.visualizer = MatplotlibVisualizer(self.config)
            self.backend = VisualizationBackend.MATPLOTLIB
        
        # Test state
        self.test_running = False
        self.animation = None
        self.current_test_mode = None  # Track which test mode is running
        
        # Initialize camera and visual components
        self.camera = None
        self.camera_available = False
        self.current_frame = None
        self.visual_detector = None
        self.optical_flow = None
        self.edge_model = None
        self.sensor_fusion = None
        
        if self.config.enable_camera:
            self._initialize_camera()
            self._initialize_visual_components()
        
        # Initialize vision modules if camera is available
        if self.camera_available:
            try:
                self.visual_odometry = VisualOdometry()
                self.dynamic_obstacle_predictor = DynamicObstaclePredictor()
                self.scene_understanding = SceneUnderstanding()
            except:
                self.visual_odometry = None
                self.dynamic_obstacle_predictor = None
                self.scene_understanding = None
        else:
            self.visual_odometry = None
            self.dynamic_obstacle_predictor = None
            self.scene_understanding = None
        
        # Add some test obstacles
        self._setup_test_environment()
    
    def _initialize_camera(self):
        """Check camera availability only - does not keep camera open"""
        try:
            # Open camera briefly to test availability
            test_camera = cv2.VideoCapture(self.config.camera_index)
            if test_camera.isOpened():
                ret, test_frame = test_camera.read()
                if ret:
                    self.camera_available = True
                    logger.info("Camera is available")
                else:
                    self.camera_available = False
                    logger.warning("Camera opened but cannot read frames")
            else:
                self.camera_available = False
                logger.warning("Could not open camera")
            
            # Always release the test camera - we don't keep it open
            test_camera.release()
            # Don't store camera object - it will be created when needed
            self.camera = None
        except Exception as e:
            logger.warning(f"Camera availability check failed: {e}")
            self.camera_available = False
            self.camera = None
    
    def _initialize_visual_components(self):
        """Initialize visual detection components"""
        if not self.camera_available:
            return
        
        # Initialize visual obstacle detector
        self.visual_detector = VisualObstacleDetector(self.config)
        
        # Initialize optical flow tracker
        self.optical_flow = OpticalFlowTracker(self.config)
        
        # Initialize edge model manager
        self.edge_model = EdgeModelManager(self.config)
        
        # Initialize sensor fusion
        self.sensor_fusion = SensorFusionManager(self.config)
        
        logger.info("Visual components initialized")
    
    def _start_camera(self):
        """Start camera - open VideoCapture when actually needed"""
        if not self.camera_available:
            return False
        
        if self.camera is not None and self.camera.isOpened():
            return True  # Already started
        
        try:
            self.camera = cv2.VideoCapture(self.config.camera_index)
            if self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)
                self.camera.set(cv2.CAP_PROP_FPS, self.config.camera_fps)
                logger.debug("Camera started")
                return True
            else:
                self.camera = None
                return False
        except Exception as e:
            logger.warning(f"Failed to start camera: {e}")
            self.camera = None
            return False
    
    def _stop_camera(self):
        """Stop camera - release VideoCapture when not needed"""
        if self.camera is not None:
            try:
                self.camera.release()
                logger.debug("Camera stopped")
            except Exception as e:
                logger.debug(f"Error releasing camera: {e}")
            finally:
                self.camera = None
                self.current_frame = None
    
    def _capture_frame(self):
        """Capture frame from camera - starts camera if needed"""
        if not self.camera_available:
            return None
        
        # Lazy initialization - start camera if not already started
        if self.camera is None or not self.camera.isOpened():
            if not self._start_camera():
                return None
        
        ret, frame = self.camera.read()
        if ret:
            self.current_frame = frame
            return frame
        return None
    
    def _process_visual_detection(self):
        """Process visual detection on current frame"""
        if not self.camera_available or self.current_frame is None:
            return []
        
        detections = []
        
        # Object detection
        if self.visual_detector and self.visual_detector.detector:
            detections = self.visual_detector.detect(self.current_frame)
        
        return detections
    
    def _setup_test_environment(self):
        """Setup test environment with obstacles"""
        # Add some obstacles in positions that don't block start/goal
        obstacles = [
            (3.0, 3.0, 0.3),   # Center area
            (6.0, 6.0, 0.4),   # Upper right area
            (7.0, 2.0, 0.25),  # Lower right area
            (2.0, 7.0, 0.35),  # Upper left area
            (4.0, 1.0, 0.2),   # Lower center area
            (1.0, 4.0, 0.3)    # Left center area
        ]
        
        for x, y, radius in obstacles:
            self.pathfinder.add_obstacle(x, y, radius)
            self.visualizer.add_obstacle(x, y, radius)
        
        # Update grid visualization
        self.visualizer.update_grid(self.pathfinder.grid)
        
        # Set obstacles in sensor manager
        self.sensor_manager.set_obstacles(obstacles)
    
    def test_simple_navigation(self):
        """Test simple navigation to a goal - camera disabled, path learning enabled"""
        logger.info("Testing simple navigation...")
        logger.info("Camera disabled for this test mode. Path learning is active.")
        
        # Stop camera if it's running (not needed for this test)
        self._stop_camera()
        
        # Set test mode to disable camera operations
        self.current_test_mode = 'simple_navigation'
        
        # Get initial path count for learning verification
        initial_path_count = len(self.autonomous_controller.valid_paths)
        logger.info(f"Starting with {initial_path_count} known valid paths")
        
        # Reset navigation state
        self.autonomous_controller.emergency_stop_navigation()
        time.sleep(0.1)  # Allow state to reset
        
        # Set initial robot position
        start_x, start_y = 1.0, 1.0
        goal_x, goal_y = np.random.uniform(1.0, 9.0, 2)
        
        self.reset_robot_state(start_x, start_y, 0.0)
        
        # Start navigation
        success = self.autonomous_controller.navigate_to(goal_x, goal_y)
        if not success:
            logger.error("Failed to start navigation")
            self.current_test_mode = None
            return
        
        # Run simulation
        self._run_navigation_simulation()
        
        # Log path learning results
        final_path_count = len(self.autonomous_controller.valid_paths)
        paths_learned = final_path_count - initial_path_count
        logger.info(f"Navigation completed. Learned {paths_learned} new paths (total: {final_path_count})")
        
        # Reset test mode
        self.current_test_mode = None
    
    def test_obstacle_avoidance(self):
        """Test navigation with obstacle avoidance"""
        logger.info("Testing obstacle avoidance...")
        
        # Reset navigation state
        self.autonomous_controller.emergency_stop_navigation()
        time.sleep(0.1)  # Allow state to reset
        
        # Set initial robot position
        start_x, start_y = 1.0, 5.0
        goal_x, goal_y = 9.0, 5.0
        
        self.reset_robot_state(start_x, start_y, 0.0)
        
        # Start navigation
        success = self.autonomous_controller.navigate_to(goal_x, goal_y)
        if not success:
            logger.error("Failed to start navigation")
            return
        
        # Run simulation
        self._run_navigation_simulation()
    
    def test_exploration(self):
        """Test autonomous exploration"""
        logger.info("Testing autonomous exploration...")
        
        # Reset navigation state
        self.autonomous_controller.emergency_stop_navigation()
        time.sleep(0.1)  # Allow state to reset
        
        # Set initial robot position
        start_x, start_y = 5.0, 5.0
        self.reset_robot_state(start_x, start_y, 0.0)
        
        # Start exploration
        success = self.autonomous_controller.start_exploration()
        if not success:
            logger.error("Failed to start exploration")
            return
        
        # Run simulation for exploration
        self._run_exploration_simulation()
    
    def _run_navigation_simulation(self, max_steps: int = 1000):
        """Run navigation simulation with visualization"""
        self.test_running = True
        step = 0
        
        prev_pos = self.robot_state.get_position()
        prev_time = time.time()
        
        # Timing control
        target_fps = 30.0  # Target frames per second
        frame_time = 1.0 / target_fps
        last_frame_time = time.time()
        
        # Visualization update throttling
        viz_update_interval = 3  # Update visualization every N physics steps
        last_viz_update_step = 0
        
        while self.test_running and step < max_steps:
            # Update robot state based on motor commands
            self._update_robot_physics()
            
            # Get current status
            nav_status = self.autonomous_controller.get_status()
            nav_status_detailed = self.autonomous_controller.get_navigation_status()
            robot_pos = self.robot_state.get_position()
            
            # Calculate linear speed
            curr_time = time.time()
            curr_pos = self.robot_state.get_position()
            dt = curr_time - prev_time
            if dt > 0:
                linear_speed = np.hypot(curr_pos.x - prev_pos.x, curr_pos.y - prev_pos.y) / dt
            else:
                linear_speed = 0.0
            
            # Update visualization
            self.visualizer.update_robot_position(
                robot_pos.x, robot_pos.y, robot_pos.theta
            )
            
            # Update path visualization
            if hasattr(self.autonomous_controller, 'current_path'):
                self.visualizer.update_path(self.autonomous_controller.current_path)
            
            # Update goal marker
            if nav_status.get('target_position'):
                target = nav_status['target_position']
                if target.get('x') is not None and target.get('y') is not None:
                    self.visualizer.update_goal(target['x'], target['y'])
            
            # Update status text with adaptive speed information
            status_info = {
                'navigation_state': nav_status.get('navigation_state', 'Unknown'),
                'position': {'x': robot_pos.x, 'y': robot_pos.y},
                'speed': {'linear': linear_speed},
                'total_waypoints': nav_status.get('total_waypoints', 0),
                'adaptive_speed': nav_status_detailed.get('adaptive_speed', {}),
                'performance': {}
            }
            
            # Add performance metrics
            if hasattr(self, 'visual_detector') and self.visual_detector:
                status_info['performance']['detection_fps'] = self.visual_detector.fps
            if hasattr(self, 'edge_model') and self.edge_model:
                status_info['performance']['model_fps'] = self.edge_model.fps
            
            self.visualizer.update_status_text(status_info)
            
            # Update camera feed (skip in simple navigation mode)
            if (hasattr(self, 'current_frame') and self.current_frame is not None and 
                self.current_test_mode != 'simple_navigation'):
                visual_detections = []
                flow_vectors = []
                if hasattr(self, 'visual_detector') and self.visual_detector:
                    visual_detections = self.visual_detector.last_detections
                if hasattr(self, 'optical_flow') and self.optical_flow:
                    flow_vectors = self.optical_flow.flow_vectors
                self.visualizer.update_camera_feed(
                    self.current_frame,
                    visual_detections,
                    flow_vectors
                )
            
            # Update motor indicators
            motor_status = self.motor_controller.get_status()
            self.visualizer.update_motor_indicators(
                motor_status['left_speed'],
                motor_status['right_speed'],
                motor_status.get('left_target', 0),
                motor_status.get('right_target', 0)
            )
            
            # Update learning data visualization (FIXED VERSION)
            if hasattr(self.autonomous_controller, '_load_learning_data'):
                # Get learning data from the controller
                learning_data = {
                    'stuck_locations': list(self.autonomous_controller.stuck_locations),
                    'areas_of_caution': list(self.autonomous_controller.areas_of_caution),
                    'valid_paths': self.autonomous_controller.valid_paths.copy()  # Create a copy to avoid iteration error
                }
                self.visualizer.update_learning_data_visualization(learning_data, self.config.grid_size)
            
            # Redraw (throttled for matplotlib to reduce UI lag)
            should_update_viz = (step - last_viz_update_step >= viz_update_interval) or (step == 0)
            
            if self.backend == VisualizationBackend.PYGAME:
                # Handle pygame events
                if not self.visualizer.handle_events():
                    break
                self.visualizer.redraw(self.autonomous_controller.navmesh_edges, self.config.grid_size)
            else:
                # Only update matplotlib visualization every N steps to reduce lag
                if should_update_viz:
                    self.visualizer.redraw(self.autonomous_controller.navmesh_edges, self.config.grid_size)
                    last_viz_update_step = step
            
            # Log path learning progress periodically
            if not hasattr(self, '_last_path_learning_log_time'):
                self._last_path_learning_log_time = time.time()
            if time.time() - self._last_path_learning_log_time > 5.0:  # Log every 5 seconds
                current_path_count = len(self.autonomous_controller.valid_paths)
                logger.info(f"Path learning: {current_path_count} valid paths recorded")
                self._last_path_learning_log_time = time.time()
            
            # Check if navigation is complete
            if nav_status.get('navigation_state') == 'reached_goal':
                logger.info("Navigation completed!")
                # Ensure learning data is saved
                if hasattr(self.autonomous_controller, '_save_learning_data'):
                    self.autonomous_controller._save_learning_data(force=True)
                break
            elif nav_status.get('navigation_state') == 'stuck':
                logger.warning("Navigation failed - robot is stuck")
                # Save learning data even if stuck
                if hasattr(self.autonomous_controller, '_save_learning_data'):
                    self.autonomous_controller._save_learning_data(force=True)
                break
            
            # Update prev_pos and prev_time after speed calculation
            prev_pos = curr_pos
            prev_time = curr_time
            
            # Timing control to maintain target FPS
            current_frame_time = time.time()
            elapsed = current_frame_time - last_frame_time
            sleep_time = max(0, frame_time - elapsed)
            if self.backend == VisualizationBackend.PYGAME:
                # FPS is handled by clock.tick in redraw
                if sleep_time > 0:
                    time.sleep(sleep_time * 0.5)  # Small sleep to prevent CPU spinning
            else:
                if sleep_time > 0:
                    time.sleep(sleep_time)
            last_frame_time = time.time()
            
            step += 1
        
        self.test_running = False
        
        # Final save of learning data
        if hasattr(self.autonomous_controller, '_save_learning_data'):
            self.autonomous_controller._save_learning_data(force=True)
            final_path_count = len(self.autonomous_controller.valid_paths)
            logger.info(f"Final learning data saved. Total valid paths: {final_path_count}")
        
        # Stop camera if it was running (not needed after test)
        if self.current_test_mode == 'simple_navigation':
            self._stop_camera()
        
        if self.backend == VisualizationBackend.MATPLOTLIB:
            plt.show(block=True)
    
    def _run_exploration_simulation(self, max_steps: int = 2000):
        """Run exploration simulation with systematic nearest-frontier coverage, 360° LIDAR mapping, and graph optimization."""
        self.test_running = True
        step = 0
        last_update_time = time.time()
        update_interval = 5.0  # seconds
        
        # Timing control
        target_fps = 30.0  # Target frames per second
        frame_time = 1.0 / target_fps
        last_frame_time = time.time()
        
        # Visualization update throttling
        viz_update_interval = 5  # Update visualization every N physics steps
        last_viz_update_step = 0
        explored_cells = set()
        grid_size = self.config.grid_size
        map_width = self.config.map_width
        map_height = self.config.map_height
        grid_rows = int(map_height // grid_size)
        grid_cols = int(map_width // grid_size)
        # 0: unexplored, 1: explored, 2: obstacle
        grid = np.zeros((grid_rows, grid_cols), dtype=np.uint8)
        
        def pos_to_cell(x, y):
            i = int(y // grid_size)
            j = int(x // grid_size)
            return i, j
        
        def cell_to_pos(i, j):
            return (j + 0.5) * grid_size, (i + 0.5) * grid_size
        
        def get_frontiers():
            frontiers = []
            for i in range(grid_rows):
                for j in range(grid_cols):
                    if grid[i, j] == 0:  # unexplored
                        # Check 4 neighbors for explored
                        for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                            ni, nj = i+di, j+dj
                            if 0 <= ni < grid_rows and 0 <= nj < grid_cols:
                                if grid[ni, nj] == 1:
                                    frontiers.append((i, j))
                                    break
            return frontiers
        
        def find_nearest_frontier(robot_i, robot_j, frontiers):
            min_dist = float('inf')
            nearest = None
            for fi, fj in frontiers:
                dist = abs(fi - robot_i) + abs(fj - robot_j)
                if dist < min_dist:
                    min_dist = dist
                    nearest = (fi, fj)
            return nearest
        
        # Main exploration loop
        prev_time = time.time()
        prev_pos = self.robot_state.get_position()
        goal_cell = None
        while self.test_running and step < max_steps:
            # Handle pygame events if using pygame backend
            if self.backend == VisualizationBackend.PYGAME:
                if not self.visualizer.handle_events():
                    break
            
            self._update_robot_physics()
            # Get robot position
            curr_pos = self.robot_state.get_position()
            robot_i, robot_j = pos_to_cell(curr_pos.x, curr_pos.y)
            # Use LIDAR scan to mark visible cells as explored and obstacles
            sensor_data = self.sensor_manager.get_sensor_data()
            lidar_scan = sensor_data.get('lidar_scan', [])
            for angle_deg, dist in lidar_scan:
                angle_rad = math.radians(angle_deg) + curr_pos.theta
                end_x = curr_pos.x + dist * np.cos(angle_rad)
                end_y = curr_pos.y + dist * np.sin(angle_rad)
                # Mark all cells along the ray as explored
                num_steps = int(dist / grid_size)
                for s in range(num_steps):
                    px = curr_pos.x + s * grid_size * np.cos(angle_rad)
                    py = curr_pos.y + s * grid_size * np.sin(angle_rad)
                    ci, cj = pos_to_cell(px, py)
                    if 0 <= ci < grid_rows and 0 <= cj < grid_cols:
                        if grid[ci, cj] == 0:
                            grid[ci, cj] = 1  # explored
                # Mark obstacle cell if hit
                if dist < self.sensor_manager.max_range:
                    ci, cj = pos_to_cell(end_x, end_y)
                    if 0 <= ci < grid_rows and 0 <= cj < grid_cols:
                        grid[ci, cj] = 2  # obstacle
            # Mark robot's current cell as explored
            if 0 <= robot_i < grid_rows and 0 <= robot_j < grid_cols:
                grid[robot_i, robot_j] = 1
            # Every 5 seconds, update visualization and pick new frontier goal
            now = time.time()
            if now - last_update_time >= update_interval or step == 0:
                # Find frontiers
                frontiers = get_frontiers()
                if frontiers:
                    nearest = find_nearest_frontier(robot_i, robot_j, frontiers)
                    if nearest:
                        goal_cell = nearest
                        goal_x, goal_y = cell_to_pos(*goal_cell)
                        self.autonomous_controller.navigate_to(goal_x, goal_y)
                
                # Visualization
                self.visualizer.update_grid(grid)
                self.visualizer.update_robot_position(curr_pos.x, curr_pos.y, curr_pos.theta)
                if hasattr(self.autonomous_controller, 'current_path'):
                    self.visualizer.update_path(self.autonomous_controller.current_path)
                if goal_cell:
                    goal_x, goal_y = cell_to_pos(*goal_cell)
                    self.visualizer.update_goal(goal_x, goal_y)
                
                # Status
                explored_count = np.sum(grid == 1)
                total_cells = grid_rows * grid_cols
                progress = 100.0 * explored_count / total_cells
                print(f"[Exploration Update] Progress: {progress:.1f}% | Explored: {explored_count}/{total_cells} | Obstacles: {np.sum(grid==2)} | Frontiers: {len(frontiers)}")
                # Throttled matplotlib update
                if self.backend == VisualizationBackend.MATPLOTLIB:
                    if hasattr(self.visualizer, 'fig') and self.visualizer.fig:
                        try:
                            self.visualizer.fig.canvas.draw()
                        except Exception:
                            pass  # Fallback if canvas not available
                last_update_time = now
            # Draw everything (only if not already drawn in update interval)
            if self.backend == VisualizationBackend.PYGAME:
                if not self.visualizer.handle_events():
                    break
                self.visualizer.draw()
                self.visualizer.clock.tick(60)  # 60 FPS
            else:
                # Matplotlib redraws are handled in update interval section
                pass
            
            # Stop if no more frontiers
            if not get_frontiers():
                print("Exploration complete: all reachable areas explored.")
                break
            
            # Timing control to maintain target FPS
            current_frame_time = time.time()
            elapsed = current_frame_time - last_frame_time
            sleep_time = max(0, frame_time - elapsed)
            
            if self.backend == VisualizationBackend.PYGAME:
                self.visualizer.clock.tick(60)  # 60 FPS
                if sleep_time > 0:
                    time.sleep(sleep_time * 0.5)  # Small sleep to prevent CPU spinning
            else:
                if sleep_time > 0:
                    time.sleep(sleep_time)
            last_frame_time = time.time()
            
            step += 1
    
    def _update_robot_physics(self):
        """Update robot position based on motor commands"""
        # Track timing for physics updates
        if not hasattr(self, '_last_physics_update_time'):
            self._last_physics_update_time = time.time()
        
        current_time = time.time()
        dt = current_time - self._last_physics_update_time
        self._last_physics_update_time = current_time
        
        # Clamp dt to prevent large jumps
        dt = min(dt, 0.1)  # Max 0.1 seconds per step
        
        left_speed, right_speed = self.motor_controller.get_speeds()
        
        # Debug logging (only log occasionally to avoid spam)
        if not hasattr(self, '_last_motor_log_time'):
            self._last_motor_log_time = 0
        if not hasattr(self, '_last_stopped_log_time'):
            self._last_stopped_log_time = 0
        
        if current_time - self._last_motor_log_time > 1.0:  # Log every second
            logger.debug(f"Motor speeds: L={left_speed:.2f}, R={right_speed:.2f}, dt={dt:.3f}")
            self._last_motor_log_time = current_time
        
        # Log when motor speeds are non-zero to verify commands are being set
        if (abs(left_speed) > 0.01 or abs(right_speed) > 0.01):
            if current_time - self._last_motor_log_time < 0.1:  # Log immediately when moving
                logger.info(f"Robot moving: L={left_speed:.2f}, R={right_speed:.2f}")
        
        if abs(left_speed) < 0.01 and abs(right_speed) < 0.01:
            # Log when robot is stopped to help debug
            if current_time - self._last_stopped_log_time > 5.0:  # Log every 5 seconds when stopped
                logger.debug(f"Robot stopped: motor speeds are zero")
                self._last_stopped_log_time = current_time
            return  # Robot is stopped
        
        # Capture camera frame if available and not in simple navigation mode
        if self.camera_available and self.current_test_mode != 'simple_navigation':
            self._capture_frame()
            if self.current_frame is not None:
                # Process visual detection
                visual_detections = self._process_visual_detection()
                
                # Process optical flow
                flow_vectors = []
                if self.optical_flow:
                    flow_vectors = self.optical_flow.track_lucas_kanade(self.current_frame)
                
                # Fuse sensor data
                if self.sensor_fusion:
                    current_pos = self.robot_state.get_position()
                    robot_pose = (current_pos.x, current_pos.y, current_pos.theta)
                    sensor_data = self.sensor_manager.get_sensor_data()
                    fused_obstacles = self.sensor_fusion.fuse_detections(
                        sensor_data.get('ultrasonic', {}),
                        visual_detections,
                        robot_pose
                    )
                    
                    # Add fused obstacles to pathfinder
                    for obs in fused_obstacles:
                        if obs['confidence'] > 0.5:  # Only high confidence detections
                            self.pathfinder.add_obstacle(obs['x'], obs['y'], 0.2)
        
        # Simple physics simulation
        current_pos = self.robot_state.get_position()
        
        # Convert wheel speeds to linear and angular velocities
        # Motor speeds are typically in percentage (-100 to 100) or m/s
        # Check if speeds are in percentage format (typical range -100 to 100)
        if abs(left_speed) > 1.0 or abs(right_speed) > 1.0:
            # Likely percentage format, convert to m/s (assuming max speed ~0.5 m/s)
            max_speed = 0.5  # m/s
            left_vel = (left_speed / 100.0) * max_speed
            right_vel = (right_speed / 100.0) * max_speed
        else:
            # Already in m/s format
            left_vel = left_speed
            right_vel = right_speed
        
        wheel_base = 0.25  # Distance between wheels in meters
        linear_vel = (left_vel + right_vel) / 2.0  # Average linear velocity
        angular_vel = (right_vel - left_vel) / wheel_base  # Angular velocity
        
        # Update position using actual time delta
        new_x = current_pos.x + linear_vel * np.cos(current_pos.theta) * dt
        new_y = current_pos.y + linear_vel * np.sin(current_pos.theta) * dt
        new_theta = current_pos.theta + angular_vel * dt
        
        # Debug position update
        dx = new_x - current_pos.x
        dy = new_y - current_pos.y
        movement = np.hypot(dx, dy)
        if movement > 0.001:
            # Log position updates when robot is actually moving
            if not hasattr(self, '_last_position_log_time'):
                self._last_position_log_time = 0
            if current_time - self._last_position_log_time > 0.5:  # Log every 0.5 seconds when moving
                logger.debug(f"Position update: dx={dx:.4f}, dy={dy:.4f}, movement={movement:.4f}m, linear_vel={linear_vel:.3f}m/s")
                self._last_position_log_time = current_time
        
        # Keep theta in [-pi, pi]
        new_theta = np.arctan2(np.sin(new_theta), np.cos(new_theta))
        
        # Update robot state using the correct method (relative position change)
        # Verify the position change is valid before applying
        if not (np.isnan(new_x) or np.isnan(new_y) or np.isnan(new_theta)):
            self.robot_state.update_position(new_x - current_pos.x, new_y - current_pos.y, new_theta - current_pos.theta)
        else:
            logger.error(f"Invalid position update detected: new_x={new_x}, new_y={new_y}, new_theta={new_theta}")
        
        # Update pathfinder
        self.pathfinder.update_robot_position(new_x, new_y)
        
        # Set robot pose in sensor manager
        self.sensor_manager.set_robot_pose(new_x, new_y, new_theta)
        
        # Mark explored cell
        grid_size = self.config.grid_size
        i = int(new_y // grid_size)
        j = int(new_x // grid_size)
        self.explored_cells.add((i, j))
        self.visualizer.update_explored(self.explored_cells, grid_size)
        # Visualize LIDAR rays
        sensor_data = self.sensor_manager.get_sensor_data()
        sensor_distances = {k: v.value for k, v in sensor_data['ultrasonic'].items()}
        lidar_scan = sensor_data.get('lidar_scan', None)
        self.visualizer.update_lidar_rays(new_x, new_y, new_theta, sensor_distances, self.sensor_manager.sensor_angles, lidar_scan=lidar_scan)
    
    def reset_robot_state(self, x: float, y: float, theta: float = 0.0):
        """Reset robot to a specific position"""
        self.robot_state.reset_position(x, y, theta)
        self.pathfinder.update_robot_position(x, y)
    
    def interactive_test(self):
        """Run interactive test with user input"""
        logger.info("Interactive Navigation Test")
        logger.info("Commands:")
        logger.info("  'nav x y' - Navigate to position (x, y)")
        logger.info("  'explore' - Start exploration")
        logger.info("  'stop' - Stop current navigation")
        logger.info("  'debug' - Toggle debug logging")
        logger.info("  'quiet' - Set quiet mode (errors only)")
        logger.info("  'normal' - Set normal mode")
        logger.info("  'quit' - Exit test")
        logger.info("  'obstacle x y r' - Add obstacle at (x, y) with radius r")
        logger.info("  'clear' - Clear all obstacles")
        
        self.test_running = True
        
        while self.test_running:
            try:
                command = input("Enter command: ").strip().lower()
                
                if command == 'quit':
                    self.test_running = False
                    break
                
                elif command == 'stop':
                    self.autonomous_controller.emergency_stop_navigation()
                    logger.info("Navigation stopped")
                
                elif command == 'explore':
                    self.autonomous_controller.start_exploration()
                    logger.info("Exploration started")
                    self._run_exploration_simulation()
                
                elif command.startswith('nav '):
                    parts = command.split()
                    if len(parts) == 3:
                        try:
                            x, y = float(parts[1]), float(parts[2])
                            self.autonomous_controller.navigate_to(x, y)
                            logger.info(f"Navigating to ({x}, {y})")
                            self._run_navigation_simulation()
                        except ValueError:
                            logger.error("Invalid coordinates")
                    else:
                        logger.error("Usage: nav x y")
                
                elif command.startswith('obstacle '):
                    parts = command.split()
                    if len(parts) == 4:
                        try:
                            x, y, r = float(parts[1]), float(parts[2]), float(parts[3])
                            self.pathfinder.add_obstacle(x, y, r)
                            self.visualizer.add_obstacle(x, y, r)
                            self.visualizer.update_grid(self.pathfinder.grid)
                            logger.info(f"Added obstacle at ({x}, {y}) with radius {r}")
                        except ValueError:
                            logger.error("Invalid obstacle parameters")
                    else:
                        logger.error("Usage: obstacle x y radius")
                
                elif command == 'clear':
                    # Clear obstacles (this would need to be implemented in pathfinder)
                    logger.warning("Clearing obstacles not implemented yet")
                
                elif command == 'debug':
                    toggle_debug_logging()
                
                elif command == 'quiet':
                    set_quiet_mode()
                
                elif command == 'normal':
                    set_normal_mode()
                
                elif command == 'visual':
                    self.test_visual_obstacle_avoidance()
                
                elif command == 'calibrate':
                    self.test_motor_calibration()
                
                elif command == 'fusion':
                    self.test_sensor_fusion()
                
                else:
                    logger.error("Unknown command")
                
            except KeyboardInterrupt:
                logger.info("Test interrupted")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
        
        self.test_running = False
    
    def run_demo(self):
        """Run a demonstration of all features"""
        logger.info("Running Navigation Demo...")
        
        # Demo 1: Simple navigation
        logger.info("\n=== Demo 1: Simple Navigation ===")
        self.test_simple_navigation()
        time.sleep(2)
        
        # Demo 2: Obstacle avoidance
        logger.info("\n=== Demo 2: Obstacle Avoidance ===")
        self.test_obstacle_avoidance()
        time.sleep(2)
        
        # Demo 3: Exploration
        logger.info("\n=== Demo 3: Autonomous Exploration ===")
        self.test_exploration()
        
        logger.info("\nDemo completed!")

    def test_visual_obstacle_avoidance(self):
        """Test visual obstacle avoidance (stub)"""
        logger.warning("Visual obstacle avoidance test not yet implemented")
    
    def test_motor_calibration(self):
        """Test motor calibration (stub)"""
        logger.warning("Motor calibration test not yet implemented")
    
    def test_sensor_fusion(self):
        """Test sensor fusion (stub)"""
        logger.warning("Sensor fusion test not yet implemented")
    
    def test_robot_mind(self):
        """Test RobotMind thinking, reasoning, and action execution"""
        logger.info("=" * 60)
        logger.info("Testing RobotMind - Thinking, Reasoning, and Actions")
        logger.info("=" * 60)
        
        try:
            # Initialize RobotMind with dependencies
            config_dict = {
                'robot': {
                    'name': 'TestRobot',
                    'model': 'llama3.1:8b',
                    'safety_distances': {
                        'comfortable': self.config.comfortable,
                        'warning': self.config.warning,
                        'critical': self.config.critical
                    }
                }
            }
            
            robot_mind = RobotMind(config_dict)
            
            # Set up dependencies (RobotMind expects these as attributes)
            robot_mind.robot_state = self.robot_state
            robot_mind.motor_controller = self.motor_controller
            robot_mind.sensor_manager = self.sensor_manager
            robot_mind.pathfinder = self.pathfinder
            
            logger.info("\nRobotMind initialized successfully")
            logger.info(f"Using model: {config_dict['robot']['model']}")
            
            # Test scenarios
            test_scenarios = [
                {
                    'name': 'Clear Path Forward',
                    'sensor_data': SensorData(
                        ultrasonic_front=100.0,
                        ultrasonic_left=80.0,
                        ultrasonic_right=80.0,
                        infrared_left=False,
                        infrared_right=False,
                        bumper_left=False,
                        bumper_right=False
                    )
                },
                {
                    'name': 'Obstacle Ahead',
                    'sensor_data': SensorData(
                        ultrasonic_front=15.0,  # Close obstacle
                        ultrasonic_left=50.0,
                        ultrasonic_right=50.0,
                        infrared_left=False,
                        infrared_right=False,
                        bumper_left=False,
                        bumper_right=False
                    )
                },
                {
                    'name': 'Obstacle on Left',
                    'sensor_data': SensorData(
                        ultrasonic_front=60.0,
                        ultrasonic_left=20.0,  # Close on left
                        ultrasonic_right=80.0,
                        infrared_left=True,  # Infrared also detects
                        infrared_right=False,
                        bumper_left=False,
                        bumper_right=False
                    )
                },
                {
                    'name': 'Bumper Contact',
                    'sensor_data': SensorData(
                        ultrasonic_front=5.0,
                        ultrasonic_left=10.0,
                        ultrasonic_right=10.0,
                        infrared_left=True,
                        infrared_right=True,
                        bumper_left=True,  # Bumper triggered
                        bumper_right=False
                    )
                },
                {
                    'name': 'Narrow Passage',
                    'sensor_data': SensorData(
                        ultrasonic_front=40.0,
                        ultrasonic_left=25.0,  # Narrow on both sides
                        ultrasonic_right=25.0,
                        infrared_left=False,
                        infrared_right=False,
                        bumper_left=False,
                        bumper_right=False
                    )
                }
            ]
            
            logger.info(f"\nRunning {len(test_scenarios)} test scenarios...\n")
            
            for i, scenario in enumerate(test_scenarios, 1):
                logger.info("-" * 60)
                logger.info(f"Scenario {i}: {scenario['name']}")
                logger.info("-" * 60)
                
                # Display sensor data
                sd = scenario['sensor_data']
                logger.info(f"Sensor Readings:")
                logger.info(f"  Ultrasonic Front: {sd.ultrasonic_front:.1f} cm")
                logger.info(f"  Ultrasonic Left: {sd.ultrasonic_left:.1f} cm")
                logger.info(f"  Ultrasonic Right: {sd.ultrasonic_right:.1f} cm")
                logger.info(f"  Infrared Left: {sd.infrared_left}")
                logger.info(f"  Infrared Right: {sd.infrared_right}")
                logger.info(f"  Bumper Left: {sd.bumper_left}")
                logger.info(f"  Bumper Right: {sd.bumper_right}")
                logger.info(f"  Current Position: ({self.robot_state.position.x:.2f}, {self.robot_state.position.y:.2f}, {self.robot_state.position.theta:.2f})")
                logger.info(f"  Battery Level: {self.robot_state.battery_level:.1f}%")
                logger.info(f"  Status: {self.robot_state.status.value}")
                
                # Test thinking/reasoning (using sync wrapper for compatibility)
                logger.info("\n🤔 RobotMind is thinking...")
                try:
                    reasoning_result = robot_mind.think_sync(scenario['sensor_data'])
                    
                    logger.info("\n💭 Reasoning Result:")
                    logger.info(f"  Action: {reasoning_result.get('action', 'unknown')}")
                    logger.info(f"  Reason: {reasoning_result.get('reason', 'no reason provided')}")
                    if 'parameters' in reasoning_result:
                        logger.info(f"  Parameters: {reasoning_result['parameters']}")
                    
                    # Display full JSON if available
                    import json
                    logger.info(f"\n  Full Response: {json.dumps(reasoning_result, indent=2)}")
                    
                except Exception as e:
                    logger.error(f"Error during thinking: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
                
                # Test action execution
                action = reasoning_result.get('action', 'stop')
                reason = reasoning_result.get('reason', 'No reason provided')
                
                logger.info(f"\n⚙️  Executing action: {action}")
                logger.info(f"   Based on reasoning: {reason}")
                
                try:
                    # Get motor state before action
                    left_before, right_before = self.motor_controller.get_current_speeds()
                    
                    # Execute action (pass reasoning_result to enable parameter extraction, using sync wrapper)
                    action_success = robot_mind.do_action_sync(action, reason, reasoning_result)
                    
                    # Get motor state after action
                    time.sleep(0.1)  # Small delay to let motors update
                    left_after, right_after = self.motor_controller.get_current_speeds()
                    
                    logger.info(f"   Action executed: {action_success}")
                    logger.info(f"   Motor speeds - Before: L={left_before:.1f}, R={right_before:.1f}")
                    logger.info(f"   Motor speeds - After: L={left_after:.1f}, R={right_after:.1f}")
                    
                    # Show motor status
                    motor_status = self.motor_controller.get_status()
                    logger.info(f"   Motor Status: {motor_status}")
                    
                except Exception as e:
                    logger.error(f"Error during action execution: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Small delay between scenarios
                logger.info("\n")
                time.sleep(1)
            
            logger.info("=" * 60)
            logger.info("RobotMind Testing Complete!")
            logger.info("=" * 60)
            
            # Interactive mode option
            print("\nWould you like to test with custom sensor data? (y/n): ", end='')
            try:
                response = input().strip().lower()
                if response == 'y':
                    self._interactive_robot_mind_test(robot_mind)
            except (EOFError, KeyboardInterrupt):
                logger.info("\nSkipping interactive test")
            
        except Exception as e:
            logger.error(f"Error in RobotMind test: {e}")
            import traceback
            traceback.print_exc()
    
    def _interactive_robot_mind_test(self, robot_mind: RobotMind):
        """Interactive test mode for RobotMind"""
        logger.info("\n" + "=" * 60)
        logger.info("Interactive RobotMind Test")
        logger.info("=" * 60)
        logger.info("Enter sensor values (or 'q' to quit):")
        
        try:
            while True:
                logger.info("\n--- New Test ---")
                
                # Get sensor inputs
                try:
                    front = float(input("Ultrasonic Front (cm): ").strip() or "50")
                    left = float(input("Ultrasonic Left (cm): ").strip() or "50")
                    right = float(input("Ultrasonic Right (cm): ").strip() or "50")
                    ir_left = input("Infrared Left (t/f): ").strip().lower() == 't'
                    ir_right = input("Infrared Right (t/f): ").strip().lower() == 't'
                    bumper_l = input("Bumper Left (t/f): ").strip().lower() == 't'
                    bumper_r = input("Bumper Right (t/f): ").strip().lower() == 't'
                except (ValueError, EOFError, KeyboardInterrupt):
                    logger.info("Exiting interactive test")
                    break
                
                # Create sensor data
                sensor_data = SensorData(
                    ultrasonic_front=front,
                    ultrasonic_left=left,
                    ultrasonic_right=right,
                    infrared_left=ir_left,
                    infrared_right=ir_right,
                    bumper_left=bumper_l,
                    bumper_right=bumper_r
                )
                
                # Think (using sync wrapper)
                logger.info("\n🤔 Thinking...")
                reasoning_result = robot_mind.think_sync(sensor_data)
                
                logger.info(f"\n💭 Action: {reasoning_result.get('action')}")
                logger.info(f"   Reason: {reasoning_result.get('reason')}")
                
                # Execute (using sync wrapper)
                action = reasoning_result.get('action', 'stop')
                reason = reasoning_result.get('reason', '')
                logger.info(f"\n⚙️  Executing: {action}")
                robot_mind.do_action_sync(action, reason, reasoning_result)
                
                # Show result
                left, right = self.motor_controller.get_current_speeds()
                logger.info(f"   Motor speeds: L={left:.1f}, R={right:.1f}")
                
        except (EOFError, KeyboardInterrupt):
            logger.info("\nExiting interactive test")
    
    def view_saved_learning_data(self):
        """View saved stuck locations and paths from stuck_locations.json"""
        logger.info("Loading saved learning data from stuck_locations.json...")
        
        # Get the file path (same directory as test.py, which is the project root)
        # test.py is in SmartAI/, and stuck_locations.json is also in SmartAI/
        stuck_locations_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'stuck_locations.json'
        )
        
        if not os.path.exists(stuck_locations_file):
            logger.error(f"File not found: {stuck_locations_file}")
            return
        
        try:
            with open(stuck_locations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract data
            raw_valid_paths = data.get('valid_paths', {})
            stuck_locations = data.get('stuck_locations', [])
            areas_of_caution = data.get('areas_of_caution', [])
            
            # Parse valid_paths keys (they are string representations of tuples)
            # Convert them to a format the visualizer can handle
            valid_paths = {}
            for key, path_data in raw_valid_paths.items():
                # Keys are like "((4, 4), (5, 4))" - we can use them as-is for visualization
                # The visualizer expects a dict with path data as lists of [x, y] coordinates
                valid_paths[key] = path_data
            
            logger.info(f"Loaded {len(stuck_locations)} stuck locations")
            logger.info(f"Loaded {len(valid_paths)} valid paths")
            logger.info(f"Loaded {len(areas_of_caution)} areas of caution")
            
            # Prepare learning data for visualization
            learning_data = {
                'stuck_locations': stuck_locations,
                'valid_paths': valid_paths,
                'areas_of_caution': areas_of_caution
            }
            
            # Update visualization with learning data
            self.visualizer.update_learning_data_visualization(learning_data, self.config.grid_size)
            
            # Update grid visualization
            self.visualizer.update_grid(self.pathfinder.grid)
            
            # Set up plot limits
            if hasattr(self.visualizer, 'ax'):
                self.visualizer.ax.set_xlim(0, self.config.map_width)
                self.visualizer.ax.set_ylim(0, self.config.map_height)
            
            # Update robot position to center for better view (optional)
            center_x = self.config.map_width / 2
            center_y = self.config.map_height / 2
            self.visualizer.update_robot_position(center_x, center_y, 0.0)
            
            # Add status text with statistics
            status_info = {
                'navigation_state': 'viewing_learning_data',
                'position': {'x': center_x, 'y': center_y},
                'speed': {'linear': 0.0},
                'total_waypoints': len(valid_paths),
                'stuck_locations_count': len(stuck_locations),
                'areas_of_caution_count': len(areas_of_caution)
            }
            self.visualizer.update_status_text(status_info)
            
            # Redraw
            if self.backend == VisualizationBackend.PYGAME:
                self.visualizer.draw()
                logger.info("Press ESC or close window to exit")
                logger.info(f"Displaying: {len(stuck_locations)} stuck locations (red), {len(valid_paths)} valid paths (green), {len(areas_of_caution)} areas of caution (orange)")
                # Keep window open until user closes it
                while True:
                    if not self.visualizer.handle_events():
                        break
                    self.visualizer.draw()
                    self.visualizer.clock.tick(30)
            else:
                # Matplotlib - show the plot
                self.visualizer.redraw()
                logger.info("Close the matplotlib window to exit")
                logger.info(f"Displaying: {len(stuck_locations)} stuck locations (red), {len(valid_paths)} valid paths (green), {len(areas_of_caution)} areas of caution (orange)")
                plt.show(block=True)
            
            logger.info("Learning data visualization completed")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON file: {e}")
        except Exception as e:
            logger.error(f"Error loading learning data: {e}")
            import traceback
            traceback.print_exc()

    def test_visual_odometry_and_vision_features(self):
        logger.info("Testing Visual Odometry and Vision Features...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            logger.error("Camera not available!")
            return
        
        logger.info("Press 'q' to quit test window.")
        logger.info("Press 'v' to toggle visual odometry visualization.")
        logger.info("Press 'd' to toggle dynamic obstacle visualization.")
        logger.info("Press 's' to toggle scene understanding visualization.")
        
        show_vo = True
        show_dynobs = True
        show_scene = True
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    logger.error("Failed to grab frame")
                    break
                
                # Process frame with vision modules
                display_frame = frame.copy()
                
                # Visual Odometry
                if self.visual_odometry and show_vo:
                    motion = self.visual_odometry.process_frame(frame)
                    if motion:
                        dx, dy, dtheta = motion
                        vo_status = self.visual_odometry.get_status()
                        
                        # Draw motion vector
                        center = (frame.shape[1]//2, frame.shape[0]//2)
                        end_point = (int(center[0] + dx*1000), int(center[1] + dy*1000))
                        cv2.arrowedLine(display_frame, center, end_point, (0, 255, 0), 2)
                        
                        # Display motion info
                        cv2.putText(display_frame, f"Motion: dx={dx:.3f}, dy={dy:.3f}, dtheta={dtheta:.3f}", 
                                  (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        cv2.putText(display_frame, f"Features: {vo_status['features_count']}", 
                                  (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                # Dynamic Obstacle Prediction
                if self.dynamic_obstacle_predictor and show_dynobs:
                    obstacles = self.dynamic_obstacle_predictor.process_frame(frame)
                    dynobs_status = self.dynamic_obstacle_predictor.get_status()
                    
                    for obstacle in obstacles:
                        x, y, w, h = obstacle.bbox
                        
                        # Draw bounding box with color based on risk level
                        color = (0, 0, 255) if obstacle.risk_level == "high" else (0, 165, 255) if obstacle.risk_level == "medium" else (0, 255, 0)
                        cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)
                        
                        # Draw predicted position
                        if obstacle.predicted_position:
                            pred_x, pred_y = obstacle.predicted_position
                            cv2.circle(display_frame, (int(pred_x), int(pred_y)), 5, (255, 0, 0), -1)
                            cv2.line(display_frame, (x + w//2, y + h//2), (int(pred_x), int(pred_y)), (255, 0, 0), 2)
                        
                        # Display obstacle info
                        label = f"{obstacle.class_name} ({obstacle.confidence:.2f})"
                        if obstacle.time_to_collision:
                            label += f" TTC: {obstacle.time_to_collision:.1f}s"
                        cv2.putText(display_frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    
                    cv2.putText(display_frame, f"Tracked Objects: {dynobs_status['tracked_objects_count']}", 
                              (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Scene Understanding
                if self.scene_understanding and show_scene:
                    scene_analysis = self.scene_understanding.process_frame(frame)
                    scene_status = self.scene_understanding.get_status()
                    
                    # Draw regions
                    for region in scene_analysis['regions']:
                        x, y, w, h = region.bbox
                        cv2.rectangle(display_frame, (x, y), (x + w, y + h), region.color, 2)
                        
                        # Display region info
                        label = f"{region.element_type.value} ({region.confidence:.2f})"
                        cv2.putText(display_frame, label, (x, y + h + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, region.color, 1)
                    
                    # Display navigation features
                    nav_features = scene_analysis['navigation_features']
                    cv2.putText(display_frame, f"Safe Directions: {len(nav_features['safe_directions'])}", 
                              (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    cv2.putText(display_frame, f"Recommended Speed: {nav_features['recommended_speed']:.1f}", 
                              (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    cv2.putText(display_frame, f"Clearance: {nav_features['clearance_estimate']:.1f}m", 
                              (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                # Display controls info
                cv2.putText(display_frame, "Controls: q=quit, v=VO, d=Obstacles, s=Scene", 
                          (10, display_frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                
                cv2.imshow("Vision Analysis", display_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('v'):
                    show_vo = not show_vo
                elif key == ord('d'):
                    show_dynobs = not show_dynobs
                elif key == ord('s'):
                    show_scene = not show_scene
        finally:
            # Stop autonomous controller thread before OpenCV cleanup to avoid GIL conflicts
            self.autonomous_controller.stop()
            if hasattr(self.autonomous_controller, 'control_thread'):
                self.autonomous_controller.control_thread.join(timeout=1.0)
            time.sleep(0.1)  # Brief delay for thread cleanup
            
            # Clean up OpenCV resources
            cap.release()
            cv2.destroyAllWindows()


def is_camera_available():
    try:
        cap = cv2.VideoCapture(0)
        if cap is not None and cap.isOpened():
            cap.release()
            return True
        return False
    except Exception:
        return False


def main():
    """Main function to run the test"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Navigation Test Script')
    parser.add_argument('--backend', type=str, choices=['matplotlib', 'pygame'], 
                       default='matplotlib', help='Visualization backend (default: matplotlib)')
    args = parser.parse_args()
    
    # Convert string to enum
    if args.backend == 'pygame':
        backend = VisualizationBackend.PYGAME
        if not PYGAME_AVAILABLE:
            logger.warning("Pygame not available, falling back to matplotlib")
            backend = VisualizationBackend.MATPLOTLIB
    else:
        backend = VisualizationBackend.MATPLOTLIB
    
    logger.info("Navigation Test Script")
    logger.info("=====================")
    logger.info(f"Using backend: {backend.value}")
    
    # Create tester
    tester = NavigationTester(backend=backend)
    
    # Start autonomous controller
    tester.autonomous_controller.start()
    
    camera_available = is_camera_available()
    
    try:
        # Show menu
        logger.info("\nSelect test mode:")
        logger.info("1. Simple Navigation Demo")
        logger.info("2. Obstacle Avoidance Demo")
        logger.info("3. Exploration Demo")
        logger.info("4. Full Demo (all tests)")
        logger.info("5. Interactive Mode")
        logger.info("6. Visual Obstacle Avoidance Test")
        logger.info("7. Motor Calibration Test")
        logger.info("8. Sensor Fusion Test")
        if camera_available:
            logger.info("9. RobotMind Test (Thinking & Reasoning)")
            logger.info("10. Visual Odometry & Vision Features Test")
            logger.info("11. View Saved Learning Data (Stuck Locations & Paths)")
            logger.info("12. Toggle Debug Logging")
            logger.info("13. Set Quiet Mode")
            logger.info("14. Switch Visualization Backend")
            logger.info("15. Exit")
        else:
            logger.info("9. RobotMind Test (Thinking & Reasoning)")
            logger.info("10. View Saved Learning Data (Stuck Locations & Paths)")
            logger.info("11. Toggle Debug Logging")
            logger.info("12. Set Quiet Mode")
            logger.info("13. Switch Visualization Backend")
            logger.info("14. Exit")
        
        while True:
            max_choice = '15' if camera_available else '14'
            choice = input(f"\nEnter choice (1-{max_choice}): ").strip()
            
            if choice == '1':
                tester.test_simple_navigation()
            elif choice == '2':
                tester.test_obstacle_avoidance()
            elif choice == '3':
                tester.test_exploration()
            elif choice == '4':
                tester.run_demo()
            elif choice == '5':
                tester.interactive_test()
            elif choice == '6':
                tester.test_visual_obstacle_avoidance()
            elif choice == '7':
                tester.test_motor_calibration()
            elif choice == '8':
                tester.test_sensor_fusion()
            elif (camera_available and choice == '9') or (not camera_available and choice == '9'):
                tester.test_robot_mind()
            elif camera_available and choice == '10':
                tester.test_visual_odometry_and_vision_features()
            elif (camera_available and choice == '11') or (not camera_available and choice == '10'):
                tester.view_saved_learning_data()
            elif (camera_available and choice == '12') or (not camera_available and choice == '11'):
                toggle_debug_logging()
            elif (camera_available and choice == '13') or (not camera_available and choice == '12'):
                set_quiet_mode()
            elif (camera_available and choice == '14') or (not camera_available and choice == '13'):
                # Switch backend - properly close old visualizer
                logger.info("Stopping current test and switching backend...")
                
                # Stop autonomous controller
                tester.autonomous_controller.stop()
                
                # Stop any running tests
                tester.test_running = False
                
                # Properly close old visualizer
                if hasattr(tester, 'visualizer'):
                    try:
                        tester.visualizer.quit()
                    except Exception as e:
                        logger.debug(f"Error closing visualizer: {e}")
                
                # Close matplotlib figures if switching from matplotlib
                if tester.backend == VisualizationBackend.MATPLOTLIB:
                    try:
                        plt.close('all')
                    except Exception as e:
                        logger.debug(f"Error closing matplotlib figures: {e}")
                
                # Close pygame if switching from pygame
                if tester.backend == VisualizationBackend.PYGAME and PYGAME_AVAILABLE:
                    try:
                        pygame.quit()
                    except Exception as e:
                        logger.debug(f"Error closing pygame: {e}")
                
                # Small delay to ensure cleanup completes
                import time
                time.sleep(0.5)
                
                # Create new tester with different backend
                if tester.backend == VisualizationBackend.MATPLOTLIB:
                    if PYGAME_AVAILABLE:
                        logger.info("Switching to pygame backend...")
                        tester = NavigationTester(backend=VisualizationBackend.PYGAME)
                        tester.autonomous_controller.start()
                        logger.info("Switched to pygame backend")
                    else:
                        logger.warning("Pygame not available")
                else:
                    logger.info("Switching to matplotlib backend...")
                    tester = NavigationTester(backend=VisualizationBackend.MATPLOTLIB)
                    tester.autonomous_controller.start()
                    logger.info("Switched to matplotlib backend")
            elif (camera_available and choice == '15') or (not camera_available and choice == '14'):
                break
            else:
                logger.error("Invalid choice. Please enter a valid option.")
    
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
    finally:
        # Cleanup
        tester.autonomous_controller.stop()
        # Stop camera if it's running (uses proper stop method)
        tester._stop_camera()
        if hasattr(tester.visualizer, 'quit'):
            tester.visualizer.quit()
        logger.info("Test completed")


if __name__ == "__main__":
    main()