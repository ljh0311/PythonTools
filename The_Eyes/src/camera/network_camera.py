#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Network (RTSP) camera support for The Eyes.

Opens IP cameras via OpenCV/ffmpeg, embeds optional credentials in the URL,
and auto-reconnects when reads fail.
"""

import logging
import time
from typing import Dict, Optional, Tuple, Union
from urllib.parse import quote, urlparse, urlunparse

import cv2
import numpy as np

from ..utils.exceptions import CameraError


def build_rtsp_url(
    url: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> str:
    """Insert credentials into an RTSP URL when not already present."""
    if not url:
        return url
    if not username and not password:
        return url

    parsed = urlparse(url)
    if parsed.scheme not in ("rtsp", "rtsps"):
        return url
    if parsed.username:
        return url

    user = quote(username or "", safe="")
    pwd = quote(password or "", safe="")
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{user}:{pwd}@{host}{port}" if user else host
    return urlunparse(
        (parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment)
    )


class NetworkCamera:
    """RTSP/IP camera using OpenCV VideoCapture (duck-compatible with Camera)."""

    def __init__(self, camera_id: Union[int, str], config: Dict):
        self.camera_id = camera_id
        self.config = config
        self.logger = logging.getLogger(f"the_eyes.camera.{camera_id}")
        self.is_open = False
        self.calibration_data = None
        self.cap: Optional[cv2.VideoCapture] = None
        self._reconnect_delay = float(config.get("reconnect_delay", 2.0))
        self._last_reconnect_attempt = 0.0

    def _stream_url(self) -> str:
        return build_rtsp_url(
            self.config.get("url", ""),
            self.config.get("username"),
            self.config.get("password"),
        )

    def _open_capture(self) -> bool:
        url = self._stream_url()
        if not url:
            self.logger.error("No RTSP URL configured for camera %s", self.camera_id)
            return False

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        buffer_size = self.config.get("buffer_size")
        if buffer_size is not None:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, int(buffer_size))

        width = self.config.get("width")
        height = self.config.get("height")
        if width and height:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))

        self.is_open = self.cap.isOpened()
        if self.is_open:
            self.logger.info("Opened network camera %s", self.camera_id)
        else:
            self.logger.warning("Failed to open network camera %s", self.camera_id)
        return self.is_open

    def open(self) -> bool:
        try:
            return self._open_capture()
        except Exception as exc:
            self.logger.error("Error opening network camera %s: %s", self.camera_id, exc)
            self.is_open = False
            return False

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_open = False
        self.logger.info("Closed network camera %s", self.camera_id)

    def _reconnect(self) -> bool:
        now = time.time()
        if now - self._last_reconnect_attempt < self._reconnect_delay:
            return False
        self._last_reconnect_attempt = now
        self.logger.info("Reconnecting network camera %s", self.camera_id)
        return self._open_capture()

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read one frame; returns (success, frame)."""
        if not self.is_open:
            if not self._reconnect():
                return False, None

        ret, frame = self.cap.read()
        if not ret or frame is None:
            if self._reconnect():
                ret, frame = self.cap.read()
            if not ret or frame is None:
                return False, None
        return True, frame

    def capture(self) -> np.ndarray:
        """Capture a frame (raises CameraError on failure)."""
        ret, frame = self.read()
        if not ret or frame is None:
            raise CameraError(f"Failed to capture frame from network camera {self.camera_id}")
        return frame
