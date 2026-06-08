"""
Image-processing quality / performance profiles for SmartCam.

A profile is a small, immutable bundle of knobs that callers (GUI preview
loop, SmartCamera pipeline) can read without each having its own ad-hoc
constants. This keeps SmartCam tunable across Windows desktops, Linux,
and Raspberry Pi without a maze of conditionals.

Profiles do NOT perform detection or rendering themselves; they describe
HOW MUCH work the rest of the system should do.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class ProcessingProfile:
    """A processing-quality preset."""
    name: str
    description: str
    # Preview detection downscale target (width, height). Smaller = faster.
    detection_preview_size: Tuple[int, int]
    # 0 = process every preview frame, 1 = every 2nd, etc.
    preview_frame_skip: int
    # Whether to run object detection on the live preview (CPU-heavy).
    enable_object_in_preview: bool
    # Default enhancement when "auto" is selected by the user.
    default_enhancement_type: str
    # Soft cap on preview FPS used by the GUI when limiting frame rate.
    recommended_max_fps: int


QUALITY = ProcessingProfile(
    name="quality",
    description="Full AI on every frame; best for desktops with a GPU.",
    detection_preview_size=(960, 720),
    preview_frame_skip=0,
    enable_object_in_preview=True,
    default_enhancement_type="auto",
    recommended_max_fps=30,
)

BALANCED = ProcessingProfile(
    name="balanced",
    description="Smooth preview with detection on alternate frames.",
    detection_preview_size=(640, 480),
    preview_frame_skip=1,
    enable_object_in_preview=True,
    default_enhancement_type="auto",
    recommended_max_fps=30,
)

PERFORMANCE = ProcessingProfile(
    name="performance",
    description="Aggressive frame skipping for low-end laptops.",
    detection_preview_size=(480, 360),
    preview_frame_skip=2,
    enable_object_in_preview=False,
    default_enhancement_type="auto",
    recommended_max_fps=24,
)

RPI = ProcessingProfile(
    name="rpi",
    description="Raspberry Pi defaults: minimal AI, low resolution.",
    detection_preview_size=(320, 240),
    preview_frame_skip=3,
    enable_object_in_preview=False,
    default_enhancement_type="denoise",
    recommended_max_fps=15,
)


_PROFILES: Dict[str, ProcessingProfile] = {
    p.name: p for p in (QUALITY, BALANCED, PERFORMANCE, RPI)
}


def get_default_profile_name() -> str:
    """Auto-pick a profile based on the current host."""
    try:
        from camera_service import is_raspberry_pi
        if is_raspberry_pi():
            return RPI.name
    except Exception:
        pass
    return BALANCED.name


def get_profile(name: str) -> ProcessingProfile:
    """Return the named profile, falling back to the default for unknown names."""
    if not name or name == "auto":
        return _PROFILES[get_default_profile_name()]
    return _PROFILES.get(name, _PROFILES[get_default_profile_name()])


def list_profile_names() -> Tuple[str, ...]:
    """Return all known profile names."""
    return tuple(_PROFILES.keys())
