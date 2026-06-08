"""
Dynamic Obstacle Prediction using EfficientDet Object Detection
Based on INF2009_VideoAnalytics obj_detection.py
"""

import cv2
import numpy as np
import time
from typing import List, Dict, Tuple, Optional
import logging
import os
from dataclasses import dataclass
from collections import deque

# Try to import MediaPipe for object detection
try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    logging.warning("MediaPipe not available. Dynamic obstacle prediction will be disabled.")

logger = logging.getLogger(__name__)

@dataclass
class DynamicObstacle:
    """Represents a dynamic obstacle"""
    id: int
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    class_name: str
    confidence: float
    velocity: Tuple[float, float]  # dx, dy in pixels/frame
    predicted_position: Tuple[float, float]  # predicted center in next frame
    time_to_collision: Optional[float] = None  # seconds to collision with robot
    risk_level: str = "low"  # low, medium, high

class DynamicObstaclePredictor:
    """Dynamic obstacle prediction using EfficientDet"""
    
    def __init__(self, model_path: str = "efficientdet.tflite", 
                 max_results: int = 10, score_threshold: float = 0.25,
                 prediction_horizon: float = 2.0):
        """
        Initialize dynamic obstacle predictor
        
        Args:
            model_path: Path to EfficientDet model
            max_results: Maximum number of detections
            score_threshold: Minimum confidence threshold
            prediction_horizon: Time horizon for prediction (seconds)
        """
        self.model_path = model_path
        self.max_results = max_results
        self.score_threshold = score_threshold
        self.prediction_horizon = prediction_horizon
        
        # Object tracking
        self.tracked_objects = {}  # id -> DynamicObstacle
        self.next_id = 0
        self.tracking_history = {}  # id -> deque of positions
        self.max_history = 10
        
        # Robot position (assumed to be at center of frame)
        self.robot_position = (320, 240)  # pixels
        self.robot_radius = 50  # pixels
        
        # Initialize detector if MediaPipe is available
        self.detector = None
        self.detection_result_list = []
        
        if MEDIAPIPE_AVAILABLE:
            self._initialize_detector()
        else:
            logger.warning("MediaPipe not available. Using fallback motion detection.")
    
    def _initialize_detector(self):
        """Initialize MediaPipe object detector"""
        try:
            if not os.path.exists(self.model_path):
                logger.error(f"Model file not found: {self.model_path}")
                return
            
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = vision.ObjectDetectorOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.LIVE_STREAM,
                max_results=self.max_results,
                score_threshold=self.score_threshold,
                result_callback=self._save_result
            )
            self.detector = vision.ObjectDetector.create_from_options(options)
            logger.info("Dynamic obstacle predictor initialized with EfficientDet")
            
        except Exception as e:
            logger.error(f"Failed to initialize detector: {e}")
            self.detector = None
    
    def _save_result(self, result, unused_output_image, timestamp_ms):
        """Callback to save detection results"""
        self.detection_result_list.append(result)
    
    def process_frame(self, frame: np.ndarray) -> List[DynamicObstacle]:
        """
        Process frame and predict dynamic obstacles
        
        Args:
            frame: Current frame (BGR format)
            
        Returns:
            List of dynamic obstacles with predictions
        """
        if self.detector is None:
            return self._fallback_motion_detection(frame)
        
        try:
            # Convert frame for MediaPipe
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            
            # Run detection
            self.detector.detect_async(mp_image, time.time_ns() // 1_000_000)
            
            # Process results
            obstacles = []
            if self.detection_result_list:
                for detection in self.detection_result_list[0].detections:
                    obstacle = self._process_detection(detection, frame)
                    if obstacle:
                        obstacles.append(obstacle)
                
                self.detection_result_list.clear()
            
            # Update tracking and predictions
            self._update_tracking(obstacles, frame)
            
            return list(self.tracked_objects.values())
            
        except Exception as e:
            logger.error(f"Error in dynamic obstacle prediction: {e}")
            return []
    
    def _process_detection(self, detection, frame) -> Optional[DynamicObstacle]:
        """Process a single detection"""
        try:
            bbox = detection.bounding_box
            category = detection.categories[0]
            
            # Filter out non-obstacle classes (customize based on your needs)
            obstacle_classes = ['person', 'car', 'truck', 'bicycle', 'motorcycle', 'dog', 'cat']
            if category.category_name.lower() not in obstacle_classes:
                return None
            
            # Create obstacle object
            obstacle = DynamicObstacle(
                id=-1,  # Will be assigned during tracking
                bbox=(bbox.origin_x, bbox.origin_y, bbox.width, bbox.height),
                class_name=category.category_name,
                confidence=category.score
            )
            
            return obstacle
            
        except Exception as e:
            logger.error(f"Error processing detection: {e}")
            return None
    
    def _update_tracking(self, new_obstacles: List[DynamicObstacle], frame: np.ndarray):
        """Update object tracking and predictions"""
        # Match new detections with existing tracks
        matched = set()
        
        for obstacle in new_obstacles:
            best_match = None
            best_iou = 0.3  # Minimum IoU threshold
            
            for track_id, tracked_obj in self.tracked_objects.items():
                if track_id in matched:
                    continue
                
                iou = self._calculate_iou(obstacle.bbox, tracked_obj.bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_match = track_id
            
            if best_match is not None:
                # Update existing track
                self._update_track(best_match, obstacle, frame)
                matched.add(best_match)
            else:
                # Create new track
                obstacle.id = self.next_id
                self.tracked_objects[obstacle.id] = obstacle
                self.tracking_history[obstacle.id] = deque(maxlen=self.max_history)
                self.tracking_history[obstacle.id].append(self._get_center(obstacle.bbox))
                self.next_id += 1
        
        # Remove old tracks
        current_time = time.time()
        to_remove = []
        for track_id, tracked_obj in self.tracked_objects.items():
            if track_id not in matched:
                # Mark for removal if not seen recently
                to_remove.append(track_id)
        
        for track_id in to_remove:
            del self.tracked_objects[track_id]
            if track_id in self.tracking_history:
                del self.tracking_history[track_id]
        
        # Update predictions for all tracked objects
        for track_id, tracked_obj in self.tracked_objects.items():
            self._predict_obstacle_motion(tracked_obj, frame)
    
    def _update_track(self, track_id: int, new_obstacle: DynamicObstacle, frame: np.ndarray):
        """Update an existing track"""
        tracked_obj = self.tracked_objects[track_id]
        
        # Update bbox and confidence
        tracked_obj.bbox = new_obstacle.bbox
        tracked_obj.confidence = new_obstacle.confidence
        tracked_obj.class_name = new_obstacle.class_name
        
        # Update tracking history
        center = self._get_center(new_obstacle.bbox)
        self.tracking_history[track_id].append(center)
    
    def _predict_obstacle_motion(self, obstacle: DynamicObstacle, frame: np.ndarray):
        """Predict future motion of an obstacle"""
        if obstacle.id not in self.tracking_history:
            return
        
        history = self.tracking_history[obstacle.id]
        if len(history) < 2:
            return
        
        # Calculate velocity from recent positions
        recent_positions = list(history)[-5:]  # Last 5 positions
        if len(recent_positions) >= 2:
            velocities = []
            for i in range(1, len(recent_positions)):
                dx = recent_positions[i][0] - recent_positions[i-1][0]
                dy = recent_positions[i][1] - recent_positions[i-1][1]
                velocities.append((dx, dy))
            
            # Average velocity
            avg_vx = np.mean([v[0] for v in velocities])
            avg_vy = np.mean([v[1] for v in velocities])
            obstacle.velocity = (avg_vx, avg_vy)
            
            # Predict future position
            current_center = self._get_center(obstacle.bbox)
            predicted_x = current_center[0] + avg_vx * self.prediction_horizon * 30  # Assume 30 fps
            predicted_y = current_center[1] + avg_vy * self.prediction_horizon * 30
            obstacle.predicted_position = (predicted_x, predicted_y)
            
            # Calculate time to collision
            obstacle.time_to_collision = self._calculate_time_to_collision(
                current_center, obstacle.velocity, obstacle.bbox
            )
            
            # Assess risk level
            obstacle.risk_level = self._assess_risk_level(obstacle)
    
    def _calculate_iou(self, bbox1: Tuple[int, int, int, int], 
                      bbox2: Tuple[int, int, int, int]) -> float:
        """Calculate Intersection over Union between two bounding boxes"""
        x1, y1, w1, h1 = bbox1
        x2, y2, w2, h2 = bbox2
        
        # Calculate intersection
        x_left = max(x1, x2)
        y_top = max(y1, y2)
        x_right = min(x1 + w1, x2 + w2)
        y_bottom = min(y1 + h1, y2 + h2)
        
        if x_right < x_left or y_bottom < y_top:
            return 0.0
        
        intersection = (x_right - x_left) * (y_bottom - y_top)
        
        # Calculate union
        area1 = w1 * h1
        area2 = w2 * h2
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _get_center(self, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
        """Get center point of bounding box"""
        x, y, w, h = bbox
        return (x + w/2, y + h/2)
    
    def _calculate_time_to_collision(self, position: Tuple[float, float], 
                                   velocity: Tuple[float, float], 
                                   bbox: Tuple[int, int, int, int]) -> Optional[float]:
        """Calculate time to collision with robot"""
        try:
            # Simple collision detection based on distance and velocity
            distance = np.sqrt((position[0] - self.robot_position[0])**2 + 
                             (position[1] - self.robot_position[1])**2)
            
            velocity_magnitude = np.sqrt(velocity[0]**2 + velocity[1]**2)
            
            if velocity_magnitude < 0.1:  # Very slow or stationary
                return None
            
            # Approximate collision time
            collision_distance = self.robot_radius + max(bbox[2], bbox[3]) / 2
            time_to_collision = (distance - collision_distance) / velocity_magnitude
            
            return time_to_collision if time_to_collision > 0 else None
            
        except Exception:
            return None
    
    def _assess_risk_level(self, obstacle: DynamicObstacle) -> str:
        """Assess risk level of an obstacle"""
        if obstacle.time_to_collision is None:
            return "low"
        
        if obstacle.time_to_collision < 1.0:  # Less than 1 second
            return "high"
        elif obstacle.time_to_collision < 3.0:  # Less than 3 seconds
            return "medium"
        else:
            return "low"
    
    def _fallback_motion_detection(self, frame: np.ndarray) -> List[DynamicObstacle]:
        """Fallback motion detection using frame differencing"""
        if not hasattr(self, 'prev_frame'):
            self.prev_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            return []
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Calculate frame difference
        diff = cv2.absdiff(self.prev_frame, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        obstacles = []
        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Minimum area
                x, y, w, h = cv2.boundingRect(contour)
                obstacle = DynamicObstacle(
                    id=self.next_id,
                    bbox=(x, y, w, h),
                    class_name="motion",
                    confidence=0.5,
                    velocity=(0.0, 0.0),  # Default velocity
                    predicted_position=(x + w/2, y + h/2)  # Default to current center
                )
                obstacles.append(obstacle)
                self.next_id += 1
        
        self.prev_frame = gray
        return obstacles
    
    def get_status(self) -> dict:
        """Get status information"""
        return {
            'detector_available': self.detector is not None,
            'tracked_objects_count': len(self.tracked_objects),
            'mediapipe_available': MEDIAPIPE_AVAILABLE
        }
    
    def reset(self):
        """Reset dynamic obstacle predictor"""
        self.tracked_objects.clear()
        self.tracking_history.clear()
        self.next_id = 0
        if hasattr(self, 'prev_frame'):
            del self.prev_frame
        logger.info("Dynamic obstacle predictor reset") 