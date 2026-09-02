#!/usr/bin/env python
"""Fetch OpenCV YuNet face detector ONNX into BrightnessController/models/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from face_detector_backend import download_yunet_model, yunet_model_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the model file already exists",
    )
    args = parser.parse_args()
    path = download_yunet_model(force=args.force)
    print(f"Model ready: {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
