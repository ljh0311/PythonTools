"""
Face detection backends for BrightnessController.

Prefers OpenCV YuNet (FaceDetectorYN) for better non-frontal recall; falls back
to frontal + profile Haar cascades when the ONNX model is unavailable.
"""

from __future__ import annotations

import os
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np

Rect = Tuple[int, int, int, int]

YUNET_MODEL_NAME = "face_detection_yunet_2023mar.onnx"
YUNET_MODEL_URLS = [
    "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
    "https://github.com/opencv/opencv_zoo/raw/refs/heads/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
]
YUNET_MIN_BYTES = 100_000


def models_dir() -> Path:
    return Path(__file__).resolve().parent / "models"


def yunet_model_path() -> Path:
    return models_dir() / YUNET_MODEL_NAME


def download_yunet_model(force: bool = False) -> Path:
    """Download YuNet ONNX into BrightnessController/models/ if missing."""
    path = yunet_model_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not force and path.exists() and path.stat().st_size >= YUNET_MIN_BYTES:
        return path

    last_error: Optional[Exception] = None
    for url in YUNET_MODEL_URLS:
        try:
            urllib.request.urlretrieve(url, path)
            if path.exists() and path.stat().st_size >= YUNET_MIN_BYTES:
                return path
            last_error = RuntimeError(
                f"downloaded file too small ({path.stat().st_size} bytes)"
            )
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to download {YUNET_MODEL_NAME}: {last_error}")


def _load_cascade(filename: str) -> Optional[cv2.CascadeClassifier]:
    candidates = [
        cv2.data.haarcascades + filename,
        filename,
        f"data/{filename}",
        f"/usr/share/opencv4/haarcascades/{filename}",
    ]
    for path in candidates:
        if os.path.exists(path):
            cascade = cv2.CascadeClassifier(path)
            if not cascade.empty():
                return cascade
    return None


class FaceDetectorBackend:
    """YuNet-first face detector with Haar cascade fallback."""

    BACKEND_YUNET = "yunet"
    BACKEND_HAAR = "haar"

    def __init__(self, auto_download: bool = True):
        self.auto_download = auto_download
        self.backend_name: Optional[str] = None
        self.yunet: Optional[cv2.FaceDetectorYN] = None
        self.face_cascade: Optional[cv2.CascadeClassifier] = None
        self.profile_cascade: Optional[cv2.CascadeClassifier] = None
        self._yunet_input_size: Optional[Tuple[int, int]] = None
        self._clahe: Optional[cv2.CLAHE] = None

    @property
    def is_ready(self) -> bool:
        return self.backend_name is not None

    def setup(self) -> bool:
        if self._setup_yunet():
            return True
        return self._setup_haar()

    def _setup_yunet(self) -> bool:
        if not hasattr(cv2, "FaceDetectorYN"):
            return False
        try:
            model = yunet_model_path()
            if not model.exists() or model.stat().st_size < YUNET_MIN_BYTES:
                if self.auto_download:
                    download_yunet_model()
                else:
                    return False
            self.yunet = cv2.FaceDetectorYN.create(
                str(model),
                "",
                (320, 320),
                score_threshold=0.6,
                nms_threshold=0.3,
                top_k=5000,
            )
            self.backend_name = self.BACKEND_YUNET
            print("✅ YuNet face detection model loaded")
            return True
        except Exception as exc:
            print(f"⚠️ YuNet unavailable ({exc}); falling back to Haar cascades")
            self.yunet = None
            return False

    def _setup_haar(self) -> bool:
        try:
            self.face_cascade = _load_cascade("haarcascade_frontalface_default.xml")
            self.profile_cascade = _load_cascade("haarcascade_profileface.xml")
            if self.face_cascade is None:
                print("⚠️ Warning: Could not load face detection model.")
                return False
            self.backend_name = self.BACKEND_HAAR
            if self.profile_cascade is not None:
                print("✅ Frontal and profile Haar face detection models loaded")
            else:
                print("✅ Haar face detection model loaded (frontal only)")
            return True
        except Exception as exc:
            print(f"⚠️ Warning: Error loading Haar face detection: {exc}")
            return False

    def _prepare_gray(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._clahe is None:
            self._clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return self._clahe.apply(gray)

    def _haar_params(self, *, desk_mode: bool, strict_detection: bool) -> dict:
        if desk_mode:
            return {"scaleFactor": 1.1, "minNeighbors": 5, "minSize": (40, 40)}
        if strict_detection:
            return {"scaleFactor": 1.2, "minNeighbors": 12, "minSize": (60, 60)}
        return {"scaleFactor": 1.15, "minNeighbors": 8, "minSize": (50, 50)}

    def _detect_haar(
        self,
        frame: np.ndarray,
        *,
        desk_mode: bool,
        strict_detection: bool,
    ) -> List[Rect]:
        gray = self._prepare_gray(frame)
        params = self._haar_params(desk_mode=desk_mode, strict_detection=strict_detection)
        rects: List[Rect] = []
        for cascade in (self.face_cascade, self.profile_cascade):
            if cascade is not None and not cascade.empty():
                found = cascade.detectMultiScale(gray, **params)
                if len(found) > 0:
                    rects.extend(
                        [(int(x), int(y), int(w), int(h)) for x, y, w, h in found]
                    )
        return rects

    def _detect_yunet(
        self,
        frame: np.ndarray,
        *,
        desk_mode: bool,
        strict_detection: bool,
    ) -> List[Rect]:
        if self.yunet is None:
            return []
        h, w = frame.shape[:2]
        if self._yunet_input_size != (w, h):
            self.yunet.setInputSize((w, h))
            self._yunet_input_size = (w, h)

        if desk_mode:
            score = 0.5
        elif strict_detection:
            score = 0.65
        else:
            score = 0.55
        self.yunet.setScoreThreshold(score)

        _, faces = self.yunet.detect(frame)
        if faces is None or len(faces) == 0:
            return []
        rects: List[Rect] = []
        for face in faces:
            x, y, fw, fh = face[:4]
            rects.append((int(x), int(y), int(fw), int(fh)))
        return rects

    def detect_rects(
        self,
        frame: np.ndarray,
        *,
        desk_mode: bool = False,
        strict_detection: bool = False,
    ) -> List[Rect]:
        if not self.is_ready:
            return []
        if self.backend_name == self.BACKEND_YUNET:
            return self._detect_yunet(
                frame, desk_mode=desk_mode, strict_detection=strict_detection
            )
        return self._detect_haar(
            frame, desk_mode=desk_mode, strict_detection=strict_detection
        )
