import cv2
import numpy as np
# Lazy import torch to avoid startup errors - only import when needed
TORCH_AVAILABLE = False
try:
    import torch
    TORCH_AVAILABLE = True
except (ImportError, OSError) as e:
    # Logger not initialized yet, use print
    print(f"Warning: PyTorch not available: {e}. Object detection features will be limited.")
    TORCH_AVAILABLE = False

from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import time
import threading
import queue
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Tuple, Any
import logging

from camera_service import (
    FrameSource,
    open_capture,
    resolve_backend_preference,
)
from framing_engine import FramingEngine, FramingScore, draw_framing_overlay
from processing_profiles import ProcessingProfile, get_profile

# Optional heavy ML stack. Imported lazily so SmartCam can start on Raspberry
# Pi / minimal installs without TensorFlow / MediaPipe / sklearn / matplotlib.
try:
    import mediapipe as mp  # noqa: F401
    MEDIAPIPE_AVAILABLE = True
except (ImportError, OSError):
    MEDIAPIPE_AVAILABLE = False

try:
    import tensorflow as tf  # noqa: F401
    TENSORFLOW_AVAILABLE = True
except (ImportError, OSError):
    TENSORFLOW_AVAILABLE = False

try:
    from sklearn.cluster import KMeans  # noqa: F401
    SKLEARN_AVAILABLE = True
except (ImportError, OSError):
    SKLEARN_AVAILABLE = False

try:
    import matplotlib.pyplot as plt  # noqa: F401
    MATPLOTLIB_AVAILABLE = True
except (ImportError, OSError):
    MATPLOTLIB_AVAILABLE = False

# Import GUI components
try:
    from gui.dialogs.splash_screen import SplashScreen
    from gui.dialogs.error_dialog import show_error_dialog
    from gui.dialogs.progress_dialog import show_progress, update_progress, close_progress, is_progress_cancelled
    from utils.error_handler import handle_error, setup_global_exception_handler
    from config.settings import get_settings
    GUI_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some GUI components not available: {e}")
    GUI_COMPONENTS_AVAILABLE = False

# Windows-specific imports for camera device names
try:
    import comtypes.client
    import win32com.client
    import wmi
    WINDOWS_AVAILABLE = True
except ImportError:
    WINDOWS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_windows_camera_names() -> Dict[int, str]:
    """
    Get camera device names on Windows using WMI.
    
    Returns:
        Dictionary mapping camera ID to device name
    """
    camera_names = {}
    
    if not WINDOWS_AVAILABLE:
        return camera_names
    
    try:
        # Use WMI to get camera device names
        c = wmi.WMI()
        cameras = c.Win32_PnPEntity(PNPClass="Image")
        
        for i, camera in enumerate(cameras):
            if camera.Name and "camera" in camera.Name.lower():
                camera_names[i] = camera.Name
                
    except Exception as e:
        logger.warning(f"Failed to get Windows camera names: {str(e)}")
    
    return camera_names

class ImageQualityEnhancer:
    """AI-powered image quality enhancement using various techniques."""
    
    def __init__(self):
        self.enhancement_models = {}
        self._load_enhancement_models()
    
    def _load_enhancement_models(self):
        """Load various enhancement models."""
        try:
            # Load super-resolution model if available
            # self.enhancement_models['super_res'] = self._load_super_resolution_model()
            logger.info("Image enhancement models loaded")
        except Exception as e:
            logger.warning(f"Could not load enhancement models: {e}")
    
    def enhance_image_quality(self, image: np.ndarray, enhancement_type: str = 'auto') -> np.ndarray:
        """Enhance image quality using AI techniques."""
        enhanced = image.copy()
        
        if enhancement_type == 'auto':
            # Auto-detect and apply appropriate enhancements
            enhanced = self._auto_enhance(enhanced)
        elif enhancement_type == 'denoise':
            enhanced = self._denoise_image(enhanced)
        elif enhancement_type == 'sharpen':
            enhanced = self._sharpen_image(enhanced)
        elif enhancement_type == 'color_correction':
            enhanced = self._color_correct(enhanced)
        elif enhancement_type == 'exposure_correction':
            enhanced = self._correct_exposure(enhanced)
        elif enhancement_type == 'super_resolution':
            enhanced = self._super_resolution(enhanced)
        
        return enhanced
    
    def _auto_enhance(self, image: np.ndarray) -> np.ndarray:
        """Automatically detect and apply appropriate enhancements."""
        # Analyze image quality
        brightness = np.mean(image)
        contrast = np.std(image)
        noise_level = self._estimate_noise(image)
        
        enhanced = image.copy()
        
        # Apply enhancements based on analysis
        if brightness < 100:  # Dark image
            enhanced = self._correct_exposure(enhanced)
        
        if contrast < 50:  # Low contrast
            enhanced = self._enhance_contrast(enhanced)
        
        if noise_level > 0.1:  # Noisy image
            enhanced = self._denoise_image(enhanced)
        
        # Always apply slight sharpening
        enhanced = self._sharpen_image(enhanced)
        
        return enhanced
    
    def _estimate_noise(self, image: np.ndarray) -> float:
        """Estimate noise level in the image."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        # Apply Laplacian filter to detect edges and noise
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        noise_level = np.var(laplacian)
        
        return noise_level
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Remove noise from image using AI techniques."""
        # Use Non-local Means Denoising
        denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        return denoised
    
    def _sharpen_image(self, image: np.ndarray) -> np.ndarray:
        """Sharpen image using unsharp masking."""
        # Create unsharp mask
        gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
        sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
        return sharpened
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast using CLAHE."""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        # Merge channels and convert back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    
    def _color_correct(self, image: np.ndarray) -> np.ndarray:
        """Perform automatic color correction."""
        # White balance correction
        if hasattr(cv2, 'xphoto') and hasattr(cv2.xphoto, 'createSimpleWB'):
            corrected = cv2.xphoto.createSimpleWB().balanceWhite(image)
        else:
            # Simple gray world white balance fallback
            result = image.copy().astype(np.float32)
            avg_b = np.mean(result[:, :, 0])
            avg_g = np.mean(result[:, :, 1])
            avg_r = np.mean(result[:, :, 2])
            avg = (avg_b + avg_g + avg_r) / 3
            result[:, :, 0] = np.clip(result[:, :, 0] * (avg / avg_b), 0, 255)
            result[:, :, 1] = np.clip(result[:, :, 1] * (avg / avg_g), 0, 255)
            result[:, :, 2] = np.clip(result[:, :, 2] * (avg / avg_r), 0, 255)
            corrected = result.astype(np.uint8)
        # Color enhancement
        hsv = cv2.cvtColor(corrected, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.2)  # Increase saturation
        corrected = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        return corrected
    
    def _correct_exposure(self, image: np.ndarray) -> np.ndarray:
        """Correct exposure issues."""
        # Gamma correction
        gamma = 1.2
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
        corrected = cv2.LUT(image, table)
        
        return corrected
    
    def _super_resolution(self, image: np.ndarray) -> np.ndarray:
        """Apply super-resolution to upscale image."""
        # Simple upscaling with interpolation
        height, width = image.shape[:2]
        upscaled = cv2.resize(image, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
        
        # Apply sharpening to the upscaled image
        upscaled = self._sharpen_image(upscaled)
        
        return upscaled

class MotionDetector:
    """Advanced motion detection with AI enhancement."""
    
    def __init__(self, sensitivity: float = 0.3):
        self.sensitivity = sensitivity
        self.previous_frame = None
        self.motion_history = []
        self.motion_threshold = 25
        
    def detect_motion(self, frame: np.ndarray) -> bool:
        """Detect motion in the frame."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.previous_frame is None:
            self.previous_frame = gray
            return False
        
        # Calculate frame difference
        frame_delta = cv2.absdiff(self.previous_frame, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Dilate to fill in holes
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check for significant motion
        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > 500:  # Minimum area threshold
                motion_detected = True
                break
        
        # Update previous frame
        self.previous_frame = gray
        
        # Update motion history
        self.motion_history.append(motion_detected)
        if len(self.motion_history) > 10:
            self.motion_history.pop(0)
        
        # Return motion if detected in recent frames
        return sum(self.motion_history) >= 3

class FaceAnalyzer:
    """Advanced face analysis and recognition."""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.face_recognizer = None
        self.known_faces = {}
        
    def detect_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect faces and facial features."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        face_data = []
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(face_roi)
            
            face_info = {
                'bbox': (x, y, w, h),
                'confidence': 0.9,  # Placeholder
                'eyes_detected': len(eyes),
                'face_quality': self._assess_face_quality(face_roi)
            }
            face_data.append(face_info)
        
        return face_data
    
    def _assess_face_quality(self, face_roi: np.ndarray) -> float:
        """Assess the quality of a detected face."""
        # Calculate sharpness
        laplacian = cv2.Laplacian(face_roi, cv2.CV_64F)
        sharpness = np.var(laplacian)
        
        # Calculate brightness
        brightness = np.mean(face_roi)
        
        # Calculate contrast
        contrast = np.std(face_roi)
        
        # Combine metrics
        quality = (sharpness * 0.4 + brightness * 0.3 + contrast * 0.3) / 1000
        return min(quality, 1.0)

class AutoTagger:
    """Automatic tagging system for captured images based on detected content."""
    
    def __init__(self):
        self.tag_categories = {
            'objects': [],
            'people': [],
            'scene': [],
            'time': [],
            'motion': [],
            'quality': []
        }
    
    def generate_tags(self, frame: np.ndarray, detections: Dict[str, Any], 
                     timestamp: datetime = None) -> Dict[str, Any]:
        """
        Generate tags based on detected content and scene analysis.
        
        Args:
            frame: The image frame
            detections: Dictionary containing detection results (faces, objects, motion)
            timestamp: Optional timestamp for time-based tags
            
        Returns:
            Dictionary of tags organized by category
        """
        tags = {
            'objects': [],
            'people': [],
            'scene': [],
            'time': [],
            'motion': [],
            'quality': []
        }
        
        # Object tags
        if 'objects' in detections and detections['objects']:
            object_classes = set()
            for obj in detections['objects']:
                class_name = obj.get('class_name', '').lower()
                if class_name:
                    object_classes.add(class_name)
                    tags['objects'].append(class_name)
            
            # Add count-based tags
            if len(detections['objects']) > 5:
                tags['objects'].append('multiple_objects')
        
        # People/face tags
        if 'faces' in detections and detections['faces']:
            face_count = len(detections['faces'])
            tags['people'].append('person')
            if face_count > 1:
                tags['people'].append('multiple_people')
            tags['people'].append(f'{face_count}_people')
            
            # Face quality tags
            avg_quality = np.mean([f.get('face_quality', 0) for f in detections['faces']])
            if avg_quality > 0.7:
                tags['quality'].append('high_quality_face')
            elif avg_quality < 0.3:
                tags['quality'].append('low_quality_face')
        
        # Motion tags
        if detections.get('motion', False):
            tags['motion'].append('motion_detected')
            tags['motion'].append('activity')
        
        # Time-based tags
        if timestamp:
            hour = timestamp.hour
            if 6 <= hour < 12:
                tags['time'].append('morning')
            elif 12 <= hour < 18:
                tags['time'].append('afternoon')
            elif 18 <= hour < 22:
                tags['time'].append('evening')
            else:
                tags['time'].append('night')
        
        # Quality tags based on image analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        if brightness > 180:
            tags['quality'].append('bright')
        elif brightness < 50:
            tags['quality'].append('dark')
        
        contrast = np.std(gray)
        if contrast > 50:
            tags['quality'].append('high_contrast')
        elif contrast < 20:
            tags['quality'].append('low_contrast')
        
        # Remove empty categories
        tags = {k: list(set(v)) for k, v in tags.items() if v}
        
        return tags
    
    def get_all_tags(self, tags: Dict[str, Any]) -> List[str]:
        """Flatten tags dictionary into a single list."""
        all_tags = []
        for category, tag_list in tags.items():
            all_tags.extend(tag_list)
        return list(set(all_tags))

class SceneClassifier:
    """Classify scenes based on visual analysis."""
    
    def __init__(self):
        self.baseline_brightness = None
        self.baseline_color_profile = None
        self.frame_count = 0
    
    def classify_scene(self, frame: np.ndarray, detections: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Classify the scene type.
        
        Args:
            frame: The image frame
            detections: Optional detection results
            
        Returns:
            Dictionary with scene classifications
        """
        classifications = {}
        
        # Indoor/Outdoor classification
        classifications['location'] = self._classify_indoor_outdoor(frame)
        
        # Day/Night classification
        classifications['time_of_day'] = self._classify_day_night(frame)
        
        # Crowded/Empty classification
        classifications['crowd_level'] = self._classify_crowd_level(frame, detections)
        
        # Activity level
        classifications['activity'] = self._classify_activity(detections)
        
        return classifications
    
    def _classify_indoor_outdoor(self, frame: np.ndarray) -> str:
        """Classify if scene is indoor or outdoor based on color analysis."""
        # Convert to HSV for better color analysis
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Analyze color distribution
        # Outdoor scenes typically have more blue (sky) and green (vegetation)
        # Indoor scenes have more neutral colors and artificial lighting
        
        # Calculate color histograms
        h_hist = cv2.calcHist([hsv], [0], None, [180], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [256], [0, 256])
        v_hist = cv2.calcHist([hsv], [2], None, [256], [0, 256])
        
        # Blue/cyan range (outdoor sky indicator)
        blue_range = np.sum(h_hist[100:130])
        # Green range (outdoor vegetation indicator)
        green_range = np.sum(h_hist[40:80])
        # Saturation (outdoor scenes typically more saturated)
        avg_saturation = np.mean(s_hist)
        
        # Brightness variance (outdoor has more variance)
        brightness_variance = np.var(v_hist)
        
        # Heuristic: outdoor if high blue/green and high saturation
        outdoor_score = (blue_range + green_range) / np.sum(h_hist) + avg_saturation / 255.0
        
        if outdoor_score > 0.4 or brightness_variance > 2000:
            return 'outdoor'
        else:
            return 'indoor'
    
    def _classify_day_night(self, frame: np.ndarray) -> str:
        """Classify if scene is day or night based on brightness."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        avg_brightness = np.mean(gray)
        
        # Threshold for day/night
        if avg_brightness > 100:
            return 'day'
        elif avg_brightness < 60:
            return 'night'
        else:
            return 'dusk_dawn'
    
    def _classify_crowd_level(self, frame: np.ndarray, detections: Dict[str, Any] = None) -> str:
        """Classify crowd level based on detected objects and faces."""
        person_count = 0
        
        if detections:
            if 'faces' in detections:
                person_count += len(detections['faces'])
            if 'objects' in detections:
                # Count person objects
                for obj in detections['objects']:
                    if 'person' in obj.get('class_name', '').lower():
                        person_count += 1
        
        if person_count == 0:
            return 'empty'
        elif person_count == 1:
            return 'single_person'
        elif person_count <= 5:
            return 'few_people'
        elif person_count <= 15:
            return 'crowded'
        else:
            return 'very_crowded'
    
    def _classify_activity(self, detections: Dict[str, Any] = None) -> str:
        """Classify activity level based on motion and detections."""
        if not detections:
            return 'static'
        
        motion_level = 0
        if detections.get('motion', False):
            motion_level += 2
        
        if 'objects' in detections and detections['objects']:
            motion_level += len(detections['objects']) * 0.1
        
        if motion_level == 0:
            return 'static'
        elif motion_level < 1:
            return 'low_activity'
        elif motion_level < 3:
            return 'moderate_activity'
        else:
            return 'high_activity'

class AnomalyDetector:
    """Detect anomalies and unusual events in captured frames."""
    
    def __init__(self, baseline_frames: int = 30, sensitivity: float = 0.7):
        """
        Initialize anomaly detector.
        
        Args:
            baseline_frames: Number of frames to use for baseline
            sensitivity: Sensitivity threshold (0.0-1.0, higher = more sensitive)
        """
        self.baseline_frames = baseline_frames
        self.sensitivity = sensitivity
        self.baseline_established = False
        self.baseline_brightness = []
        self.baseline_object_patterns = []
        self.baseline_motion_patterns = []
        self.frame_history = []
    
    def update_baseline(self, frame: np.ndarray, detections: Dict[str, Any] = None):
        """Update baseline model with new frame."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        brightness = np.mean(gray)
        
        self.baseline_brightness.append(brightness)
        if len(self.baseline_brightness) > self.baseline_frames:
            self.baseline_brightness.pop(0)
        
        # Track object patterns
        if detections and 'objects' in detections:
            object_classes = [obj.get('class_name', '') for obj in detections['objects']]
            self.baseline_object_patterns.append(set(object_classes))
            if len(self.baseline_object_patterns) > self.baseline_frames:
                self.baseline_object_patterns.pop(0)
        
        # Track motion patterns
        motion_detected = detections.get('motion', False) if detections else False
        self.baseline_motion_patterns.append(motion_detected)
        if len(self.baseline_motion_patterns) > self.baseline_frames:
            self.baseline_motion_patterns.pop(0)
        
        # Mark baseline as established once we have enough frames
        if len(self.baseline_brightness) >= self.baseline_frames:
            self.baseline_established = True
    
    def detect_anomaly(self, frame: np.ndarray, detections: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Detect if current frame contains anomalies.
        
        Returns:
            Dictionary with anomaly information
        """
        if not self.baseline_established:
            self.update_baseline(frame, detections)
            return {'is_anomaly': False, 'confidence': 0.0, 'reasons': []}
        
        anomaly_info = {
            'is_anomaly': False,
            'confidence': 0.0,
            'reasons': []
        }
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_brightness = np.mean(gray)
        
        # Check brightness anomaly
        if len(self.baseline_brightness) > 0:
            avg_brightness = np.mean(self.baseline_brightness)
            std_brightness = np.std(self.baseline_brightness) if len(self.baseline_brightness) > 1 else 10
            
            brightness_diff = abs(current_brightness - avg_brightness)
            if brightness_diff > std_brightness * (2 - self.sensitivity):
                anomaly_info['is_anomaly'] = True
                anomaly_info['confidence'] += 0.3
                anomaly_info['reasons'].append('unusual_brightness')
        
        # Check object pattern anomaly
        if detections and 'objects' in detections:
            current_objects = set([obj.get('class_name', '') for obj in detections['objects']])
            
            if len(self.baseline_object_patterns) > 0:
                # Check for new object types
                baseline_object_types = set()
                for pattern in self.baseline_object_patterns:
                    baseline_object_types.update(pattern)
                
                new_objects = current_objects - baseline_object_types
                if new_objects:
                    anomaly_info['is_anomaly'] = True
                    anomaly_info['confidence'] += 0.4
                    anomaly_info['reasons'].append(f'unusual_objects: {", ".join(new_objects)}')
                
                # Check for sudden change in object count
                if len(self.baseline_object_patterns) > 5:
                    recent_counts = [len(p) for p in self.baseline_object_patterns[-10:]]
                    avg_count = np.mean(recent_counts)
                    current_count = len(current_objects)
                    
                    if abs(current_count - avg_count) > avg_count * 0.5:
                        anomaly_info['is_anomaly'] = True
                        anomaly_info['confidence'] += 0.2
                        anomaly_info['reasons'].append('unusual_object_count')
        
        # Check motion pattern anomaly
        if detections:
            current_motion = detections.get('motion', False)
            
            if len(self.baseline_motion_patterns) > 10:
                recent_motion_rate = sum(self.baseline_motion_patterns[-10:]) / 10.0
                
                # Sudden motion in previously static scene
                if not recent_motion_rate and current_motion:
                    anomaly_info['is_anomaly'] = True
                    anomaly_info['confidence'] += 0.3
                    anomaly_info['reasons'].append('sudden_motion')
                
                # Sudden stillness in previously active scene
                elif recent_motion_rate > 0.7 and not current_motion:
                    anomaly_info['is_anomaly'] = True
                    anomaly_info['confidence'] += 0.2
                    anomaly_info['reasons'].append('sudden_stillness')
        
        # Normalize confidence
        anomaly_info['confidence'] = min(anomaly_info['confidence'], 1.0)
        
        # Update baseline
        self.update_baseline(frame, detections)
        
        return anomaly_info

class SmartCamera:
    """
    AI-powered smart camera system with intelligent image and video capture capabilities.
    Features include object detection, face recognition, motion detection, and automatic capture.
    Enhanced with advanced image quality improvement techniques from INF2009 projects.
    """
    
    @staticmethod
    def detect_available_cameras(max_cameras: int = 10) -> List[Dict[str, Any]]:
        """
        Detect available cameras and return their information.
        
        Args:
            max_cameras: Maximum number of cameras to check
            
        Returns:
            List of dictionaries containing camera information
        """
        available_cameras = []
        
        # Get Windows camera names if available
        windows_camera_names = get_windows_camera_names()
        
        backend_pref = resolve_backend_preference("auto")
        for camera_id in range(max_cameras):
            try:
                cap, _ = open_capture(camera_id, backend_pref)
                if cap is not None and cap.isOpened():
                    # Get camera properties
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    # Try to get a test frame
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Try to get camera name (platform dependent)
                        camera_name = f"Camera {camera_id}"
                        
                        # Use Windows camera name if available
                        if camera_id in windows_camera_names:
                            camera_name = windows_camera_names[camera_id]
                        else:
                            # Fallback to backend-based naming
                            try:
                                if hasattr(cap, 'getBackendName'):
                                    backend = cap.getBackendName()
                                    if 'MSMF' in backend:  # Windows Media Foundation
                                        camera_name = f"Camera {camera_id} (Windows)"
                                    elif 'DSHOW' in backend:  # DirectShow
                                        camera_name = f"Camera {camera_id} (DirectShow)"
                            except:
                                pass
                        
                        camera_info = {
                            'camera_id': camera_id,
                            'name': camera_name,
                            'resolution': (width, height),
                            'fps': fps,
                            'available': True,
                            'test_frame_shape': frame.shape,
                            'backend': cap.getBackendName() if hasattr(cap, 'getBackendName') else 'Unknown'
                        }
                        available_cameras.append(camera_info)
                        logger.info(f"Detected camera {camera_id}: {camera_name} ({width}x{height} @ {fps:.1f}fps)")
                    else:
                        # Camera opened but can't read frames
                        camera_name = f"Camera {camera_id} (No Signal)"
                        if camera_id in windows_camera_names:
                            camera_name = f"{windows_camera_names[camera_id]} (No Signal)"
                            
                        camera_info = {
                            'camera_id': camera_id,
                            'name': camera_name,
                            'resolution': (width, height),
                            'fps': fps,
                            'available': False,
                            'test_frame_shape': None,
                            'backend': cap.getBackendName() if hasattr(cap, 'getBackendName') else 'Unknown'
                        }
                        available_cameras.append(camera_info)
                        logger.warning(f"Camera {camera_id} opened but can't read frames")
                    
                    cap.release()
                else:
                    # Camera doesn't exist or can't be opened
                    camera_name = f"Camera {camera_id} (Not Found)"
                    if camera_id in windows_camera_names:
                        camera_name = f"{windows_camera_names[camera_id]} (Not Found)"
                        
                    camera_info = {
                        'camera_id': camera_id,
                        'name': camera_name,
                        'resolution': (0, 0),
                        'fps': 0,
                        'available': False,
                        'test_frame_shape': None,
                        'backend': 'Unknown'
                    }
                    available_cameras.append(camera_info)
                    
            except Exception as e:
                logger.warning(f"Error checking camera {camera_id}: {str(e)}")
                # Add error info to list
                camera_name = f"Camera {camera_id} (Error)"
                if camera_id in windows_camera_names:
                    camera_name = f"{windows_camera_names[camera_id]} (Error)"
                    
                camera_info = {
                    'camera_id': camera_id,
                    'name': camera_name,
                    'resolution': (0, 0),
                    'fps': 0,
                    'available': False,
                    'test_frame_shape': None,
                    'backend': 'Error',
                    'error': str(e)
                }
                available_cameras.append(camera_info)
                continue
        
        available_count = len([c for c in available_cameras if c['available']])
        logger.info(f"Detected {available_count} available cameras out of {len(available_cameras)} checked")
        return available_cameras
    
    def __init__(
        self,
        camera_id: int = 0,
        model_path: str = "models/",
        backend_preference: Any = None,
    ):
        """
        Initialize the smart camera system.

        Args:
            camera_id: Camera device ID (default: 0 for primary camera).
            model_path: Path to AI model files.
            backend_preference: OpenCV capture backend preference. Accepts
                "auto" (platform default), a single backend string/int, or a
                list of backend strings/ints. When None, the value from
                CAMERA_CONFIG.backend_preference is used.
        """
        self.camera_id = camera_id
        self.model_path = model_path
        self.cap = None
        self.is_recording = False
        self.is_detecting = False
        
        # AI model components
        self.object_detector = None
        self.face_analyzer = None
        self.motion_detector = None
        self.image_enhancer = None
        
        # Smart processing components
        self.auto_tagger = None
        self.scene_classifier = None
        self.anomaly_detector = None
        
        # Capture settings
        self.capture_settings = {
            'resolution': (1920, 1080),
            'fps': 30,
            'quality': 95,
            'auto_focus': True,
            'exposure': 'auto',
            'auto_enhancement': True,
            'enhancement_type': 'auto'
        }
        
        # Detection settings
        self.detection_settings = {
            'confidence_threshold': 0.5,
            'nms_threshold': 0.4,
            'motion_sensitivity': 0.3,
            'face_recognition_enabled': True,
            'object_detection_enabled': True,
            'motion_detection_enabled': True,
            'quality_enhancement_enabled': True
        }
        
        # Storage settings
        self.storage_settings = {
            'output_dir': 'captures/',
            'max_storage_gb': 10,
            'auto_cleanup': True,
            'file_format': 'jpg',
            'save_enhanced': True,
            'save_original': False
        }
        
        # Smart AI Capture settings
        self.ai_capture_settings = {
            'auto_capture_enabled': True,
            'capture_cooldown_seconds': 5,  # Minimum time between captures
            'face_capture_threshold': 0.6,  # Confidence threshold for face capture
            'object_capture_threshold': 0.7,  # Confidence threshold for object capture
            'motion_capture_threshold': 0.5,  # Motion sensitivity for capture
            'max_captures_per_minute': 12,  # Rate limiting
            'capture_sequence_count': 3,  # Number of frames to capture per event
            'capture_sequence_interval': 0.5,  # Seconds between sequence frames
            'save_detection_overlay': True,  # Save frames with detection boxes
            'event_classification': True,  # Classify events by type
        }
        
        # Smart Processing settings
        self.smart_processing_settings = {
            'auto_tagging_enabled': True,
            'scene_classification_enabled': True,
            'anomaly_detection_enabled': True,
            'anomaly_sensitivity': 0.7,  # 0.0-1.0, higher = more sensitive
            'baseline_frames': 30,  # Frames to use for anomaly baseline
        }

        # AI-assisted framing/composition settings
        self.framing_settings = {
            'enabled': True,
            'min_score': 0.40,           # capture preference threshold
            'gate_capture': False,        # if True, framing must clear min_score
            'show_overlay': True,         # render guide grid + score in saved overlays
        }
        self.framing_engine: Optional[FramingEngine] = None
        
        # Event tracking
        self.detected_events = []
        self.face_database = {}
        self.known_objects = set()
        self.last_capture_time = 0
        self.capture_count_this_minute = 0
        self.minute_start_time = time.time()

        # Duplicate capture suppression state
        self.recent_captures: List[Dict[str, Any]] = []
        self.max_recent_captures: int = 8

        # Threading
        self.capture_queue = queue.Queue(maxsize=100)
        self.processing_queue = queue.Queue(maxsize=50)
        self.capture_thread = None
        self.processing_thread = None

        # Single-reader frame source (set up by `_initialize_camera`)
        self.frame_source: Optional[FrameSource] = None
        if backend_preference is None and GUI_COMPONENTS_AVAILABLE:
            try:
                cfg = get_settings().get("CAMERA_CONFIG", {})
                backend_preference = cfg.get("backend_preference", "auto")
            except Exception:
                backend_preference = "auto"
        if backend_preference is None:
            backend_preference = "auto"
        self.backend_preference: List[int] = resolve_backend_preference(backend_preference)
        self.active_backend: Optional[int] = None

        # Image-processing quality/performance profile
        profile_name = "auto"
        if GUI_COMPONENTS_AVAILABLE:
            try:
                from config.settings import get_processing_profile_name
                profile_name = get_processing_profile_name()
            except Exception:
                profile_name = "auto"
        self.processing_profile: ProcessingProfile = get_profile(profile_name)
        if self.capture_settings.get('enhancement_type') in (None, 'auto'):
            self.capture_settings['enhancement_type'] = (
                self.processing_profile.default_enhancement_type
            )

        # Initialize components
        self._initialize_camera()
        self._load_ai_models()
        self._setup_storage()
    
    def _initialize_camera(self):
        """Initialize camera with optimal settings using a platform-aware backend."""
        try:
            cap, backend_id = open_capture(self.camera_id, self.backend_preference)
            if cap is None or not cap.isOpened():
                raise Exception(f"Failed to open camera {self.camera_id}")

            self.cap = cap
            self.active_backend = backend_id

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.capture_settings['resolution'][0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.capture_settings['resolution'][1])
            self.cap.set(cv2.CAP_PROP_FPS, self.capture_settings['fps'])

            if self.capture_settings['auto_focus']:
                self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

            self.frame_source = FrameSource(self.cap, name=f"FrameSource-{self.camera_id}")
            self.frame_source.start()

            logger.info(f"Camera {self.camera_id} initialized successfully")

        except Exception as e:
            logger.error(f"Camera initialization failed: {str(e)}")
            raise
    
    def _load_ai_models(self):
        """Load AI models for object detection, face recognition, and motion detection."""
        try:
            # Load YOLO object detection model (requires PyTorch)
            if TORCH_AVAILABLE:
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
                    self.object_detector = None
            else:
                logger.warning("PyTorch not available, skipping YOLO model loading")
                self.object_detector = None
            
            # Initialize face analyzer (only requires OpenCV)
            if self.detection_settings['face_recognition_enabled']:
                try:
                    self.face_analyzer = FaceAnalyzer()
                    logger.info("Face analyzer initialized")
                except Exception as e:
                    logger.error(f"Face analyzer initialization failed: {str(e)}")
                    self.face_analyzer = None
            
            # Initialize motion detector (only requires OpenCV)
            if self.detection_settings['motion_detection_enabled']:
                try:
                    self.motion_detector = MotionDetector(self.detection_settings['motion_sensitivity'])
                    logger.info("Motion detector initialized")
                except Exception as e:
                    logger.error(f"Motion detector initialization failed: {str(e)}")
                    self.motion_detector = None
            
            # Initialize image enhancer
            if self.detection_settings['quality_enhancement_enabled']:
                try:
                    self.image_enhancer = ImageQualityEnhancer()
                    logger.info("Image quality enhancer initialized")
                except Exception as e:
                    logger.error(f"Image enhancer initialization failed: {str(e)}")
                    self.image_enhancer = None
            
            # Initialize smart processing components
            if self.smart_processing_settings['auto_tagging_enabled']:
                try:
                    self.auto_tagger = AutoTagger()
                    logger.info("Auto tagger initialized")
                except Exception as e:
                    logger.error(f"Auto tagger initialization failed: {str(e)}")
                    self.auto_tagger = None
            
            if self.smart_processing_settings['scene_classification_enabled']:
                try:
                    self.scene_classifier = SceneClassifier()
                    logger.info("Scene classifier initialized")
                except Exception as e:
                    logger.error(f"Scene classifier initialization failed: {str(e)}")
                    self.scene_classifier = None
            
            if self.smart_processing_settings['anomaly_detection_enabled']:
                try:
                    self.anomaly_detector = AnomalyDetector(
                        baseline_frames=self.smart_processing_settings['baseline_frames'],
                        sensitivity=self.smart_processing_settings['anomaly_sensitivity']
                    )
                    logger.info("Anomaly detector initialized")
                except Exception as e:
                    logger.error(f"Anomaly detector initialization failed: {str(e)}")
                    self.anomaly_detector = None

            if self.framing_settings.get('enabled', True):
                try:
                    self.framing_engine = FramingEngine()
                    logger.info("Framing engine initialized")
                except Exception as e:
                    logger.error(f"Framing engine initialization failed: {str(e)}")
                    self.framing_engine = None
                
        except Exception as e:
            logger.error(f"AI model loading failed: {str(e)}")
            # Ensure all components are None if there's a critical error
            self.object_detector = None
            self.face_analyzer = None
            self.motion_detector = None
            self.image_enhancer = None
            self.auto_tagger = None
            self.scene_classifier = None
            self.anomaly_detector = None
    
    def _setup_storage(self):
        """Setup storage directory and cleanup system."""
        try:
            os.makedirs(self.storage_settings['output_dir'], exist_ok=True)
            os.makedirs(os.path.join(self.storage_settings['output_dir'], 'images'), exist_ok=True)
            os.makedirs(os.path.join(self.storage_settings['output_dir'], 'videos'), exist_ok=True)
            os.makedirs(os.path.join(self.storage_settings['output_dir'], 'events'), exist_ok=True)
            os.makedirs(os.path.join(self.storage_settings['output_dir'], 'enhanced'), exist_ok=True)
            
            logger.info("Storage directories created")
            
        except Exception as e:
            logger.error(f"Storage setup failed: {str(e)}")
    
    def start_capture(self):
        """Start continuous capture and processing."""
        if self.capture_thread and self.capture_thread.is_alive():
            logger.warning("Capture already running")
            return
        
        self.is_detecting = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        
        self.capture_thread.start()
        self.processing_thread.start()
        
        logger.info("Smart camera capture started")
    
    def stop_capture(self):
        """Stop capture and processing."""
        self.is_detecting = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=5)
        if self.processing_thread:
            self.processing_thread.join(timeout=5)
        
        if self.is_recording:
            self.stop_recording()
        
        logger.info("Smart camera capture stopped")
    
    def _capture_loop(self):
        """Main capture loop for continuous frame acquisition.

        Pulls frames from the shared `FrameSource` (single reader) so the GUI
        and the AI processing pipeline never contend on `cap.read()`.
        """
        last_frame_id: Optional[int] = None
        while self.is_detecting:
            try:
                if not self.frame_source:
                    time.sleep(0.05)
                    continue

                snapshot = self.frame_source.latest_frame(copy=True)
                if snapshot is None:
                    time.sleep(0.01)
                    continue

                frame, timestamp, frame_id = snapshot
                if frame_id == last_frame_id:
                    time.sleep(0.005)
                    continue
                last_frame_id = frame_id

                frame_data = {
                    'frame': frame,
                    'timestamp': timestamp,
                    'frame_id': frame_id,
                }

                if not self.capture_queue.full():
                    self.capture_queue.put(frame_data)
                else:
                    try:
                        self.capture_queue.get_nowait()
                        self.capture_queue.put(frame_data)
                    except queue.Empty:
                        pass

            except Exception as e:
                logger.error(f"Capture loop error: {str(e)}")
                time.sleep(0.1)

    def get_preview_frame(self, copy: bool = True) -> Optional[np.ndarray]:
        """Return the latest live frame for GUI consumers.

        This is the GUI-safe way to obtain a frame; it does not contend with
        the AI capture pipeline because both consume from the same single
        reader via `FrameSource`.
        """
        if not self.frame_source:
            return None
        snapshot = self.frame_source.latest_frame(copy=copy)
        if snapshot is None:
            return None
        return snapshot[0]
    
    def _processing_loop(self):
        """Main processing loop for AI analysis."""
        while self.is_detecting:
            try:
                if not self.capture_queue.empty():
                    frame_data = self.capture_queue.get_nowait()
                    self._process_frame(frame_data)
                else:
                    time.sleep(0.01)
                    
            except Exception as e:
                logger.error(f"Processing loop error: {str(e)}")
                time.sleep(0.1)
    
    def _process_frame(self, frame_data: Dict[str, Any]):
        """Process a single frame with AI analysis."""
        frame = frame_data['frame']
        timestamp = frame_data['timestamp']
        
        # Enhance image quality if enabled
        if self.detection_settings['quality_enhancement_enabled'] and self.image_enhancer:
            enhanced_frame = self.image_enhancer.enhance_image_quality(
                frame, self.capture_settings['enhancement_type']
            )
        else:
            enhanced_frame = frame
        
        detections = {}
        
        # Object detection
        if self.detection_settings['object_detection_enabled'] and self.object_detector:
            detections['objects'] = self._detect_objects(enhanced_frame)
        
        # Face detection and recognition
        if self.detection_settings['face_recognition_enabled'] and self.face_analyzer:
            detections['faces'] = self.face_analyzer.detect_faces(enhanced_frame)
        
        # Motion detection
        if self.detection_settings['motion_detection_enabled'] and self.motion_detector:
            motion_detected = self.motion_detector.detect_motion(enhanced_frame)
            if motion_detected:
                detections['motion'] = True
        
        # Smart processing: Scene classification
        if self.smart_processing_settings['scene_classification_enabled'] and self.scene_classifier:
            scene_info = self.scene_classifier.classify_scene(enhanced_frame, detections)
            detections['scene'] = scene_info
        
        # Smart processing: Anomaly detection
        anomaly_info = None
        if self.smart_processing_settings['anomaly_detection_enabled'] and self.anomaly_detector:
            anomaly_info = self.anomaly_detector.detect_anomaly(enhanced_frame, detections)
            detections['anomaly'] = anomaly_info
            # If anomaly detected, treat as significant event
            if anomaly_info.get('is_anomaly', False):
                detections['anomaly_detected'] = True
        
        # Smart processing: Auto tagging
        tags = None
        if self.smart_processing_settings['auto_tagging_enabled'] and self.auto_tagger:
            tags = self.auto_tagger.generate_tags(enhanced_frame, detections, timestamp)
            detections['tags'] = tags

        # AI-assisted framing/composition score
        if self.framing_settings.get('enabled', True) and self.framing_engine is not None:
            try:
                score = self.framing_engine.score(enhanced_frame.shape, detections)
                detections['framing'] = score.to_dict()
            except Exception as e:
                logger.debug(f"Framing scoring failed: {e}")

        # Check if any significant events detected
        if self._is_significant_event(detections):
            self._handle_significant_event(enhanced_frame, detections, timestamp)
    
    def _detect_objects(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Detect objects in the frame using YOLO."""
        try:
            results = self.object_detector(frame)
            detections = []
            
            for det in results.xyxy[0]:
                x1, y1, x2, y2, conf, cls = det.tolist()
                if conf > self.detection_settings['confidence_threshold']:
                    detection = {
                        'bbox': (int(x1), int(y1), int(x2-x1), int(y2-y1)),
                        'confidence': float(conf),
                        'class': int(cls),
                        'class_name': results.names[int(cls)]
                    }
                    detections.append(detection)
            
            return detections
        except Exception as e:
            logger.error(f"Object detection error: {str(e)}")
            return []
    
    def _is_significant_event(self, detections: Dict[str, Any]) -> bool:
        """Determine if the detected events are significant enough to capture."""
        if not self.ai_capture_settings['auto_capture_enabled']:
            return False
        
        # Anomaly detection always triggers capture (bypasses rate limiting)
        if detections.get('anomaly_detected', False):
            return True
        
        # Context-aware capture: adjust sensitivity based on scene
        scene = detections.get('scene', {})
        if scene:
            # More sensitive in outdoor/active scenes
            if scene.get('location') == 'outdoor' and scene.get('activity') == 'high_activity':
                # Reduce cooldown for active outdoor scenes
                cooldown_multiplier = 0.7
            elif scene.get('location') == 'indoor' and scene.get('activity') == 'static':
                # Increase cooldown for static indoor scenes
                cooldown_multiplier = 1.5
            else:
                cooldown_multiplier = 1.0
        else:
            cooldown_multiplier = 1.0
        
        # Check rate limiting
        current_time = time.time()
        if current_time - self.minute_start_time >= 60:
            self.capture_count_this_minute = 0
            self.minute_start_time = current_time
        
        if self.capture_count_this_minute >= self.ai_capture_settings['max_captures_per_minute']:
            return False
        
        # Check cooldown with context-aware adjustment
        adjusted_cooldown = self.ai_capture_settings['capture_cooldown_seconds'] * cooldown_multiplier
        if current_time - self.last_capture_time < adjusted_cooldown:
            return False

        # Optional framing gate: only capture well-framed scenes when enabled.
        framing = detections.get('framing')
        if (
            framing
            and framing.get('has_subject')
            and self.framing_settings.get('gate_capture', False)
        ):
            min_score = float(self.framing_settings.get('min_score', 0.0))
            if framing.get('composite', 0.0) < min_score:
                return False
        
        # Check for faces with threshold
        if 'faces' in detections and len(detections['faces']) > 0:
            for face in detections['faces']:
                if face.get('confidence', 1.0) >= self.ai_capture_settings['face_capture_threshold']:
                    return True
        
        # Check for objects with threshold
        if 'objects' in detections:
            for obj in detections['objects']:
                if obj['confidence'] >= self.ai_capture_settings['object_capture_threshold']:
                    return True
        
        # Check for motion with threshold
        if 'motion' in detections and detections['motion']:
            motion_strength = detections.get('motion_strength', 1.0)
            if motion_strength >= self.ai_capture_settings['motion_capture_threshold']:
                return True
        
        return False
    
    def _handle_significant_event(self, frame: np.ndarray, detections: Dict[str, Any], timestamp: datetime):
        """Handle significant events by saving enhanced images/videos."""
        try:
            # Update capture tracking
            self.last_capture_time = time.time()
            self.capture_count_this_minute += 1
            
            # Classify event type
            event_type = self._classify_event(detections)
            
            # Create event directory with classification
            event_dir = os.path.join(self.storage_settings['output_dir'], 'events', 
                                   f"{event_type}_{timestamp.strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(event_dir, exist_ok=True)
            
            # Smart filtering: avoid duplicate captures
            if self._is_duplicate_capture(detections):
                logger.debug("Skipping duplicate capture")
                return
            
            # Capture sequence if enabled
            if self.ai_capture_settings['capture_sequence_count'] > 1:
                self._capture_event_sequence(frame, detections, timestamp, event_dir, event_type)
            else:
                # Single frame capture
                self._save_event_frame(frame, detections, timestamp, event_dir, event_type, 1)
            
            # Save detection metadata with smart processing data
            metadata = {
                'timestamp': timestamp.isoformat(),
                'event_type': event_type,
                'detections': detections,
                'enhancement_applied': self.detection_settings['quality_enhancement_enabled'],
                'capture_settings': self.ai_capture_settings.copy()
            }
            
            # Add smart processing metadata
            if 'tags' in detections and detections['tags']:
                metadata['tags'] = self.auto_tagger.get_all_tags(detections['tags']) if self.auto_tagger else []
            
            if 'scene' in detections:
                metadata['scene_classification'] = detections['scene']
            
            if 'anomaly' in detections and detections['anomaly'].get('is_anomaly', False):
                metadata['anomaly'] = detections['anomaly']
                metadata['is_anomaly'] = True
            
            metadata_filename = os.path.join(event_dir, f"metadata_{timestamp.strftime('%H%M%S_%f')}.json")
            with open(metadata_filename, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Also save to images directory for easy access
            if self.storage_settings['save_enhanced']:
                images_dir = os.path.join(self.storage_settings['output_dir'], 'images')
                enhanced_filename = os.path.join(images_dir, 
                                               f"ai_capture_{event_type}_{timestamp.strftime('%Y%m%d_%H%M%S_%f')}.jpg")
                cv2.imwrite(enhanced_filename, frame)
            
            logger.info(f"AI event captured: {event_type} - {event_dir}")
            
        except Exception as e:
            logger.error(f"Error handling significant event: {str(e)}")
    
    def _classify_event(self, detections: Dict[str, Any]) -> str:
        """Classify the type of event based on detections."""
        if not self.ai_capture_settings['event_classification']:
            return "event"
        
        if 'faces' in detections and len(detections['faces']) > 0:
            return "face_detection"
        elif 'objects' in detections and len(detections['objects']) > 0:
            # Get the most confident object
            best_obj = max(detections['objects'], key=lambda x: x['confidence'])
            return f"object_{best_obj['class_name']}"
        elif 'motion' in detections and detections['motion']:
            return "motion_detection"
        else:
            return "unknown_event"
    
    def _capture_event_sequence(self, frame: np.ndarray, detections: Dict[str, Any], 
                               timestamp: datetime, event_dir: str, event_type: str):
        """Capture a sequence of frames for the event with quality-based selection."""
        sequence_count = self.ai_capture_settings['capture_sequence_count']
        interval = self.ai_capture_settings['capture_sequence_interval']
        
        # Collect frames with quality scores
        frame_sequence = []
        
        # Save first frame immediately
        first_quality = self._assess_frame_quality(frame)
        frame_sequence.append({
            'frame': frame,
            'detections': detections,
            'timestamp': timestamp,
            'quality': first_quality,
            'index': 1
        })
        
        # Capture additional frames
        for i in range(2, sequence_count + 1):
            time.sleep(interval)
            try:
                seq_frame = self.frame_source.read_once() if self.frame_source else None
                if seq_frame is not None:
                    # Apply enhancement
                    if self.detection_settings['quality_enhancement_enabled'] and self.image_enhancer:
                        seq_frame = self.image_enhancer.enhance_image_quality(
                            seq_frame, self.capture_settings['enhancement_type']
                        )
                    
                    # Process detections for this frame
                    seq_detections = self._process_frame_detections(seq_frame)
                    
                    # Assess quality
                    quality = self._assess_frame_quality(seq_frame)
                    
                    frame_sequence.append({
                        'frame': seq_frame,
                        'detections': seq_detections,
                        'timestamp': datetime.now(),
                        'quality': quality,
                        'index': i
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to capture sequence frame {i}: {str(e)}")
                break
        
        # Quality-based selection: save all frames but prioritize best quality
        if frame_sequence:
            # Sort by quality (descending)
            frame_sequence.sort(key=lambda x: x['quality'], reverse=True)
            
            # Save all frames, but mark the best one
            for i, frame_data in enumerate(frame_sequence):
                is_best = (i == 0)
                self._save_event_frame(
                    frame_data['frame'],
                    frame_data['detections'],
                    frame_data['timestamp'],
                    event_dir,
                    event_type,
                    frame_data['index'],
                    is_best_quality=is_best
                )
    
    def _save_event_frame(self, frame: np.ndarray, detections: Dict[str, Any], 
                         timestamp: datetime, event_dir: str, event_type: str, frame_num: int,
                         is_best_quality: bool = False):
        """Save a single event frame with optional detection overlay."""
        try:
            # Create frame with detection overlay if enabled
            if self.ai_capture_settings['save_detection_overlay']:
                overlay_frame = self._create_detection_overlay(frame, detections)
            else:
                overlay_frame = frame
            
            # Save enhanced frame with quality indicator
            if self.storage_settings['save_enhanced']:
                quality_suffix = "_best" if is_best_quality else ""
                frame_suffix = f"_{frame_num:02d}" if frame_num > 1 else ""
                enhanced_filename = os.path.join(event_dir, 
                                               f"{event_type}_frame{frame_suffix}_{timestamp.strftime('%H%M%S_%f')}{quality_suffix}.jpg")
                cv2.imwrite(enhanced_filename, overlay_frame)
            
        except Exception as e:
            logger.error(f"Error saving event frame: {str(e)}")
    
    def _create_detection_overlay(self, frame: np.ndarray, detections: Dict[str, Any]) -> np.ndarray:
        """Create a frame with detection bounding boxes and labels."""
        overlay_frame = frame.copy()
        
        # Draw face detections
        if 'faces' in detections:
            for face in detections['faces']:
                x, y, w, h = face["bbox"]
                cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(overlay_frame, "Face", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Draw object detections
        if 'objects' in detections:
            for obj in detections['objects']:
                x, y, w, h = obj["bbox"]
                label = obj.get("class_name", "Object")
                confidence = obj.get("confidence", 0)
                cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                cv2.putText(overlay_frame, f"{label} {confidence:.2f}", (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
        
        # Draw motion detection
        if 'motion' in detections and detections['motion']:
            h, w = overlay_frame.shape[:2]
            cv2.rectangle(overlay_frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)
            cv2.putText(overlay_frame, "MOTION DETECTED", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Draw framing guide + score (kept lightweight: grid + chosen subject)
        framing = detections.get('framing')
        if (
            framing
            and self.framing_settings.get('show_overlay', True)
            and self.framing_engine is not None
        ):
            try:
                score = FramingScore(
                    composite=float(framing.get('composite', 0.0)),
                    centering=float(framing.get('centering', 0.0)),
                    rule_of_thirds=float(framing.get('rule_of_thirds', 0.0)),
                    margin=float(framing.get('margin', 0.0)),
                    coverage=float(framing.get('coverage', 0.0)),
                    subject_bbox=tuple(framing['subject_bbox']) if framing.get('subject_bbox') else None,
                    subject_kind=framing.get('subject_kind'),
                    has_subject=bool(framing.get('has_subject', False)),
                )
                overlay_frame = draw_framing_overlay(
                    overlay_frame, score, show_grid=True, show_subject=False, show_score=True,
                )
            except Exception as e:
                logger.debug(f"Framing overlay draw failed: {e}")

        return overlay_frame
    
    def _is_duplicate_capture(self, detections: Dict[str, Any]) -> bool:
        """
        Check if this capture is a duplicate of a recent capture.
        
        Args:
            detections: Current detection results
            
        Returns:
            True if this appears to be a duplicate
        """
        try:
            # Create a signature for this capture
            signature = {
                'face_count': len(detections.get('faces', [])),
                'object_count': len(detections.get('objects', [])),
                'object_types': tuple(sorted([obj.get('class_name', '') for obj in detections.get('objects', [])])),
                'motion': detections.get('motion', False),
                'scene': detections.get('scene', {}).get('location', 'unknown')
            }
            
            # Check against recent captures
            for recent_sig in self.recent_captures:
                # Compare signatures
                if (signature['face_count'] == recent_sig['face_count'] and
                    signature['object_count'] == recent_sig['object_count'] and
                    signature['object_types'] == recent_sig['object_types'] and
                    signature['motion'] == recent_sig['motion'] and
                    signature['scene'] == recent_sig['scene']):
                    return True  # Duplicate detected
            
            # Add to recent captures
            self.recent_captures.append(signature)
            if len(self.recent_captures) > self.max_recent_captures:
                self.recent_captures.pop(0)
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking duplicate capture: {e}")
            return False
    
    def _assess_frame_quality(self, frame: np.ndarray) -> float:
        """
        Assess the quality of a frame for capture selection.
        
        Returns:
            Quality score (0.0-1.0, higher is better)
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Sharpness (Laplacian variance)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            sharpness = np.var(laplacian) / 1000.0  # Normalize
            
            # Brightness (optimal range 0.3-0.7)
            brightness = np.mean(gray) / 255.0
            brightness_score = 1.0 - abs(brightness - 0.5) * 2  # Best at 0.5
            
            # Contrast (standard deviation)
            contrast = np.std(gray) / 128.0  # Normalize
            contrast = min(contrast, 1.0)
            
            # Combine metrics (weighted)
            quality = (sharpness * 0.4 + brightness_score * 0.3 + contrast * 0.3)
            return min(max(quality, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"Failed to assess frame quality: {e}")
            return 0.5  # Default quality
    
    def _process_frame_detections(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a frame for detections without saving."""
        detections = {}
        
        # Object detection
        if self.detection_settings['object_detection_enabled'] and self.object_detector:
            detections['objects'] = self._detect_objects(frame)
        
        # Face detection and recognition
        if self.detection_settings['face_recognition_enabled'] and self.face_analyzer:
            detections['faces'] = self.face_analyzer.detect_faces(frame)
        
        # Motion detection
        if self.detection_settings['motion_detection_enabled'] and self.motion_detector:
            motion_detected = self.motion_detector.detect_motion(frame)
            if motion_detected:
                detections['motion'] = True
                detections['motion_strength'] = 1.0  # Placeholder for motion strength
        
        return detections
    
    def capture_high_quality_image(self, enhancement_type: str = 'auto') -> str:
        """Capture a single high-quality image with AI enhancement."""
        try:
            frame = self.frame_source.read_once() if self.frame_source else None
            if frame is None:
                raise Exception("Failed to capture frame")
            
            # Apply AI enhancement
            if self.image_enhancer:
                enhanced_frame = self.image_enhancer.enhance_image_quality(frame, enhancement_type)
            else:
                enhanced_frame = frame
            
            # Save image
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            filename = os.path.join(self.storage_settings['output_dir'], 'images', 
                                  f"enhanced_capture_{timestamp}.jpg")
            
            cv2.imwrite(filename, enhanced_frame)
            logger.info(f"High-quality image captured: {filename}")
            
            return filename
            
        except Exception as e:
            logger.error(f"Error capturing high-quality image: {str(e)}")
            return ""
    
    def start_recording(self, duration: int = 30):
        """Start recording high-quality video."""
        if self.is_recording:
            logger.warning("Recording already in progress")
            return
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = os.path.join(self.storage_settings['output_dir'], 'videos', 
                                        f"enhanced_video_{timestamp}.mp4")
            
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.video_writer = cv2.VideoWriter(
                video_filename, fourcc, self.capture_settings['fps'], 
                self.capture_settings['resolution']
            )
            
            self.is_recording = True
            self.recording_start_time = time.time()
            self.recording_duration = duration
            
            logger.info(f"Started recording: {video_filename}")
            
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
    
    def stop_recording(self):
        """Stop video recording."""
        if not self.is_recording:
            return
        
        try:
            self.is_recording = False
            if hasattr(self, 'video_writer'):
                self.video_writer.release()
            
            logger.info("Recording stopped")
            
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
    
    def get_camera_info(self) -> Dict[str, Any]:
        """Get camera information and capabilities."""
        if not self.cap:
            return {}
        
        info = {
            'camera_id': self.camera_id,
            'resolution': (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            ),
            'fps': self.cap.get(cv2.CAP_PROP_FPS),
            'brightness': self.cap.get(cv2.CAP_PROP_BRIGHTNESS),
            'contrast': self.cap.get(cv2.CAP_PROP_CONTRAST),
            'saturation': self.cap.get(cv2.CAP_PROP_SATURATION),
            'hue': self.cap.get(cv2.CAP_PROP_HUE),
            'gain': self.cap.get(cv2.CAP_PROP_GAIN),
            'exposure': self.cap.get(cv2.CAP_PROP_EXPOSURE)
        }
        
        return info
    
    def set_camera_settings(self, settings: Dict[str, Any]):
        """Set camera parameters."""
        try:
            for key, value in settings.items():
                if hasattr(cv2, f'CAP_PROP_{key.upper()}'):
                    prop_id = getattr(cv2, f'CAP_PROP_{key.upper()}')
                    self.cap.set(prop_id, value)
            
            logger.info("Camera settings updated")
            
        except Exception as e:
            logger.error(f"Error setting camera parameters: {str(e)}")
    
    def cleanup(self):
        """Clean up resources."""
        self.stop_capture()
        if self.frame_source:
            try:
                self.frame_source.stop()
            except Exception:
                pass
            self.frame_source = None
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()
        logger.info("Smart camera cleanup completed")
    
    def cleanup_old_captures(self, age_hours: int = 24, dry_run: bool = False) -> Dict[str, int]:
        """
        Clean up old capture files based on age.
        
        Args:
            age_hours: Delete files older than this many hours (1-168 for 1 hour to 1 week)
            dry_run: If True, only count files without deleting them
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            from datetime import timedelta
            
            # Validate age parameter
            if age_hours < 1 or age_hours > 168:
                raise ValueError("Age must be between 1 hour (1) and 1 week (168)")
            
            cutoff_time = datetime.now() - timedelta(hours=age_hours)
            stats = {
                'total_files_found': 0,
                'files_to_delete': 0,
                'files_deleted': 0,
                'bytes_freed': 0,
                'errors': 0
            }
            
            # Directories to clean
            dirs_to_clean = [
                os.path.join(self.storage_settings['output_dir'], 'images'),
                os.path.join(self.storage_settings['output_dir'], 'videos'),
                os.path.join(self.storage_settings['output_dir'], 'events'),
                os.path.join(self.storage_settings['output_dir'], 'enhanced')
            ]
            
            # File extensions to consider
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
            metadata_extensions = {'.json', '.txt'}
            
            all_extensions = image_extensions | video_extensions | metadata_extensions
            
            for directory in dirs_to_clean:
                if not os.path.exists(directory):
                    continue
                
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file)[1].lower()
                        
                        # Only process relevant file types
                        if file_ext not in all_extensions:
                            continue
                        
                        stats['total_files_found'] += 1
                        
                        try:
                            # Get file modification time
                            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                            
                            if mtime < cutoff_time:
                                stats['files_to_delete'] += 1
                                file_size = os.path.getsize(file_path)
                                
                                if not dry_run:
                                    os.remove(file_path)
                                    stats['files_deleted'] += 1
                                    stats['bytes_freed'] += file_size
                                    logger.info(f"Deleted old file: {file_path}")
                                else:
                                    logger.info(f"Would delete: {file_path} (modified: {mtime})")
                                    
                        except Exception as e:
                            stats['errors'] += 1
                            logger.error(f"Error processing file {file_path}: {str(e)}")
            
            # Convert bytes to MB for logging
            mb_freed = stats['bytes_freed'] / (1024 * 1024)
            
            if dry_run:
                logger.info(f"Cleanup dry run: {stats['files_to_delete']} files would be deleted "
                           f"({mb_freed:.2f} MB) from {stats['total_files_found']} total files")
            else:
                logger.info(f"Cleanup completed: {stats['files_deleted']} files deleted "
                           f"({mb_freed:.2f} MB freed) from {stats['total_files_found']} total files")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            return {'error': str(e)}
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics for the captures directory."""
        try:
            stats = {
                'total_size_mb': 0,
                'file_count': 0,
                'directory_count': 0,
                'oldest_file': None,
                'newest_file': None,
                'by_type': {
                    'images': {'count': 0, 'size_mb': 0},
                    'videos': {'count': 0, 'size_mb': 0},
                    'events': {'count': 0, 'size_mb': 0},
                    'enhanced': {'count': 0, 'size_mb': 0}
                }
            }
            
            if not os.path.exists(self.storage_settings['output_dir']):
                return stats
            
            # File extensions to track
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
            video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.wmv'}
            
            for root, dirs, files in os.walk(self.storage_settings['output_dir']):
                stats['directory_count'] += len(dirs)
                
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    try:
                        file_size = os.path.getsize(file_path)
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        stats['file_count'] += 1
                        stats['total_size_mb'] += file_size / (1024 * 1024)
                        
                        # Track oldest and newest files
                        if stats['oldest_file'] is None or file_mtime < stats['oldest_file']:
                            stats['oldest_file'] = file_mtime
                        if stats['newest_file'] is None or file_mtime > stats['newest_file']:
                            stats['newest_file'] = file_mtime
                        
                        # Categorize by type
                        if file_ext in image_extensions:
                            stats['by_type']['images']['count'] += 1
                            stats['by_type']['images']['size_mb'] += file_size / (1024 * 1024)
                        elif file_ext in video_extensions:
                            stats['by_type']['videos']['count'] += 1
                            stats['by_type']['videos']['size_mb'] += file_size / (1024 * 1024)
                        
                        # Categorize by directory
                        rel_path = os.path.relpath(root, self.storage_settings['output_dir'])
                        if 'events' in rel_path:
                            stats['by_type']['events']['count'] += 1
                            stats['by_type']['events']['size_mb'] += file_size / (1024 * 1024)
                        elif 'enhanced' in rel_path:
                            stats['by_type']['enhanced']['count'] += 1
                            stats['by_type']['enhanced']['size_mb'] += file_size / (1024 * 1024)
                            
                    except Exception as e:
                        logger.warning(f"Error processing file {file_path}: {str(e)}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {'error': str(e)}
    
    def set_ai_capture_settings(self, settings: Dict[str, Any]):
        """Update AI capture settings."""
        try:
            for key, value in settings.items():
                if key in self.ai_capture_settings:
                    self.ai_capture_settings[key] = value
            
            logger.info("AI capture settings updated")
            
        except Exception as e:
            logger.error(f"Error updating AI capture settings: {str(e)}")

    def set_framing_settings(self, settings: Dict[str, Any]):
        """Update AI-assisted framing settings."""
        try:
            for key, value in settings.items():
                if key in self.framing_settings:
                    self.framing_settings[key] = value

            if self.framing_settings.get('enabled', True) and self.framing_engine is None:
                try:
                    self.framing_engine = FramingEngine()
                except Exception as e:
                    logger.error(f"Framing engine reinit failed: {e}")
            elif not self.framing_settings.get('enabled', True):
                self.framing_engine = None

            logger.info("Framing settings updated")

        except Exception as e:
            logger.error(f"Error updating framing settings: {str(e)}")
    
    def get_ai_capture_settings(self) -> Dict[str, Any]:
        """Get current AI capture settings."""
        return self.ai_capture_settings.copy()
    
    def set_smart_processing_settings(self, settings: Dict[str, Any]):
        """Update smart processing settings."""
        try:
            for key, value in settings.items():
                if key in self.smart_processing_settings:
                    self.smart_processing_settings[key] = value
            
            # Reinitialize components if needed
            if 'auto_tagging_enabled' in settings:
                if settings['auto_tagging_enabled'] and not self.auto_tagger:
                    self.auto_tagger = AutoTagger()
                elif not settings['auto_tagging_enabled']:
                    self.auto_tagger = None
            
            if 'scene_classification_enabled' in settings:
                if settings['scene_classification_enabled'] and not self.scene_classifier:
                    self.scene_classifier = SceneClassifier()
                elif not settings['scene_classification_enabled']:
                    self.scene_classifier = None
            
            if 'anomaly_detection_enabled' in settings or 'anomaly_sensitivity' in settings or 'baseline_frames' in settings:
                if self.smart_processing_settings['anomaly_detection_enabled']:
                    self.anomaly_detector = AnomalyDetector(
                        baseline_frames=self.smart_processing_settings['baseline_frames'],
                        sensitivity=self.smart_processing_settings['anomaly_sensitivity']
                    )
                else:
                    self.anomaly_detector = None
            
            logger.info("Smart processing settings updated")
            
        except Exception as e:
            logger.error(f"Error updating smart processing settings: {str(e)}")
    
    def get_smart_processing_settings(self) -> Dict[str, Any]:
        """Get current smart processing settings."""
        return self.smart_processing_settings.copy()

def main():
    """Main function to demonstrate the SmartCamera capabilities."""
    try:
        from utils.ai_stack_status import print_startup_banner

        print_startup_banner()
    except Exception:
        pass

    # Set up global exception handler if GUI components are available
    if GUI_COMPONENTS_AVAILABLE:
        setup_global_exception_handler()
    
    try:
        # Initialize smart camera
        camera = SmartCamera(camera_id=0)
        
        print("Smart Camera AI System")
        print("======================")
        print("Press 'c' to capture high-quality image")
        print("Press 'r' to start/stop recording")
        print("Press 'i' to show camera info")
        print("Press 'q' to quit")
        
        # Start capture
        camera.start_capture()
        
        while True:
            key = input("Enter command: ").lower().strip()
            
            if key == 'q':
                break
            elif key == 'c':
                filename = camera.capture_high_quality_image()
                if filename:
                    print(f"Image saved: {filename}")
            elif key == 'r':
                if not camera.is_recording:
                    camera.start_recording()
                    print("Recording started...")
                else:
                    camera.stop_recording()
                    print("Recording stopped")
            elif key == 'i':
                info = camera.get_camera_info()
                print("Camera Info:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
        
        camera.cleanup()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
        camera.cleanup()
    except Exception as e:
        if GUI_COMPONENTS_AVAILABLE:
            handle_error(e, {
                "operation": "main_function",
                "component": "SmartCamera",
                "camera_id": 0
            })
        else:
            print(f"Error: {str(e)}")
        camera.cleanup()


def run_with_splash_screen():
    """Run the application with splash screen."""
    if not GUI_COMPONENTS_AVAILABLE:
        print("GUI components not available, running without splash screen")
        main()
        return
    
    try:
        import tkinter as tk
        
        # Create root window (hidden)
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        
        # Show splash screen
        splash = SplashScreen(root, completion_callback=lambda: _launch_main_application(root))
        
    except Exception as e:
        print(f"Error launching with splash screen: {e}")
        # Fallback to direct launch
        main()


def _launch_main_application(root):
    """Launch the main application after splash screen."""
    try:
        # Destroy the root window
        root.destroy()
        
        # Launch the main application
        main()
        
    except Exception as e:
        if GUI_COMPONENTS_AVAILABLE:
            handle_error(e, {
                "operation": "launch_main_application",
                "component": "application_launcher"
            })
        else:
            print(f"Error launching main application: {e}")

if __name__ == "__main__":
    # Check if splash screen is requested
    import sys
    if "--splash" in sys.argv and GUI_COMPONENTS_AVAILABLE:
        run_with_splash_screen()
    else:
        main()

