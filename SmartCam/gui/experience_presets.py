"""
Experience presets for SmartCam desktop GUI — fewer knobs for casual / trip use.

Each preset maps to the tk variables on SmartCameraGUI; apply_preset() only sets
values and relies on the GUI's existing _update_* hooks when a camera is active.
"""

from __future__ import annotations

from typing import Any, Dict, List

PresetDict = Dict[str, Any]

# Human-readable order shown in the combobox
PRESET_ORDER: List[str] = [
    "Trip (simple)",
    "Scenic (stills)",
    "Balanced",
    "Crowd-aware",
]

PRESETS: Dict[str, PresetDict] = {
    "Trip (simple)": {
        "summary": (
            "Manual-style driving: auto-capture off, fewer clouding features, "
            "face analysis off (less sensitive in public spaces). "
            "Motion + object still inform the preview if models are available."
        ),
        "auto_enhancement": True,
        "enhancement_type": "auto",
        "face_detection": False,
        "motion_detection": True,
        "object_detection": True,
        "auto_capture": False,
        "capture_cooldown": 12,
        "max_captures_per_minute": 6,
        "capture_sequence_count": 2,
        "save_detection_overlay": False,
        "debug_mode": False,
        "auto_tagging": False,
        "scene_classification": False,
        "anomaly_detection": False,
        "anomaly_sensitivity": 0.5,
        "baseline_frames": 40,
        "framing_assist": True,
        "framing_min_score": 0.40,
        "framing_gate": False,
    },
    "Scenic (stills)": {
        "summary": (
            "Still photography bias: no auto bursts, emphasis on enhancement and "
            "composition; scene tagging on for album sorting; motion-heavy alerts reduced."
        ),
        "auto_enhancement": True,
        "enhancement_type": "auto",
        "face_detection": True,
        "motion_detection": False,
        "object_detection": True,
        "auto_capture": False,
        "capture_cooldown": 8,
        "max_captures_per_minute": 8,
        "capture_sequence_count": 3,
        "save_detection_overlay": True,
        "debug_mode": False,
        "auto_tagging": True,
        "scene_classification": True,
        "anomaly_detection": False,
        "anomaly_sensitivity": 0.55,
        "baseline_frames": 30,
        "framing_assist": True,
        "framing_min_score": 0.38,
        "framing_gate": False,
    },
    "Balanced": {
        "summary": (
            "Default-style mix: auto-capture on with moderate limits, all detectors on, "
            "smart processing on — closest to the stock SmartCam experience."
        ),
        "auto_enhancement": True,
        "enhancement_type": "auto",
        "face_detection": True,
        "motion_detection": True,
        "object_detection": True,
        "auto_capture": True,
        "capture_cooldown": 5,
        "max_captures_per_minute": 12,
        "capture_sequence_count": 3,
        "save_detection_overlay": True,
        "debug_mode": False,
        "auto_tagging": True,
        "scene_classification": True,
        "anomaly_detection": True,
        "anomaly_sensitivity": 0.7,
        "baseline_frames": 30,
        "framing_assist": True,
        "framing_min_score": 0.40,
        "framing_gate": False,
    },
    "Crowd-aware": {
        "summary": (
            "Public spaces: face pipeline off, no auto-capture, no overlays on disk, "
            "metadata-heavy smart features off. You still get manual shutter / record "
            "and optional motion/object hints in preview only (no extra face crops saved)."
        ),
        "auto_enhancement": True,
        "enhancement_type": "auto",
        "face_detection": False,
        "motion_detection": True,
        "object_detection": False,
        "auto_capture": False,
        "capture_cooldown": 15,
        "max_captures_per_minute": 4,
        "capture_sequence_count": 2,
        "save_detection_overlay": False,
        "debug_mode": False,
        "auto_tagging": False,
        "scene_classification": False,
        "anomaly_detection": False,
        "anomaly_sensitivity": 0.5,
        "baseline_frames": 20,
        "framing_assist": False,
        "framing_min_score": 0.40,
        "framing_gate": False,
    },
}


def apply_preset(gui: Any, preset_name: str) -> str:
    """
    Apply a named preset to SmartCameraGUI variables.

    Returns the preset summary string (for status / dialogs).
    """
    preset = PRESETS[preset_name]

    gui.auto_enhancement_var.set(bool(preset["auto_enhancement"]))
    gui.enhancement_type_var.set(str(preset["enhancement_type"]))
    gui.face_detection_var.set(bool(preset["face_detection"]))
    gui.motion_detection_var.set(bool(preset["motion_detection"]))
    gui.object_detection_var.set(bool(preset["object_detection"]))

    gui.auto_capture_var.set(bool(preset["auto_capture"]))
    gui.capture_cooldown_var.set(int(preset["capture_cooldown"]))
    gui.max_captures_per_minute_var.set(int(preset["max_captures_per_minute"]))
    gui.capture_sequence_count_var.set(int(preset["capture_sequence_count"]))
    gui.save_detection_overlay_var.set(bool(preset["save_detection_overlay"]))
    gui.debug_mode_var.set(bool(preset["debug_mode"]))

    gui.auto_tagging_var.set(bool(preset["auto_tagging"]))
    gui.scene_classification_var.set(bool(preset["scene_classification"]))
    gui.anomaly_detection_var.set(bool(preset["anomaly_detection"]))
    gui.anomaly_sensitivity_var.set(float(preset["anomaly_sensitivity"]))
    gui.baseline_frames_var.set(int(preset["baseline_frames"]))

    gui.framing_assist_var.set(bool(preset["framing_assist"]))
    gui.framing_min_score_var.set(float(preset["framing_min_score"]))
    gui.framing_gate_var.set(bool(preset["framing_gate"]))

    return str(preset["summary"])


def privacy_and_storage_notice(output_dir_abs: str) -> str:
    """Static copy for in-app and README-aligned privacy summary."""
    return (
        "How SmartCam treats your data (desktop app)\n"
        "-------------------------------------------\n"
        f"- Saves folder (default relative to the app): {output_dir_abs}\n"
        "  Typical layout under that root: images/, videos/, events/, enhanced/\n"
        "- Processing is local on this PC unless you add your own cloud code.\n"
        "- When \"Save Detection Overlay\" is ON, stills may include drawn boxes "
        "(more identifiable than raw scenery). Turn it OFF in Trip / Crowd-aware presets.\n"
        "- Auto-capture can write images without a deliberate shutter press; use "
        "cooldown / max per minute, or disable auto-capture for strict control.\n"
        "- Face / object pipelines depend on installed AI packages; see README install tiers.\n"
        "\n"
        "This is not legal advice; obey local rules for recording in public and private spaces.\n"
    )
