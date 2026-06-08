from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import cv2
import numpy as np
import json
from typing import List, Dict, Optional
import asyncio
import base64
import sys
import os
import logging
import threading
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the parent directory to the Python path to import the src modules
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

try:
    from src.camera.camera_manager import CameraManager
    from src.utils.config import load_config
    from src.security.motion_detector import MotionDetector, MotionDetectionMethod
    from src.security.recorder import VideoRecorder
    from src.security.alert_manager import AlertManager, AlertType, AlertLevel
    logger.info("Successfully imported security modules")
except ImportError as e:
    logger.error(f"Failed to import src modules: {str(e)}")
    logger.error(f"Project root: {project_root}")
    logger.error(f"Python path: {sys.path}")
    raise

app = FastAPI(title="The Eyes - Home Security API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Dict[int, WebSocket] = {}
camera_connections: Dict[str, List[WebSocket]] = {}

# Load configuration
try:
    config_path = os.path.join(project_root, "config", "config.json")
    config = load_config(config_path)
    logger.info(f"Loaded configuration from {config_path}")
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    config = {"cameras": {}, "security": {}}

# Initialize camera manager
try:
    camera_manager = CameraManager(config.get("cameras", {}))
    logger.info(
        f"Initialized camera manager with {len(camera_manager.cameras)} cameras"
    )
except Exception as e:
    logger.error(f"Failed to initialize camera manager: {e}")
    camera_manager = None

# Initialize security components
motion_detectors: Dict[str, MotionDetector] = {}
recorder: Optional[VideoRecorder] = None
alert_manager: Optional[AlertManager] = None

security_config = config.get("security", {})
recording_config = security_config.get("recording", {})
alerts_config = security_config.get("alerts", {})

# Initialize alert manager
if alerts_config.get("enabled", True):
    try:
        log_file = alerts_config.get("log_file", "logs/alerts.json")
        alert_manager = AlertManager(
            log_file=log_file,
            enable_sound=False,  # Web version doesn't support sound
            enable_visual=True
        )
        logger.info("Alert manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize alert manager: {e}")

# Initialize video recorder
if recording_config.get("enabled", False):
    try:
        output_dir = recording_config.get("output_dir", "recordings")
        recorder = VideoRecorder(
            output_dir=output_dir,
            codec=recording_config.get("codec", "mp4v"),
            fps=recording_config.get("fps", 30.0),
            max_file_size_mb=recording_config.get("max_file_size_mb", 500),
            max_duration_minutes=recording_config.get("max_duration_minutes", 60)
        )
        logger.info("Video recorder initialized")
    except Exception as e:
        logger.error(f"Failed to initialize recorder: {e}")

# Initialize motion detectors for each camera
motion_config = security_config.get("motion_detection", {})
if motion_config.get("enabled", False) and camera_manager:
    try:
        method_str = motion_config.get("method", "mog2")
        method = MotionDetectionMethod.MOG2 if method_str == "mog2" else (
            MotionDetectionMethod.KNN if method_str == "knn" else MotionDetectionMethod.FRAME_DIFF
        )
        
        for camera_id in camera_manager.cameras:
            detector = MotionDetector(
                method=method,
                sensitivity=motion_config.get("sensitivity", 0.5),
                min_area=motion_config.get("min_area", 500)
            )
            
            # Add motion callback for recording and alerts
            if recorder and recording_config.get("motion_triggered", True):
                def make_motion_callback(cam_id):
                    def callback(frame, contours, mask):
                        if recorder and not recorder.is_recording(cam_id):
                            h, w = frame.shape[:2]
                            recorder.start_recording(cam_id, w, h, motion_triggered=True)
                        if recorder:
                            recorder.write_frame(cam_id, frame)
                        if alert_manager and alerts_config.get("motion_alerts", True):
                            alert_manager.add_alert(
                                AlertType.MOTION_DETECTED,
                                f"Motion detected on camera {cam_id}",
                                camera_id=cam_id,
                                level=AlertLevel.WARNING,
                                suppress_duplicates_seconds=alerts_config.get("suppress_duplicates_seconds", 5.0)
                            )
                    return callback
                
                detector.add_motion_callback(make_motion_callback(camera_id))
            
            motion_detectors[camera_id] = detector
            logger.info(f"Motion detector initialized for camera {camera_id}")
    except Exception as e:
        logger.error(f"Failed to initialize motion detectors: {e}")

# Buffer for latest frames from each camera
camera_frames: Dict[str, np.ndarray] = {}
camera_frame_timestamps: Dict[str, float] = {}
processing_lock = threading.Lock()


@app.websocket("/ws/camera/{camera_id}")
async def camera_stream_websocket(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for streaming camera feeds."""
    await websocket.accept()
    
    if camera_id not in camera_connections:
        camera_connections[camera_id] = []
    camera_connections[camera_id].append(websocket)
    
    logger.info(f"New camera stream connection for {camera_id}. Total: {len(camera_connections[camera_id])}")
    
    try:
        while True:
            # Send latest frame if available
            with processing_lock:
                if camera_id in camera_frames:
                    frame = camera_frames[camera_id].copy()
                    timestamp = camera_frame_timestamps.get(camera_id, time.time())
                else:
                    await asyncio.sleep(0.1)
                    continue
            
            # Process motion detection if enabled
            motion_detected = False
            motion_contours = []
            if camera_id in motion_detectors:
                detector = motion_detectors[camera_id]
                motion_detected, motion_mask, motion_contours = detector.detect(frame)
            
            # Write to recording if active
            if recorder and recorder.is_recording(camera_id):
                recorder.write_frame(camera_id, frame)
            
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send frame data
            try:
                await websocket.send_json({
                    "type": "frame",
                    "camera_id": camera_id,
                    "frame": f"data:image/jpeg;base64,{frame_base64}",
                    "timestamp": timestamp,
                    "motion_detected": motion_detected,
                    "motion_contours": [cv2.boundingRect(c).tolist() for c in motion_contours] if motion_contours else []
                })
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error sending frame: {e}")
                break
            
            await asyncio.sleep(0.033)  # ~30 FPS
            
    except WebSocketDisconnect:
        logger.info(f"Camera stream WebSocket disconnected for {camera_id}")
    finally:
        if camera_id in camera_connections and websocket in camera_connections[camera_id]:
            camera_connections[camera_id].remove(websocket)
            if not camera_connections[camera_id]:
                del camera_connections[camera_id]


@app.websocket("/ws/input")
async def input_websocket(websocket: WebSocket):
    """WebSocket endpoint for receiving camera frames from browser."""
    await websocket.accept()
    active_connections[id(websocket)] = websocket
    logger.info(f"New input WebSocket connection. Total: {len(active_connections)}")
    
    try:
        while True:
            try:
                data = await websocket.receive_text()
                payload = json.loads(data)
                camera_id = payload.get("camera_id")
                image_data = payload.get("image")
                
                if not camera_id or not image_data:
                    continue
                
                # Decode base64 image
                try:
                    img_data = base64.b64decode(image_data.split(",")[1])
                    nparr = np.frombuffer(img_data, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if img is None:
                        continue
                except Exception as e:
                    logger.error(f"Image decoding error: {str(e)}")
                    continue
                
                # Buffer the latest frame
                with processing_lock:
                    camera_frames[camera_id] = img
                    camera_frame_timestamps[camera_id] = time.time()
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing input: {str(e)}")
                continue
                
    except WebSocketDisconnect:
        logger.info("Input WebSocket disconnected")
    finally:
        if id(websocket) in active_connections:
            del active_connections[id(websocket)]


@app.get("/api/cameras")
async def get_cameras():
    """Get information about available cameras."""
    try:
        if not camera_manager:
            return {"cameras": {}, "total": 0}
        
        cameras_info = {}
        for camera_id, camera in camera_manager.cameras.items():
            cameras_info[camera_id] = {
                "id": camera_id,
                "type": camera.__class__.__name__,
                "is_open": camera.is_open,
                "config": camera.config,
                "has_motion_detection": camera_id in motion_detectors,
                "is_recording": recorder.is_recording(camera_id) if recorder else False
            }
        return {"cameras": cameras_info, "total": len(cameras_info)}
    except Exception as e:
        logger.error(f"Error getting camera info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/motion/status")
async def get_motion_status(camera_id: Optional[str] = None):
    """Get motion detection status."""
    try:
        if camera_id:
            if camera_id in motion_detectors:
                stats = motion_detectors[camera_id].get_statistics()
                return {"camera_id": camera_id, **stats}
            else:
                raise HTTPException(status_code=404, detail=f"Motion detector not found for camera {camera_id}")
        else:
            all_stats = {}
            for cam_id, detector in motion_detectors.items():
                all_stats[cam_id] = detector.get_statistics()
            return {"motion_detectors": all_stats}
    except Exception as e:
        logger.error(f"Error getting motion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/motion/config")
async def configure_motion_detection(camera_id: str, config_data: dict):
    """Configure motion detection for a camera."""
    try:
        if camera_id not in motion_detectors:
            raise HTTPException(status_code=404, detail=f"Motion detector not found for camera {camera_id}")
        
        detector = motion_detectors[camera_id]
        detector.update_settings(
            sensitivity=config_data.get("sensitivity"),
            min_area=config_data.get("min_area"),
            var_threshold=config_data.get("var_threshold")
        )
        return {"status": "success", "camera_id": camera_id}
    except Exception as e:
        logger.error(f"Error configuring motion detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/start")
async def start_recording(camera_id: str, motion_triggered: bool = False):
    """Start recording for a camera."""
    try:
        if not recorder:
            raise HTTPException(status_code=503, detail="Recording not enabled")
        
        if camera_id not in camera_frames:
            raise HTTPException(status_code=404, detail=f"No frames available for camera {camera_id}")
        
        with processing_lock:
            frame = camera_frames.get(camera_id)
            if frame is None:
                raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")
            h, w = frame.shape[:2]
        
        success = recorder.start_recording(camera_id, w, h, motion_triggered=motion_triggered)
        if success:
            return {"status": "success", "camera_id": camera_id, "recording": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to start recording")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/stop")
async def stop_recording(camera_id: str):
    """Stop recording for a camera."""
    try:
        if not recorder:
            raise HTTPException(status_code=503, detail="Recording not enabled")
        
        filepath = recorder.stop_recording(camera_id)
        if filepath:
            return {"status": "success", "camera_id": camera_id, "recording": False, "filepath": str(filepath)}
        else:
            raise HTTPException(status_code=404, detail=f"No active recording for camera {camera_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recording/status")
async def get_recording_status(camera_id: Optional[str] = None):
    """Get recording status."""
    try:
        if not recorder:
            return {"enabled": False}
        
        if camera_id:
            is_recording = recorder.is_recording(camera_id)
            return {"enabled": True, "camera_id": camera_id, "recording": is_recording}
        else:
            all_status = {}
            if camera_manager:
                for cam_id in camera_manager.cameras:
                    all_status[cam_id] = recorder.is_recording(cam_id)
            return {"enabled": True, "recordings": all_status}
    except Exception as e:
        logger.error(f"Error getting recording status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/alerts")
async def get_alerts(limit: int = 50, unacknowledged_only: bool = False):
    """Get alerts."""
    try:
        if not alert_manager:
            return {"alerts": [], "total": 0}
        
        alerts = alert_manager.get_alerts(limit=limit, unacknowledged_only=unacknowledged_only)
        return {
            "alerts": [alert.to_dict() for alert in alerts],
            "total": len(alerts),
            "statistics": alert_manager.get_statistics()
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alerts/acknowledge")
async def acknowledge_alert(alert_data: dict):
    """Acknowledge an alert."""
    try:
        if not alert_manager:
            raise HTTPException(status_code=503, detail="Alert manager not enabled")
        
        # This is a simplified version - in production, you'd want to pass alert ID
        alert_manager.acknowledge_all()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error acknowledging alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cameras": len(camera_manager.cameras) if camera_manager else 0,
        "connections": len(active_connections),
        "motion_detection_enabled": len(motion_detectors) > 0,
        "recording_enabled": recorder is not None,
        "alerts_enabled": alert_manager is not None
    }


if __name__ == "__main__":
    try:
        import uvicorn

        logger.info("Starting The Eyes Home Security API server on http://0.0.0.0:8000")
        if camera_manager:
            logger.info(f"Available cameras: {list(camera_manager.cameras.keys())}")
        logger.info(f"Motion detection: {len(motion_detectors)} detectors")
        logger.info(f"Recording: {'Enabled' if recorder else 'Disabled'}")
        logger.info(f"Alerts: {'Enabled' if alert_manager else 'Disabled'}")
        
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            log_level="info",
            reload=True,
            workers=1,
        )
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
