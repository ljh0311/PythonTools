from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
import cv2
import numpy as np
import json
from typing import Any, List, Dict, Optional, Tuple
import asyncio
import base64
import sys
import os
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

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
    from src.camera.network_camera import build_rtsp_url
    from src.camera.network_camera_scanner import (
        discover_network_range,
        scan_network,
    )
    from src.utils.config import load_config, save_config
    from src.security.motion_detector import MotionDetector, MotionDetectionMethod
    from src.security.recorder import VideoRecorder
    from src.security.alert_manager import AlertManager, AlertType, AlertLevel
    from src.security.audit_log import write_audit, format_delete_summary
    from src.security.away_notifier import notify_motion_started, notify_motion_ended
    from src.security.media_library import (
        MotionSessionStore,
        collect_recordings_dirs,
        list_recording_files,
        new_session_id,
        resolve_media_path,
        media_mime_type,
        delete_media_file,
        delete_media_files,
        delete_older_media,
    )
    from src.security.face_memory import FaceMemoryStore
    logger.info("Successfully imported security modules")
except ImportError as e:
    logger.error(f"Failed to import src modules: {str(e)}")
    logger.error(f"Project root: {project_root}")
    logger.error(f"Python path: {sys.path}")
    raise

app = FastAPI(title="The Eyes - Home Security API")

# TODO: Add authentication middleware (session/JWT) before exposing API in production.
# TODO: Protect /api/* and WebSocket routes once login is implemented.

# Configure CORS
# TODO: Replace allow_origins=["*"] with explicit frontend origin when auth uses credentials.
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
    config = {"cameras": {}, "security": {}, "web": {}}

# Initialize camera manager
web_config = config.get("web", {})
prefer_browser_cameras = web_config.get("prefer_browser_cameras", True)
camera_configs = config.get("cameras", {})
network_camera_configs = {
    cid: cfg
    for cid, cfg in camera_configs.items()
    if str(cfg.get("type", "")).lower() == "network"
}
has_network_cameras = bool(network_camera_configs)

try:
    if prefer_browser_cameras and not has_network_cameras:
        # Web UI feeds frames via /ws/input — don't open local webcams (avoids lock contention).
        camera_manager = CameraManager({}, auto_scan=False)
        logger.info("Camera manager initialized in browser-only mode (no local webcam capture)")
    elif prefer_browser_cameras and has_network_cameras:
        camera_manager = CameraManager(network_camera_configs, auto_scan=False)
        logger.info(
            "Camera manager initialized in hybrid mode: %s network camera(s), browser webcams",
            len(camera_manager.cameras),
        )
    else:
        camera_manager = CameraManager(camera_configs, auto_scan=True)
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
face_config = security_config.get("face_recognition", {})
away_notifications_config = alerts_config.get("away_notifications", {})
auto_delete_config = recording_config.get("auto_delete", {})
audit_log_config = security_config.get("audit_log", {})
AUDIT_LOG_PATH = Path(project_root) / audit_log_config.get("file", "logs/security_audit.txt")
RETENTION_DAYS = int(recording_config.get("retention_days", 30))
AUTO_DELETE_ENABLED = bool(auto_delete_config.get("enabled", True))
AUTO_DELETE_INTERVAL_HOURS = float(auto_delete_config.get("interval_hours", 6))
AWAY_NOTIFICATIONS_ENABLED = bool(away_notifications_config.get("enabled", False))
retention_cleanup_task: Optional[asyncio.Task] = None

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
backend_dir = Path(__file__).resolve().parent
if recording_config.get("enabled", False):
    try:
        output_dir = str(backend_dir / recording_config.get("output_dir", "recordings"))
        recorder = VideoRecorder(
            output_dir=output_dir,
            codec=recording_config.get("codec", "avc1"),
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

            _apply_zones_to_detector(detector, _get_camera_zones_from_config(camera_id))
            motion_detectors[camera_id] = detector
            logger.info(f"Motion detector initialized for camera {camera_id}")
    except Exception as e:
        logger.error(f"Failed to initialize motion detectors: {e}")

# Buffer for latest frames from each camera
camera_frames: Dict[str, np.ndarray] = {}
camera_raw_frames: Dict[str, np.ndarray] = {}
camera_frame_timestamps: Dict[str, float] = {}
camera_motion_status: Dict[str, bool] = {}
camera_motion_contours: Dict[str, List[List[int]]] = {}
camera_motion_events: Dict[str, Optional[Dict]] = {}
camera_id_aliases: Dict[str, str] = {}
processing_lock = threading.Lock()
frame_processor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="frame_proc")
pending_browser_frames: Dict[str, np.ndarray] = {}
browser_process_scheduled: Dict[str, bool] = {}
MOTION_DETECT_MAX_WIDTH = int(motion_config.get("process_max_width", 640))
camera_capture_task: Optional[asyncio.Task] = None
camera_capture_running = False
disabled_cameras: set = set()

MOTION_END_TIMEOUT_SECONDS = float(motion_config.get("motion_end_timeout_seconds", 2.0))
MOTION_TRIGGER_DEBOUNCE_SECONDS = float(motion_config.get("trigger_debounce_seconds", 1.0))
MOTION_SNAPSHOT_DIR = Path(project_root) / motion_config.get("snapshot_dir", "snapshots/motion")
MOTION_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
motion_store = MotionSessionStore(MOTION_SNAPSHOT_DIR, Path(project_root))
RECORDINGS_DIRS = collect_recordings_dirs(
    Path(project_root),
    recording_config.get("output_dir", "recordings"),
    Path(recorder.output_dir) if recorder else None,
)
FACE_DATA_DIR = Path(project_root) / face_config.get("data_dir", "data/faces")
face_memory = FaceMemoryStore(
    project_root=Path(project_root),
    data_dir=FACE_DATA_DIR,
    enabled=bool(face_config.get("enabled", False)),
    similarity_threshold=float(face_config.get("similarity_threshold", 0.42)),
)


def _allowed_media_dirs() -> List[Path]:
    return list(RECORDINGS_DIRS) + [MOTION_SNAPSHOT_DIR]


def _recordings_dirs_live() -> List[Path]:
    return collect_recordings_dirs(
        Path(project_root),
        recording_config.get("output_dir", "recordings"),
        Path(recorder.output_dir) if recorder else None,
    )


def _load_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _recordings_summary(limit: int = 1000) -> Dict[str, Any]:
    rows = list_recording_files(_recordings_dirs_live(), Path(project_root), limit=limit)
    by_camera: Dict[str, Dict[str, Any]] = {}
    motion_count = 0
    continuous_count = 0
    total_mb = 0.0
    for row in rows:
        camera_id = row.get("camera_id", "unknown")
        if camera_id not in by_camera:
            by_camera[camera_id] = {"count": 0, "size_mb": 0.0, "motion": 0, "continuous": 0}
        by_camera[camera_id]["count"] += 1
        by_camera[camera_id]["size_mb"] += float(row.get("size_mb", 0.0))
        total_mb += float(row.get("size_mb", 0.0))
        if row.get("motion_triggered"):
            motion_count += 1
            by_camera[camera_id]["motion"] += 1
        else:
            continuous_count += 1
            by_camera[camera_id]["continuous"] += 1
    return {
        "total_count": len(rows),
        "total_size_mb": round(total_mb, 2),
        "motion_count": motion_count,
        "continuous_count": continuous_count,
        "by_camera": by_camera,
    }


def _alerts_summary() -> Dict[str, Any]:
    alerts_path = Path(project_root) / alerts_config.get("log_file", "logs/alerts.json")
    rows = _load_json_list(alerts_path)
    by_day: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    for row in rows:
        created_at = row.get("created_at")
        if isinstance(created_at, (int, float)):
            day = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d")
            by_day[day] = by_day.get(day, 0) + 1
        alert_type = str(row.get("type", "unknown"))
        by_type[alert_type] = by_type.get(alert_type, 0) + 1
    return {
        "available": alerts_path.exists(),
        "total_count": len(rows),
        "by_day": by_day,
        "by_type": by_type,
    }


def _motion_analytics_summary() -> Dict[str, Any]:
    sessions_path = MOTION_SNAPSHOT_DIR / "sessions.json"
    rows = _load_json_list(sessions_path)
    by_day: Dict[str, int] = {}
    by_hour: Dict[str, int] = {}
    by_camera: Dict[str, Dict[str, Any]] = {}
    durations: List[float] = []
    for row in rows:
        started_at = row.get("started_at")
        if not isinstance(started_at, (int, float)):
            continue
        dt = datetime.fromtimestamp(started_at)
        day_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%H:00")
        by_day[day_key] = by_day.get(day_key, 0) + 1
        by_hour[hour_key] = by_hour.get(hour_key, 0) + 1
        camera_id = str(row.get("camera_id", "unknown"))
        if camera_id not in by_camera:
            by_camera[camera_id] = {"count": 0, "total_duration_s": 0.0}
        by_camera[camera_id]["count"] += 1
        ended_at = row.get("ended_at")
        if isinstance(ended_at, (int, float)) and ended_at >= started_at:
            duration = float(ended_at - started_at)
            by_camera[camera_id]["total_duration_s"] += duration
            durations.append(duration)
    avg_duration = (sum(durations) / len(durations)) if durations else 0.0
    return {
        "total_events": len(rows),
        "by_day": by_day,
        "by_hour": by_hour,
        "by_camera": by_camera,
        "avg_duration_s": round(avg_duration, 2),
        "max_duration_s": round(max(durations), 2) if durations else 0.0,
    }


def _analytics_summary() -> Dict[str, Any]:
    return {
        "motion": _motion_analytics_summary(),
        "recordings": _recordings_summary(),
        "alerts": _alerts_summary(),
        "faces": {
            "enabled": face_memory.enabled,
            "runtime_ready": face_memory.runtime_ready,
            "people": len(face_memory.get_people_summary()) if face_memory.enabled else 0,
        },
        "generated_at": time.time(),
    }

security_state = {
    "motion_detection_enabled": bool(motion_config.get("enabled", False)),
    "motion_triggered_recording": bool(recording_config.get("motion_triggered", True)),
}

motion_activity_state: Dict[str, Dict] = {}
recording_suppress_until: Dict[str, float] = {}
MANUAL_STOP_SUPPRESS_SECONDS = float(recording_config.get("manual_stop_suppress_seconds", 120.0))


def _suppress_motion_recording(camera_id: str) -> None:
    """Block motion-triggered auto-start after the user manually stops recording."""
    recording_suppress_until[camera_id] = time.time() + MANUAL_STOP_SUPPRESS_SECONDS


def _clear_motion_recording_suppress(camera_id: str) -> None:
    recording_suppress_until.pop(camera_id, None)


def _is_motion_recording_suppressed(camera_id: str) -> bool:
    until = recording_suppress_until.get(camera_id, 0.0)
    if until > time.time():
        return True
    if camera_id in recording_suppress_until:
        recording_suppress_until.pop(camera_id, None)
    return False


def _get_local_ip_safe() -> str:
    """Best-effort local IP for network scan (does not exit the process)."""
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    finally:
        sock.close()


def _audit(action: str, details: str = "") -> None:
    write_audit(AUDIT_LOG_PATH, action, details)


def _maybe_notify_away_motion_started(
    camera_id: str, session_id: Optional[str], snapshot_path: Optional[str]
) -> None:
    if not AWAY_NOTIFICATIONS_ENABLED:
        return
    try:
        notify_motion_started(camera_id, session_id=session_id, snapshot_path=snapshot_path)
    except Exception as exc:
        logger.error("Away motion-started notification failed: %s", exc)


def _maybe_notify_away_motion_ended(
    camera_id: str, session_id: Optional[str], snapshot_path: Optional[str]
) -> None:
    if not AWAY_NOTIFICATIONS_ENABLED:
        return
    try:
        notify_motion_ended(camera_id, session_id=session_id, snapshot_path=snapshot_path)
    except Exception as exc:
        logger.error("Away motion-ended notification failed: %s", exc)


def _run_retention_cleanup(trigger: str = "scheduled") -> Dict:
    """Delete recordings/snapshots older than retention_days; audit the result."""
    if RETENTION_DAYS < 1:
        return {"count": 0, "skipped": True, "reason": "invalid retention_days"}
    result = delete_older_media(
        Path(project_root),
        _allowed_media_dirs(),
        _recordings_dirs_live(),
        MOTION_SNAPSHOT_DIR,
        RETENTION_DAYS,
        include_recordings=True,
        include_snapshots=True,
    )
    _audit(
        "auto_delete",
        f"trigger={trigger}, {format_delete_summary(result)}",
    )
    logger.info(
        "Retention cleanup (%s): deleted %s file(s) older than %s days",
        trigger,
        result.get("count", 0),
        RETENTION_DAYS,
    )
    return result


async def _retention_cleanup_loop() -> None:
    """Periodic background task to purge media past retention_days."""
    interval_seconds = max(AUTO_DELETE_INTERVAL_HOURS, 0.25) * 3600
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            await asyncio.to_thread(_run_retention_cleanup, "interval")
        except Exception as exc:
            logger.error("Scheduled retention cleanup failed: %s", exc)


def _normalize_camera_id(camera_id: str) -> str:
    """Map browser-provided IDs to a canonical camera ID."""
    if camera_manager and camera_id in camera_manager.cameras:
        return camera_id

    if camera_id.startswith("webcam_"):
        return camera_id

    if camera_id in camera_id_aliases:
        return camera_id_aliases[camera_id]

    canonical_id = camera_id
    if camera_manager:
        webcam_ids = sorted([cam_id for cam_id in camera_manager.cameras.keys() if cam_id.startswith("webcam_")])
        if webcam_ids:
            canonical_id = webcam_ids[len(camera_id_aliases) % len(webcam_ids)]
    camera_id_aliases[camera_id] = canonical_id
    return canonical_id


def _ensure_motion_detector(camera_id: str) -> Optional[MotionDetector]:
    """Create motion detector on-demand for dynamic camera IDs."""
    if not security_state["motion_detection_enabled"]:
        return None
    if camera_id in motion_detectors:
        return motion_detectors[camera_id]

    method_str = motion_config.get("method", "mog2")
    method = MotionDetectionMethod.MOG2 if method_str == "mog2" else (
        MotionDetectionMethod.KNN if method_str == "knn" else MotionDetectionMethod.FRAME_DIFF
    )
    detector = MotionDetector(
        method=method,
        sensitivity=motion_config.get("sensitivity", 0.5),
        min_area=motion_config.get("min_area", 500),
    )
    _apply_zones_to_detector(detector, _get_camera_zones_from_config(camera_id))
    motion_detectors[camera_id] = detector
    logger.info(f"Motion detector initialized on-demand for camera {camera_id}")
    return detector


def _save_motion_snapshot(
    camera_id: str, frame: np.ndarray, phase: str, session_id: str
) -> str:
    """Save a paired motion snapshot (first/last share session_id)."""
    snapshot_path = motion_store.snapshot_path(camera_id, session_id, phase)
    cv2.imwrite(str(snapshot_path), frame)
    now = time.time()
    if phase == "first":
        motion_store.register_session_start(session_id, camera_id, snapshot_path, now)
    else:
        motion_store.register_session_end(session_id, camera_id, snapshot_path, now)
    rel_path = motion_store.rel_path(snapshot_path)
    try:
        face_memory.process_snapshot(
            camera_id=camera_id,
            session_id=session_id,
            phase=phase,
            snapshot_rel_path=rel_path,
            timestamp=now,
        )
    except Exception as exc:
        logger.warning("Face snapshot processing failed: %s", exc)
    return rel_path


def _apply_frame_results(
    camera_id: str,
    source: str,
    canonical_id: str,
    raw_frame: np.ndarray,
    display_frame: np.ndarray,
    motion_detected: bool,
    contours: List,
    motion_event: Optional[Dict],
) -> None:
    """Publish processed frame state under a short lock."""
    timestamp = time.time()
    contour_boxes = [list(cv2.boundingRect(c)) for c in contours] if contours else []
    with processing_lock:
        camera_frames[canonical_id] = display_frame
        camera_raw_frames[canonical_id] = raw_frame
        camera_frame_timestamps[canonical_id] = timestamp
        camera_motion_status[canonical_id] = motion_detected
        camera_motion_contours[canonical_id] = contour_boxes
        camera_motion_events[canonical_id] = motion_event
        if source == "browser_input" and canonical_id != camera_id:
            camera_frames[camera_id] = display_frame
            camera_raw_frames[camera_id] = raw_frame
            camera_frame_timestamps[camera_id] = timestamp
            camera_motion_status[camera_id] = motion_detected
            camera_motion_contours[camera_id] = contour_boxes
            camera_motion_events[camera_id] = motion_event


def _process_camera_frame(camera_id: str, frame: np.ndarray, source: str = "unknown") -> None:
    """Shared frame processing path — runs off the asyncio event loop."""
    canonical_id = _normalize_camera_id(camera_id)
    if canonical_id in disabled_cameras:
        return
    raw_frame = frame.copy()

    motion_detected = False
    contours = []
    detector = _ensure_motion_detector(canonical_id)

    detect_frame = raw_frame
    if detector and raw_frame.shape[1] > MOTION_DETECT_MAX_WIDTH:
        scale = MOTION_DETECT_MAX_WIDTH / raw_frame.shape[1]
        detect_frame = cv2.resize(
            raw_frame,
            (MOTION_DETECT_MAX_WIDTH, int(raw_frame.shape[0] * scale)),
            interpolation=cv2.INTER_AREA,
        )

    if detector:
        motion_detected, _, contours = detector.detect(detect_frame)

    motion_event = _register_motion_transition(canonical_id, raw_frame, motion_detected)

    if recorder:
        if (
            motion_detected
            and security_state["motion_triggered_recording"]
            and not _is_motion_recording_suppressed(canonical_id)
            and not recorder.is_recording(canonical_id)
        ):
            h, w = raw_frame.shape[:2]
            if recorder.start_recording(canonical_id, w, h, motion_triggered=True):
                _audit("recording_started", f"camera_id={canonical_id}, motion_triggered=true")
        if recorder.is_recording(canonical_id):
            recorder.write_frame(canonical_id, raw_frame)

    # Keep stream encoding fast — motion boxes are signaled via motion_detected flag.
    display_frame = raw_frame
    _apply_frame_results(
        camera_id, source, canonical_id, raw_frame, display_frame,
        motion_detected, contours, motion_event,
    )


def _schedule_browser_frame_processing(camera_id: str, frame: np.ndarray) -> None:
    """Coalesce browser frames: always process the latest, drop backlog."""
    pending_browser_frames[camera_id] = frame
    if browser_process_scheduled.get(camera_id):
        return
    browser_process_scheduled[camera_id] = True

    async def _run():
        try:
            while True:
                pending = pending_browser_frames.pop(camera_id, None)
                if pending is None:
                    break
                await asyncio.to_thread(_process_camera_frame, camera_id, pending, "browser_input")
        finally:
            browser_process_scheduled[camera_id] = False
            if camera_id in pending_browser_frames:
                _schedule_browser_frame_processing(camera_id, pending_browser_frames[camera_id])

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(_run())


def _register_motion_transition(camera_id: str, frame: np.ndarray, active_motion: bool) -> Optional[Dict]:
    """
    Track motion state transitions and emit first/last motion events.
    """
    now = time.time()
    state = motion_activity_state.setdefault(
        camera_id,
        {
            "active": False,
            "session_id": None,
            "last_motion_time": 0.0,
            "last_start_time": 0.0,
            "last_candidate_frame": None,
        },
    )

    event = None
    if active_motion:
        state["last_motion_time"] = now
        state["last_candidate_frame"] = frame.copy()

        # Transition idle -> active with debounce to avoid rapid flicker.
        if not state["active"] and (now - state["last_start_time"]) >= MOTION_TRIGGER_DEBOUNCE_SECONDS:
            state["active"] = True
            state["last_start_time"] = now
            session_id = new_session_id()
            state["session_id"] = session_id
            snapshot_path = _save_motion_snapshot(camera_id, frame, "first", session_id)
            event = {
                "type": "motion_first_detected",
                "camera_id": camera_id,
                "session_id": session_id,
                "snapshot": snapshot_path,
                "first_snapshot": snapshot_path,
                "timestamp": now,
            }
            if alert_manager and alerts_config.get("motion_alerts", True):
                cam_label = _camera_display_name(camera_id)
                alert_manager.add_alert(
                    AlertType.MOTION_DETECTED,
                    f"Motion started on camera {cam_label}",
                    camera_id=camera_id,
                    level=AlertLevel.WARNING,
                    data={
                        "phase": "first",
                        "session_id": session_id,
                        "snapshot": snapshot_path,
                        "first_snapshot": snapshot_path,
                    },
                    suppress_duplicates_seconds=alerts_config.get("suppress_duplicates_seconds", 5.0),
                )
            _audit(
                "motion_started",
                f"camera_id={camera_id}, session_id={session_id}, snapshot={snapshot_path}",
            )
            _maybe_notify_away_motion_started(camera_id, session_id, snapshot_path)
    elif state["active"] and (now - state["last_motion_time"]) >= MOTION_END_TIMEOUT_SECONDS:
        state["active"] = False
        last_frame = state["last_candidate_frame"] if state["last_candidate_frame"] is not None else frame
        session_id = state.get("session_id") or new_session_id()
        snapshot_path = _save_motion_snapshot(camera_id, last_frame, "last", session_id)
        state["session_id"] = None
        if (
            recorder
            and security_state["motion_triggered_recording"]
            and recorder.is_recording(camera_id)
            and recorder.is_motion_triggered(camera_id)
        ):
            filepath = recorder.stop_recording(camera_id)
            _audit(
                "recording_stopped",
                f"camera_id={camera_id}, motion_triggered=true, filepath={filepath or 'n/a'}",
            )
        event = {
            "type": "motion_last_detected",
            "camera_id": camera_id,
            "session_id": session_id,
            "snapshot": snapshot_path,
            "last_snapshot": snapshot_path,
            "timestamp": now,
        }
        if alert_manager and alerts_config.get("motion_alerts", True):
            cam_label = _camera_display_name(camera_id)
            alert_manager.add_alert(
                AlertType.MOTION_DETECTED,
                f"Motion ended on camera {cam_label}",
                camera_id=camera_id,
                level=AlertLevel.INFO,
                data={
                    "phase": "last",
                    "session_id": session_id,
                    "snapshot": snapshot_path,
                    "last_snapshot": snapshot_path,
                },
                suppress_duplicates_seconds=alerts_config.get("suppress_duplicates_seconds", 5.0),
            )
        _audit(
            "motion_ended",
            f"camera_id={camera_id}, session_id={session_id}, snapshot={snapshot_path}",
        )
        _maybe_notify_away_motion_ended(camera_id, session_id, snapshot_path)

    return event


def _camera_source(camera) -> str:
    """Return feed source label for API consumers."""
    camera_type = str(camera.config.get("type", "")).lower()
    if camera_type == "network":
        return "rtsp"
    return "backend"


def _sanitize_camera_config(camera_config: Dict) -> Dict:
    """Strip secrets before returning config to clients."""
    safe = dict(camera_config)
    if "password" in safe:
        safe["password"] = "***" if safe["password"] else ""
    return safe


def _parse_normalized_zone(zone) -> Optional[Tuple[float, float, float, float]]:
    """Validate and parse a normalized zone [x, y, w, h] in 0-1 range."""
    if not isinstance(zone, (list, tuple)) or len(zone) != 4:
        return None
    try:
        x, y, w, h = (float(zone[0]), float(zone[1]), float(zone[2]), float(zone[3]))
    except (TypeError, ValueError):
        return None
    if not all(0.0 <= v <= 1.0 for v in (x, y, w, h)):
        return None
    if w <= 0 or h <= 0 or x + w > 1.0 + 1e-6 or y + h > 1.0 + 1e-6:
        return None
    return (x, y, w, h)


def _get_camera_zones_from_config(camera_id: str) -> List[List[float]]:
    """Load normalized zones for a camera from config."""
    cam_cfg = config.get("cameras", {}).get(camera_id, {})
    raw = cam_cfg.get("zones")
    if raw is None:
        legacy = motion_config.get("detection_zones", {})
        if isinstance(legacy, dict):
            raw = legacy.get(camera_id, [])
        else:
            raw = []
    zones = []
    for item in raw or []:
        parsed = _parse_normalized_zone(item)
        if parsed:
            zones.append(list(parsed))
    return zones


def _apply_zones_to_detector(detector: MotionDetector, zones: List[List[float]]) -> None:
    """Apply normalized zones to a motion detector."""
    parsed = []
    for item in zones:
        zone = _parse_normalized_zone(item)
        if zone:
            parsed.append(zone)
    detector.set_normalized_detection_zones(parsed)


def _ensure_camera_config_entry(camera_id: str) -> Dict:
    """Ensure cameras.{id} exists in config and return it."""
    if "cameras" not in config:
        config["cameras"] = {}
    if camera_id not in config["cameras"]:
        config["cameras"][camera_id] = {"type": "browser", "name": camera_id}
    return config["cameras"][camera_id]


def _camera_display_name(camera_id: str) -> str:
    """Human-friendly camera label for alerts and UI."""
    canonical_id = _normalize_camera_id(camera_id)
    cfg = config.get("cameras", {}).get(canonical_id, {})
    name = cfg.get("name")
    if name and str(name).strip() and str(name) != canonical_id:
        return str(name)
    if camera_manager and canonical_id in camera_manager.cameras:
        cam_cfg = getattr(camera_manager.cameras[canonical_id], "config", {}) or {}
        name = cam_cfg.get("name")
        if name and str(name).strip():
            return str(name)
    return canonical_id


def _camera_api_info(camera_id: str, camera) -> Dict:
    """Build camera metadata for GET /api/cameras."""
    source = _camera_source(camera)
    cfg = camera.config
    return {
        "id": camera_id,
        "name": cfg.get("name") or camera_id,
        "type": cfg.get("type", "webcam"),
        "source": source,
        "is_open": camera.is_open,
        "config": _sanitize_camera_config(cfg),
        "has_motion_detection": camera_id in motion_detectors,
        "is_recording": recorder.is_recording(camera_id) if recorder else False,
        "enabled": camera_id not in disabled_cameras,
    }


def _backend_capture_camera_ids() -> List[str]:
    """Camera IDs that should be captured server-side."""
    if not camera_manager:
        return []
    ids = []
    for cam_id, camera in camera_manager.cameras.items():
        cam_type = str(camera.config.get("type", "webcam")).lower()
        if cam_type == "network" or not prefer_browser_cameras:
            ids.append(cam_id)
    return ids


def _should_run_backend_capture() -> bool:
    return bool(_backend_capture_camera_ids())


def _capturing_local_webcams() -> bool:
    if not camera_manager or prefer_browser_cameras:
        return False
    return any(
        str(camera_manager.cameras[cid].config.get("type", "webcam")).lower() != "network"
        for cid in _backend_capture_camera_ids()
    )


async def _capture_backend_cameras_loop():
    """Continuously capture frames from backend cameras and process them."""
    global camera_capture_running
    if not _should_run_backend_capture():
        logger.info("Backend capture loop disabled (no server-side cameras)")
        return

    camera_capture_running = True
    logger.info("Starting backend camera capture loop")
    backend_capture_paused = False
    try:
        while camera_capture_running:
            capture_ids = set(_backend_capture_camera_ids())
            if not capture_ids:
                await asyncio.sleep(0.5)
                continue

            # Browser holds local webcams — pause only when capturing those.
            if _capturing_local_webcams() and active_connections:
                if not backend_capture_paused:
                    logger.info(
                        "Pausing local webcam capture while browser camera input is connected"
                    )
                    backend_capture_paused = True
                await asyncio.sleep(0.5)
                continue

            if backend_capture_paused:
                logger.info("Resuming backend camera capture")
                backend_capture_paused = False

            if camera_manager and camera_manager.cameras:
                try:
                    frames = await asyncio.to_thread(camera_manager.capture_all)
                    for cam_id, frame in frames.items():
                        if cam_id in disabled_cameras:
                            continue
                        if cam_id in capture_ids and frame is not None:
                            await asyncio.to_thread(
                                _process_camera_frame, cam_id, frame, "backend_capture"
                            )
                except Exception as e:
                    logger.error(f"Error in backend camera capture loop: {e}")
            await asyncio.sleep(1.0 / 30.0)
    finally:
        camera_capture_running = False
        logger.info("Stopped backend camera capture loop")


@app.on_event("startup")
async def on_startup():
    """Start background camera capture and retention cleanup."""
    global camera_capture_task, retention_cleanup_task
    if camera_capture_task is None:
        camera_capture_task = asyncio.create_task(_capture_backend_cameras_loop())
    if AUTO_DELETE_ENABLED and RETENTION_DAYS >= 1:
        try:
            await asyncio.to_thread(_run_retention_cleanup, "startup")
        except Exception as exc:
            logger.error("Startup retention cleanup failed: %s", exc)
        if retention_cleanup_task is None:
            retention_cleanup_task = asyncio.create_task(_retention_cleanup_loop())


@app.on_event("shutdown")
async def on_shutdown():
    """Stop background camera capture and flush recorders."""
    global camera_capture_running, camera_capture_task, retention_cleanup_task
    camera_capture_running = False
    if retention_cleanup_task:
        retention_cleanup_task.cancel()
        try:
            await retention_cleanup_task
        except asyncio.CancelledError:
            pass
        retention_cleanup_task = None
    if camera_capture_task:
        await asyncio.wait([camera_capture_task], timeout=2.0)
        camera_capture_task = None
    frame_processor.shutdown(wait=False, cancel_futures=True)
    if recorder:
        recorder.stop_all_recordings()


@app.websocket("/ws/camera/{camera_id}")
async def camera_stream_websocket(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for streaming camera feeds."""
    await websocket.accept()
    
    canonical_id = _normalize_camera_id(camera_id)

    if canonical_id not in camera_connections:
        camera_connections[canonical_id] = []
    camera_connections[canonical_id].append(websocket)
    
    logger.info(f"New camera stream connection for {canonical_id}. Total: {len(camera_connections[canonical_id])}")
    
    try:
        while True:
            # Send latest frame and/or motion metadata to subscribers.
            with processing_lock:
                frame = camera_frames.get(canonical_id)
                if frame is not None:
                    frame = frame.copy()
                timestamp = camera_frame_timestamps.get(canonical_id, time.time())
                motion_detected = camera_motion_status.get(canonical_id, False)
                motion_contours = camera_motion_contours.get(canonical_id, [])
                motion_event = camera_motion_events.get(canonical_id)
                camera_motion_events[canonical_id] = None

            payload = {
                "type": "frame",
                "camera_id": canonical_id,
                "timestamp": timestamp,
                "motion_detected": motion_detected,
                "motion_contours": motion_contours,
                "motion_event": motion_event,
            }

            if frame is not None:
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                payload["frame"] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
            else:
                payload["frame"] = None

            if payload["frame"] is None and not motion_detected and motion_event is None:
                await asyncio.sleep(0.1)
                continue

            try:
                await websocket.send_json(payload)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error sending frame: {e}")
                break
            
            await asyncio.sleep(0.033)  # ~30 FPS
            
    except WebSocketDisconnect:
        logger.info(f"Camera stream WebSocket disconnected for {canonical_id}")
    finally:
        if canonical_id in camera_connections and websocket in camera_connections[canonical_id]:
            camera_connections[canonical_id].remove(websocket)
            if not camera_connections[canonical_id]:
                del camera_connections[canonical_id]


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

                canonical_id = _normalize_camera_id(camera_id)
                if canonical_id in disabled_cameras:
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
                
                # Process asynchronously — don't block the input socket on motion detection.
                _schedule_browser_frame_processing(camera_id, img)
                
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
        cameras_info = {}
        if camera_manager:
            for camera_id, camera in camera_manager.cameras.items():
                cameras_info[camera_id] = _camera_api_info(camera_id, camera)

        # Include dynamically discovered input cameras not present in camera_manager.
        with processing_lock:
            for camera_id in camera_frames.keys():
                if camera_id not in cameras_info:
                    cameras_info[camera_id] = {
                        "id": camera_id,
                        "name": camera_id,
                        "type": "browser",
                        "source": "browser",
                        "is_open": True,
                        "config": {"source": "browser_input"},
                        "has_motion_detection": camera_id in motion_detectors,
                        "is_recording": recorder.is_recording(camera_id) if recorder else False,
                        "enabled": camera_id not in disabled_cameras,
                    }
        return {
            "cameras": cameras_info,
            "total": len(cameras_info),
            "prefer_browser_cameras": prefer_browser_cameras,
        }
    except Exception as e:
        logger.error(f"Error getting camera info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/cameras")
async def add_camera(body: Dict):
    """Add an RTSP/network camera and persist it to config."""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="Camera manager not available")

    camera_id = str(body.get("id") or body.get("camera_id") or "").strip()
    url = str(body.get("url") or "").strip()
    name = str(body.get("name") or camera_id).strip()
    username = body.get("username")
    password = body.get("password")

    if not camera_id:
        raise HTTPException(status_code=400, detail="id is required")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    if not url.lower().startswith(("rtsp://", "rtsps://")):
        raise HTTPException(status_code=400, detail="url must be an RTSP URL (rtsp://...)")

    if camera_id in camera_manager.cameras:
        raise HTTPException(status_code=409, detail=f"Camera {camera_id} already exists")

    camera_config = {
        "type": "network",
        "url": url,
        "name": name,
    }
    if username:
        camera_config["username"] = str(username)
    if password:
        camera_config["password"] = str(password)

    added = await asyncio.to_thread(camera_manager.add_camera, camera_id, camera_config)
    if not added:
        raise HTTPException(
            status_code=502,
            detail=f"Could not open RTSP stream for camera {camera_id}",
        )

    if "cameras" not in config:
        config["cameras"] = {}
    config["cameras"][camera_id] = camera_config
    try:
        await asyncio.to_thread(save_config, config, config_path)
    except Exception as exc:
        logger.error("Failed to save camera config: %s", exc)
        camera_manager.remove_camera(camera_id)
        raise HTTPException(status_code=500, detail="Camera opened but config save failed") from exc

    camera = camera_manager.cameras[camera_id]
    _audit("camera_added", f"camera_id={camera_id}, url={build_rtsp_url(url, username, '')}")
    return {"status": "success", "camera": _camera_api_info(camera_id, camera)}


@app.post("/api/cameras/{camera_id}/power")
async def set_camera_power(camera_id: str, body: Dict):
    """Enable or disable a camera feed (stops capture, motion, and recording)."""
    canonical_id = _normalize_camera_id(camera_id)
    enabled = bool(body.get("enabled", True))

    if enabled:
        disabled_cameras.discard(canonical_id)
        cam_cfg = config.get("cameras", {}).get(canonical_id)
        if (
            camera_manager
            and cam_cfg
            and str(cam_cfg.get("type", "")).lower() == "network"
            and canonical_id not in camera_manager.cameras
        ):
            opened = await asyncio.to_thread(camera_manager.add_camera, canonical_id, cam_cfg)
            if not opened:
                raise HTTPException(
                    status_code=502,
                    detail=f"Could not reopen RTSP stream for camera {canonical_id}",
                )
    else:
        disabled_cameras.add(canonical_id)
        if recorder and recorder.is_recording(canonical_id):
            await asyncio.to_thread(recorder.stop_recording, canonical_id)
        if camera_manager and canonical_id in camera_manager.cameras:
            cam = camera_manager.cameras[canonical_id]
            if str(cam.config.get("type", "")).lower() == "network":
                await asyncio.to_thread(camera_manager.remove_camera, canonical_id)
        with processing_lock:
            camera_frames.pop(canonical_id, None)
            camera_raw_frames.pop(canonical_id, None)
            camera_frame_timestamps.pop(canonical_id, None)
            camera_motion_status[canonical_id] = False
            camera_motion_contours.pop(canonical_id, None)

    _audit("camera_power", f"camera_id={canonical_id}, enabled={enabled}")
    return {"status": "success", "camera_id": canonical_id, "enabled": enabled}


@app.post("/api/cameras/scan")
async def scan_network_cameras(body: Optional[Dict] = None):
    """Scan the local network for potential IP cameras."""
    body = body or {}
    network = body.get("network")
    try:
        if not network:
            local_ip = await asyncio.to_thread(_get_local_ip_safe)
            network = discover_network_range(local_ip)
        results = await asyncio.to_thread(scan_network, network)
        devices = []
        for item in results:
            if not item.get("is_camera"):
                continue
            ip = item.get("ip", "")
            rtsp_ports = [p for p in item.get("open_ports", []) if p in (554, 8554, 10554)]
            suggested_url = None
            if rtsp_ports:
                suggested_url = f"rtsp://{ip}:{rtsp_ports[0]}/"
            devices.append(
                {
                    "ip": ip,
                    "hostname": item.get("hostname") or "",
                    "open_ports": item.get("open_ports", []),
                    "endpoints": item.get("camera_endpoints", []),
                    "suggested_rtsp_url": suggested_url,
                }
            )
        return {"network": network, "devices": devices, "total": len(devices)}
    except Exception as exc:
        logger.error("Network camera scan failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/cameras/{camera_id}/zones")
async def get_camera_zones(camera_id: str):
    """Return normalized detection zones for a camera."""
    canonical_id = _normalize_camera_id(camera_id)
    zones = _get_camera_zones_from_config(canonical_id)
    return {"camera_id": canonical_id, "zones": zones}


@app.put("/api/cameras/{camera_id}/zones")
async def put_camera_zones(camera_id: str, body: Dict):
    """Save normalized detection zones for a camera and apply to runtime detector."""
    canonical_id = _normalize_camera_id(camera_id)
    raw_zones = body.get("zones")
    if not isinstance(raw_zones, list):
        raise HTTPException(status_code=400, detail="zones must be an array of [x, y, w, h]")

    parsed_zones = []
    for item in raw_zones:
        zone = _parse_normalized_zone(item)
        if zone is None:
            raise HTTPException(
                status_code=400,
                detail="Each zone must be [x, y, w, h] with values in 0-1 and x+w, y+h <= 1",
            )
        parsed_zones.append(list(zone))

    cam_cfg = _ensure_camera_config_entry(canonical_id)
    cam_cfg["zones"] = parsed_zones
    try:
        await asyncio.to_thread(save_config, config, config_path)
    except Exception as exc:
        logger.error("Failed to save zones for %s: %s", canonical_id, exc)
        raise HTTPException(status_code=500, detail="Failed to persist zones") from exc

    detector = _ensure_motion_detector(canonical_id)
    if detector:
        _apply_zones_to_detector(detector, parsed_zones)

    _audit("zones_updated", f"camera_id={canonical_id}, count={len(parsed_zones)}")
    return {"status": "success", "camera_id": canonical_id, "zones": parsed_zones}


@app.get("/api/motion/status")
async def get_motion_status(camera_id: Optional[str] = None):
    """Get motion detection status."""
    try:
        if camera_id:
            canonical_id = _normalize_camera_id(camera_id)
            if canonical_id in motion_detectors:
                stats = motion_detectors[canonical_id].get_statistics()
                return {"camera_id": canonical_id, **stats}
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
        canonical_id = _normalize_camera_id(camera_id)
        if canonical_id not in motion_detectors:
            raise HTTPException(status_code=404, detail=f"Motion detector not found for camera {camera_id}")
        
        detector = motion_detectors[canonical_id]
        detector.update_settings(
            sensitivity=config_data.get("sensitivity"),
            min_area=config_data.get("min_area"),
            var_threshold=config_data.get("var_threshold")
        )
        return {"status": "success", "camera_id": canonical_id}
    except Exception as e:
        logger.error(f"Error configuring motion detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/start")
async def start_recording(camera_id: str, motion_triggered: bool = False):
    """Start recording for a camera."""
    try:
        if not recorder:
            raise HTTPException(status_code=503, detail="Recording not enabled")
        
        canonical_id = _normalize_camera_id(camera_id)

        if canonical_id not in camera_raw_frames:
            raise HTTPException(status_code=404, detail=f"No frames available for camera {camera_id}")
        
        with processing_lock:
            frame = camera_raw_frames.get(canonical_id)
            if frame is None:
                raise HTTPException(status_code=404, detail=f"No frame available for camera {camera_id}")
            h, w = frame.shape[:2]
        
        success = recorder.start_recording(canonical_id, w, h, motion_triggered=motion_triggered)
        if success:
            if not motion_triggered:
                _clear_motion_recording_suppress(canonical_id)
            _audit(
                "recording_started",
                f"camera_id={canonical_id}, motion_triggered={motion_triggered}",
            )
            return {"status": "success", "camera_id": canonical_id, "recording": True}
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
        
        canonical_id = _normalize_camera_id(camera_id)
        filepath = recorder.stop_recording(canonical_id)
        _suppress_motion_recording(canonical_id)
        if filepath:
            _audit(
                "recording_stopped",
                f"camera_id={canonical_id}, filepath={filepath}",
            )
            return {"status": "success", "camera_id": canonical_id, "recording": False, "filepath": str(filepath)}
        return {
            "status": "success",
            "camera_id": canonical_id,
            "recording": False,
            "already_stopped": True,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/recording/stop-all")
async def stop_all_recordings():
    """Stop every active recording and pause motion-triggered restart briefly."""
    try:
        if not recorder:
            raise HTTPException(status_code=503, detail="Recording not enabled")
        stopped = []
        for camera_id in recorder.active_camera_ids():
            filepath = recorder.stop_recording(camera_id)
            _suppress_motion_recording(camera_id)
            stopped.append(
                {"camera_id": camera_id, "filepath": str(filepath) if filepath else None}
            )
            _audit(
                "recording_stopped",
                f"camera_id={camera_id}, stop_all=true, filepath={filepath or 'n/a'}",
            )
        return {"status": "success", "recording": False, "stopped": stopped}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping all recordings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/api/recording/status")
async def get_recording_status(camera_id: Optional[str] = None):
    """Get recording status."""
    try:
        if not recorder:
            return {"enabled": False}
        
        if camera_id:
            canonical_id = _normalize_camera_id(camera_id)
            is_recording = recorder.is_recording(canonical_id)
            return {"enabled": True, "camera_id": canonical_id, "recording": is_recording}
        else:
            all_status = {}
            with processing_lock:
                camera_ids = set(camera_frames.keys())
                if camera_manager:
                    camera_ids.update(camera_manager.cameras.keys())
            if recorder:
                camera_ids.update(recorder.active_camera_ids())
            for cam_id in sorted(camera_ids):
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


@app.get("/api/security/settings")
async def get_security_settings():
    """Get runtime security settings."""
    return {
        "motion_detection_enabled": security_state["motion_detection_enabled"],
        "motion_triggered_recording": security_state["motion_triggered_recording"],
        "recording_enabled": recorder is not None,
    }


@app.post("/api/security/settings")
async def update_security_settings(settings: dict):
    """Update runtime security settings used by the frame processing pipeline."""
    if "motion_detection_enabled" in settings:
        security_state["motion_detection_enabled"] = bool(settings["motion_detection_enabled"])
        if not security_state["motion_detection_enabled"]:
            security_state["motion_triggered_recording"] = False
    if "motion_triggered_recording" in settings:
        security_state["motion_triggered_recording"] = bool(settings["motion_triggered_recording"])
    return {
        "status": "success",
        "settings": {
            "motion_detection_enabled": security_state["motion_detection_enabled"],
            "motion_triggered_recording": security_state["motion_triggered_recording"],
        },
    }


@app.get("/api/media/motion-sessions")
async def list_motion_sessions(limit: int = 40):
    """List paired motion snapshot sessions (first + last)."""
    sessions = motion_store.list_sessions(limit=limit)
    face_enabled = face_memory.enabled
    if face_enabled:
        sessions = face_memory.attach_session_detections(sessions)
    return {
        "sessions": sessions,
        "face_recognition_enabled": face_enabled,
    }


@app.get("/api/media/recordings")
async def list_recordings(limit: int = 40):
    """List video recordings on disk."""
    dirs = collect_recordings_dirs(
        Path(project_root),
        recording_config.get("output_dir", "recordings"),
        Path(recorder.output_dir) if recorder else None,
    )
    return {
        "recordings": list_recording_files(dirs, Path(project_root), limit=limit),
    }


@app.get("/api/media/file")
async def serve_media_file(path: str):
    """Serve a snapshot or recording file by project-relative path."""
    allowed = _allowed_media_dirs()
    try:
        resolved = resolve_media_path(path, Path(project_root), allowed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        resolved,
        media_type=media_mime_type(resolved),
        headers={"Accept-Ranges": "bytes"},
    )


@app.delete("/api/media/file")
async def delete_media_file_endpoint(path: str):
    """Delete a snapshot or recording by project-relative path."""
    allowed = _allowed_media_dirs()
    try:
        result = delete_media_file(path, Path(project_root), allowed)
        _audit("manual_delete", f"path={path}, count=1")
        return {"status": "success", **result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/media/delete")
async def delete_media_bulk(body: Dict):
    """Delete multiple media files. Body: { \"paths\": [\"...\"] }."""
    paths = body.get("paths") or []
    if not isinstance(paths, list) or not paths:
        raise HTTPException(status_code=400, detail="paths must be a non-empty list")
    allowed = _allowed_media_dirs()
    result = delete_media_files(paths, Path(project_root), allowed)
    _audit("manual_delete", f"bulk=true, {format_delete_summary(result)}")
    return {"status": "success", **result}


@app.delete("/api/media/motion-sessions/{session_id}")
async def delete_motion_session(session_id: str, camera_id: str):
    """Delete paired first/last snapshots for a motion session."""
    paths = motion_store.session_snapshot_paths(session_id, camera_id)
    if not paths:
        raise HTTPException(status_code=404, detail="Motion session not found")
    allowed = _allowed_media_dirs()
    result = delete_media_files(paths, Path(project_root), allowed)
    motion_store.remove_from_index(session_id, camera_id)
    _audit(
        "manual_delete",
        f"session_id={session_id}, camera_id={camera_id}, {format_delete_summary(result)}",
    )
    return {"status": "success", "session_id": session_id, "camera_id": camera_id, **result}


@app.post("/api/media/delete-older")
async def delete_older_media_endpoint(body: Dict):
    """Delete media older than N days. Body: { older_than_days, include_recordings?, include_snapshots? }."""
    days = int(body.get("older_than_days", 0))
    include_recordings = bool(body.get("include_recordings", True))
    include_snapshots = bool(body.get("include_snapshots", True))
    if days < 1:
        raise HTTPException(status_code=400, detail="older_than_days must be at least 1")
    try:
        result = delete_older_media(
            Path(project_root),
            _allowed_media_dirs(),
            _recordings_dirs_live(),
            MOTION_SNAPSHOT_DIR,
            days,
            include_recordings=include_recordings,
            include_snapshots=include_snapshots,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _audit("manual_delete", f"older_than_days={days}, {format_delete_summary(result)}")
    return {"status": "success", **result}


@app.get("/api/analytics/summary")
async def analytics_summary():
    """Aggregate dashboard stats from motion sessions, recordings, and alerts."""
    return _analytics_summary()


@app.get("/api/faces/persons")
async def list_known_people():
    """List known people with summary metadata."""
    if not face_memory.enabled:
        return {"enabled": False, "persons": []}
    return {"enabled": True, "runtime_ready": face_memory.runtime_ready, "persons": face_memory.get_people_summary()}


@app.get("/api/faces/sightings")
async def list_face_sightings(person_id: Optional[str] = None, limit: int = 200):
    """List face sightings, optionally filtered by person."""
    if not face_memory.enabled:
        return {"enabled": False, "sightings": []}
    return {
        "enabled": True,
        "runtime_ready": face_memory.runtime_ready,
        "sightings": face_memory.list_sightings(person_id=person_id, limit=limit),
    }


@app.post("/api/faces/enroll")
async def enroll_face_from_snapshot(body: Dict):
    """Enroll one face from a snapshot path."""
    if not face_memory.enabled:
        raise HTTPException(status_code=503, detail="Face recognition is disabled")
    snapshot_path = str(body.get("snapshot_path") or "").strip()
    camera_id = str(body.get("camera_id") or "manual")
    person_id = body.get("person_id")
    if not snapshot_path:
        raise HTTPException(status_code=400, detail="snapshot_path is required")
    try:
        result = face_memory.enroll_from_snapshot(snapshot_path, camera_id, person_id=person_id)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.put("/api/faces/persons/{person_id}")
async def rename_known_person(person_id: str, body: Dict):
    """Rename person label."""
    if not face_memory.enabled:
        raise HTTPException(status_code=503, detail="Face recognition is disabled")
    name = str(body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    try:
        person = face_memory.rename_person(person_id, name)
        return {"status": "success", "person": person}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"person not found: {exc}") from exc


@app.post("/api/faces/persons/merge")
async def merge_known_people(body: Dict):
    """Merge source person into target person."""
    if not face_memory.enabled:
        raise HTTPException(status_code=503, detail="Face recognition is disabled")
    source_person_id = str(body.get("source_person_id") or "").strip()
    target_person_id = str(body.get("target_person_id") or "").strip()
    if not source_person_id or not target_person_id:
        raise HTTPException(status_code=400, detail="source_person_id and target_person_id are required")
    try:
        return face_memory.merge_people(source_person_id, target_person_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"person not found: {exc}") from exc


@app.get("/api/faces/similar-pairs")
async def list_similar_face_pairs(min_similarity: Optional[float] = None):
    """Suggest person profiles that likely depict the same face."""
    if not face_memory.enabled:
        return {"enabled": False, "pairs": [], "threshold": face_memory.similarity_threshold}
    pairs = face_memory.find_similar_pairs(min_similarity=min_similarity)
    return {
        "enabled": True,
        "threshold": min_similarity if min_similarity is not None else face_memory.similarity_threshold,
        "pairs": pairs,
    }


@app.post("/api/faces/persons/merge-similar")
async def merge_similar_face_pairs(body: Optional[Dict] = None):
    """Merge all person pairs above the similarity threshold."""
    if not face_memory.enabled:
        raise HTTPException(status_code=503, detail="Face recognition is disabled")
    body = body or {}
    min_similarity = body.get("min_similarity")
    try:
        min_sim = float(min_similarity) if min_similarity is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="min_similarity must be a number") from None
    result = face_memory.merge_all_similar_pairs(min_similarity=min_sim)
    _audit("faces_merge_similar", f"pairs={result.get('pairs_merged', 0)}, moved={result.get('sightings_moved', 0)}")
    return result


@app.post("/api/faces/sightings/reassign")
async def reassign_face_sighting(body: Dict):
    """Move sighting to an existing or new person."""
    if not face_memory.enabled:
        raise HTTPException(status_code=503, detail="Face recognition is disabled")
    sighting_id = str(body.get("sighting_id") or "").strip()
    target_person_id = body.get("target_person_id")
    create_person_name = body.get("create_person_name")
    if not sighting_id:
        raise HTTPException(status_code=400, detail="sighting_id is required")
    try:
        return face_memory.reassign_sighting(sighting_id, target_person_id, create_person_name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"not found: {exc}") from exc


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "cameras": len(camera_manager.cameras) if camera_manager else 0,
        "network_cameras": len(network_camera_configs),
        "prefer_browser_cameras": prefer_browser_cameras,
        "backend_capture": _should_run_backend_capture(),
        "connections": len(active_connections),
        "motion_detection_enabled": security_state["motion_detection_enabled"],
        "recording_enabled": recorder is not None,
        "alerts_enabled": alert_manager is not None,
        "face_recognition_enabled": face_memory.enabled,
        "face_runtime_ready": face_memory.runtime_ready,
        "media_api": True,
        "analytics_api": True,
        "faces_api": True,
        "rtsp_api": True,
        "zones_api": True,
        "recording_stop_all_api": True,
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
            reload=False,
            workers=1,
        )
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise
