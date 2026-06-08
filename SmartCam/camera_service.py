"""
Camera service utilities for SmartCam.

Provides:
  - Platform-aware OpenCV backend selection for Windows / Linux / Raspberry Pi.
  - A `FrameSource` class that owns a single reader thread for a `cv2.VideoCapture`
    handle so multiple consumers (GUI preview + AI processing pipeline) can share
    the latest frame without contending for `cap.read()`.

This keeps `main.py` modular and lets us unit test backend selection without
hardware.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def is_raspberry_pi() -> bool:
    """Best-effort detection of a Raspberry Pi host."""
    try:
        machine = platform.machine().lower()
        if machine.startswith("arm") or machine.startswith("aarch64"):
            cpuinfo = "/proc/cpuinfo"
            if os.path.exists(cpuinfo):
                with open(cpuinfo, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().lower()
                if "raspberry pi" in text or "bcm" in text:
                    return True
            model_path = "/proc/device-tree/model"
            if os.path.exists(model_path):
                with open(model_path, "r", encoding="utf-8", errors="ignore") as f:
                    if "raspberry pi" in f.read().lower():
                        return True
    except Exception:
        pass
    return False


def get_default_backend_preference() -> List[int]:
    """
    Return an OS-appropriate ordered list of OpenCV `CAP_*` backends to try.

    The fallback chain always ends with `cv2.CAP_ANY` so OpenCV can pick whatever
    is available. Missing constants on a given OpenCV build are silently skipped.
    """
    candidates: List[str]
    if sys.platform.startswith("win"):
        candidates = ["CAP_DSHOW", "CAP_MSMF", "CAP_ANY"]
    elif sys.platform == "darwin":
        candidates = ["CAP_AVFOUNDATION", "CAP_ANY"]
    elif is_raspberry_pi():
        candidates = ["CAP_V4L2", "CAP_GSTREAMER", "CAP_ANY"]
    else:
        candidates = ["CAP_V4L2", "CAP_GSTREAMER", "CAP_ANY"]

    backends: List[int] = []
    for name in candidates:
        value = getattr(cv2, name, None)
        if isinstance(value, int) and value not in backends:
            backends.append(value)
    if not backends:
        backends = [cv2.CAP_ANY]
    return backends


def resolve_backend_preference(setting: Any) -> List[int]:
    """
    Translate a backend preference setting into a list of `CAP_*` ints.

    Accepts:
      - "auto" or None: use platform default.
      - A single string, e.g. "CAP_DSHOW".
      - A list of strings or ints.
      - A single int.
    """
    if setting is None or setting == "auto":
        return get_default_backend_preference()

    items: List[Any]
    if isinstance(setting, (list, tuple)):
        items = list(setting)
    else:
        items = [setting]

    resolved: List[int] = []
    for item in items:
        if isinstance(item, int):
            resolved.append(item)
            continue
        if isinstance(item, str):
            value = getattr(cv2, item, None)
            if isinstance(value, int):
                resolved.append(value)
                continue
        logger.warning("Ignoring unknown camera backend value: %r", item)

    if not resolved:
        return get_default_backend_preference()

    if cv2.CAP_ANY not in resolved:
        resolved.append(cv2.CAP_ANY)
    return resolved


def open_capture(
    camera_id: int,
    backend_preference: Optional[List[int]] = None,
) -> Tuple[Optional[cv2.VideoCapture], Optional[int]]:
    """
    Try to open a `cv2.VideoCapture` using the given (or platform default)
    backend preference order.

    Returns:
        (capture, backend_id) on success, or (None, None) if no backend opens.
        The caller owns the returned capture and is responsible for releasing it.
    """
    if backend_preference is None:
        backend_preference = get_default_backend_preference()

    last_error: Optional[Exception] = None
    for backend in backend_preference:
        try:
            cap = cv2.VideoCapture(camera_id, backend)
            if cap.isOpened():
                logger.info(
                    "Opened camera %s using backend %s",
                    camera_id, _backend_name(backend)
                )
                return cap, backend
            cap.release()
        except Exception as e:
            last_error = e
            logger.debug(
                "Backend %s failed for camera %s: %s",
                _backend_name(backend), camera_id, e
            )

    if last_error:
        logger.warning(
            "Could not open camera %s with any backend (last error: %s)",
            camera_id, last_error
        )
    else:
        logger.warning("Could not open camera %s with any backend", camera_id)
    return None, None


def _backend_name(backend_id: int) -> str:
    """Return a friendly name for a `cv2.CAP_*` backend id."""
    for attr in dir(cv2):
        if attr.startswith("CAP_") and getattr(cv2, attr, None) == backend_id:
            return attr
    return f"backend_{backend_id}"


class FrameSource:
    """
    Thread-safe single reader for a `cv2.VideoCapture`.

    Owns the reading thread; consumers call `latest_frame()` (non-blocking) to
    get the most recent frame snapshot. This keeps only ONE thread calling
    `cap.read()`, which avoids contention/lockups when both the GUI preview and
    the AI processing pipeline want frames concurrently.
    """

    def __init__(
        self,
        cap: cv2.VideoCapture,
        sleep_when_idle: float = 0.005,
        sleep_on_error: float = 0.1,
        name: str = "FrameSource",
    ) -> None:
        if cap is None:
            raise ValueError("FrameSource requires a valid cv2.VideoCapture")
        self._cap = cap
        self._lock = threading.Lock()
        self._frame_lock = threading.Lock()
        self._latest: Optional[Tuple[np.ndarray, datetime, int]] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sleep_when_idle = sleep_when_idle
        self._sleep_on_error = sleep_on_error
        self._name = name
        self._error_count = 0

    def start(self) -> None:
        """Start the background reader thread (idempotent)."""
        if self._running and self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name=self._name, daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Stop the background reader thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        """Internal reader loop."""
        while self._running:
            try:
                with self._lock:
                    ret, frame = self._cap.read()
                if not ret or frame is None:
                    self._error_count += 1
                    time.sleep(self._sleep_on_error)
                    continue
                self._error_count = 0
                snapshot = (frame, datetime.now(), int(time.time() * 1000))
                with self._frame_lock:
                    self._latest = snapshot
                time.sleep(self._sleep_when_idle)
            except Exception as e:
                self._error_count += 1
                logger.debug("FrameSource read error: %s", e)
                time.sleep(self._sleep_on_error)

    def latest_frame(self, copy: bool = True) -> Optional[Tuple[np.ndarray, datetime, int]]:
        """
        Return the most recent (frame, timestamp, frame_id) tuple.

        Returns None if no frame has been captured yet. By default returns a
        defensive copy of the frame so consumers can mutate it without racing
        the reader thread.
        """
        with self._frame_lock:
            snapshot = self._latest
        if snapshot is None:
            return None
        frame, ts, fid = snapshot
        if copy:
            frame = frame.copy()
        return frame, ts, fid

    def read_once(self, timeout: float = 1.0) -> Optional[np.ndarray]:
        """
        Return a single frame.

        - If the background pump is running, wait up to `timeout` seconds for
          a fresh frame and return its copy.
        - Otherwise, read directly from the capture under the lock.
        """
        if self.is_running():
            deadline = time.time() + timeout
            while time.time() < deadline:
                snapshot = self.latest_frame(copy=True)
                if snapshot is not None:
                    return snapshot[0]
                time.sleep(0.01)
            return None

        with self._lock:
            ret, frame = self._cap.read()
        if not ret or frame is None:
            return None
        return frame

    @property
    def cap(self) -> cv2.VideoCapture:
        """Underlying capture (use only for `get`/`set` of properties)."""
        return self._cap
