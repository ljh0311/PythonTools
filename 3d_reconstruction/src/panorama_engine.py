"""
360-degree equirectangular spherical panorama from multiple keyframe images.
Uses pose estimation (rotation only) and projects each image onto a sphere.
"""

import cv2
import numpy as np
from typing import List, Optional

from reconstruction_engine import ReconstructionEngine


# Default equirectangular canvas: width = 2 * height (360° x 180°)
DEFAULT_PANORAMA_HEIGHT = 1024
DEFAULT_PANORAMA_WIDTH = 2048


def _camera_rays_grid(h: int, w: int, fx: float, fy: float, cx: float, cy: float) -> np.ndarray:
    """All ray directions for image grid (h, w). Returns (H*W, 3) normalized rays in camera frame."""
    vv, uu = np.mgrid[0:h, 0:w].astype(np.float64)
    x = (uu.ravel() - cx) / fx
    y = (vv.ravel() - cy) / fy
    z = np.ones_like(x)
    rays = np.stack([x, y, z], axis=1)
    norms = np.linalg.norm(rays, axis=1, keepdims=True) + 1e-10
    return rays / norms


def _rays_to_equirect_pixels(rays_world: np.ndarray, width: int, height: int) -> np.ndarray:
    """Map (N, 3) unit rays to equirectangular pixel coords (N, 2)."""
    x, y, z = rays_world[:, 0], rays_world[:, 1], rays_world[:, 2]
    lon = np.arctan2(x, z)
    lon = np.where(lon < 0, lon + 2 * np.pi, lon)
    lat = np.arcsin(np.clip(-y, -1.0, 1.0))
    px = (lon / (2 * np.pi)) * width
    py = (0.5 - lat / np.pi) * height
    return np.stack([px, py], axis=1)


def build_equirectangular_panorama(
    keyframes: List[np.ndarray],
    engine: ReconstructionEngine,
    panorama_width: int = DEFAULT_PANORAMA_WIDTH,
    panorama_height: int = DEFAULT_PANORAMA_HEIGHT,
) -> Optional[np.ndarray]:
    """
    Build a 360° equirectangular panorama from keyframe images.

    Args:
        keyframes: List of BGR images (same size).
        engine: ReconstructionEngine used for estimate_camera_pose.
        panorama_width: Output equirectangular width (typically 2 * height).
        panorama_height: Output equirectangular height.

    Returns:
        BGR panorama image, or None if insufficient keyframes/poses.
    """
    if len(keyframes) < 1:
        return None

    n = len(keyframes)
    h, w = keyframes[0].shape[:2]
    fx = float(w)
    fy = float(w)
    cx = w / 2.0
    cy = h / 2.0

    # Cumulative rotations: R_global[i] = rotation from world (frame 0) to camera i
    # So ray in camera i: ray_world = R_global[i].T @ ray_cam
    R_global = [np.eye(3, dtype=np.float64)]
    for i in range(n - 1):
        R, _, pts1, pts2 = engine.estimate_camera_pose(keyframes[i], keyframes[i + 1])
        if pts1 is None or len(pts1) < 8:
            # Fallback: assume identity (no rotation) for this pair
            R_next = R_global[-1].copy()
        else:
            # R from frame i to frame i+1; cumulative: from 0 to i+1 is R @ R_global[i]
            R_next = R.astype(np.float64) @ R_global[-1]
        R_global.append(R_next)

    # Precompute ray grid for image size
    rays_cam = _camera_rays_grid(h, w, fx, fy, cx, cy)  # (H*W, 3)

    # Equirectangular canvas: accumulate color and count for averaging
    canvas = np.zeros((panorama_height, panorama_width, 3), dtype=np.float64)
    count = np.zeros((panorama_height, panorama_width), dtype=np.float32)

    for idx, img in enumerate(keyframes):
        R_world_to_cam = R_global[idx].T
        rays_world = (R_world_to_cam.T @ rays_cam.T).T  # (H*W, 3)
        pixels = _rays_to_equirect_pixels(rays_world, panorama_width, panorama_height)  # (H*W, 2)
        ix = (np.round(pixels[:, 0]).astype(int)) % panorama_width
        iy = np.round(pixels[:, 1]).astype(int)
        valid = (iy >= 0) & (iy < panorama_height)
        ix, iy = ix[valid], iy[valid]
        colors = img.reshape(-1, 3)[valid].astype(np.float64)
        np.add.at(canvas, (iy, ix), colors)
        np.add.at(count, (iy, ix), 1.0)

    # Average and convert to uint8
    mask = count > 0
    result = np.zeros((panorama_height, panorama_width, 3), dtype=np.uint8)
    result[mask] = (canvas[mask] / count[mask, np.newaxis]).clip(0, 255).astype(np.uint8)
    return result
