"""Proximity context builders and offline rule decisions for RobotMind.

Not a standalone reasoner — helpers used by RobotMind / TaskBoss.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# COCO / EfficientDet furniture-like classes used for proximity typing
FURNITURE_CLASSES = frozenset({
    "chair", "couch", "sofa", "bed", "dining table", "table",
    "toilet", "tv", "laptop", "book", "bottle", "cup",
    "potted plant", "vase", "refrigerator", "microwave", "oven",
    "toaster", "sink", "clock", "bench", "backpack", "handbag",
    "suitcase", "umbrella", "keyboard", "mouse", "remote",
    "cell phone", "microwave oven",
})

PERSON_CLASSES = frozenset({"person"})
WALL_HINTS = frozenset({"wall"})


def sensor_cm_to_m(cm: float) -> float:
    """SensorData / SensorManager distances are centimeters."""
    return float(cm) / 100.0


def classify_label(class_name: str) -> str:
    name = (class_name or "unknown").lower().strip()
    if name in PERSON_CLASSES:
        return "person"
    if name in WALL_HINTS:
        return "wall"
    if name in FURNITURE_CLASSES:
        return "furniture"
    if name in ("motion", "obstacle", "unknown", ""):
        return "unknown"
    # Remaining COCO dynamics (car, dog, …) → unknown for indoor proximity
    return "unknown"


def count_vision_labels(
    obstacles: Optional[List[Any]] = None,
    scene: Optional[Dict[str, Any]] = None,
) -> Dict[str, int]:
    """Tally person / wall / furniture / unknown from detections + scene walls."""
    counts = {"person": 0, "wall": 0, "furniture": 0, "unknown": 0}
    for o in obstacles or []:
        name = getattr(o, "class_name", None) or (o.get("class_name") if isinstance(o, dict) else "")
        key = classify_label(str(name))
        counts[key] = counts.get(key, 0) + 1

    if scene:
        for region in scene.get("regions", []) or []:
            et = region
            if hasattr(region, "element_type"):
                et = region.element_type
                et = getattr(et, "value", et)
            elif isinstance(region, dict):
                et = region.get("element_type") or region.get("type")
                if hasattr(et, "value"):
                    et = et.value
            if str(et).lower() == "wall":
                counts["wall"] += 1
    return counts


def closest_side(front_m: float, left_m: float, right_m: float) -> Tuple[str, float]:
    sides = (("front", front_m), ("left", left_m), ("right", right_m))
    side, dist = min(sides, key=lambda x: x[1] if x[1] > 0 else float("inf"))
    return side, dist


def dominant_object_type(labels: Dict[str, int]) -> str:
    """Prefer person > wall > furniture > unknown when counts present."""
    for key in ("person", "wall", "furniture", "unknown"):
        if labels.get(key, 0) > 0:
            return key
    return "unknown"


def build_proximity_context(
    front_m: float,
    left_m: float,
    right_m: float,
    *,
    vision_labels: Optional[Dict[str, int]] = None,
    nav_state: Optional[str] = None,
    current_task: Optional[str] = None,
    safety_cm: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    labels = vision_labels or {"person": 0, "wall": 0, "furniture": 0, "unknown": 0}
    side, dist_m = closest_side(front_m, left_m, right_m)
    obj = dominant_object_type(labels)
    safety = safety_cm or {"critical": 15.0, "warning": 35.0, "comfortable": 50.0}
    return {
        "front_m": front_m,
        "left_m": left_m,
        "right_m": right_m,
        "vision_labels": labels,
        "nav_state": nav_state,
        "current_task": current_task,
        "closest_side": side,
        "closest_m": dist_m,
        "object_type": obj,
        "safety_m": {k: v / 100.0 for k, v in safety.items()},
    }


def format_proximity_for_llm(ctx: Dict[str, Any]) -> str:
    labels = ctx.get("vision_labels") or {}
    return (
        "Proximity Context:\n"
        f"  Front: {ctx.get('front_m', 0):.2f} m | Left: {ctx.get('left_m', 0):.2f} m | "
        f"Right: {ctx.get('right_m', 0):.2f} m\n"
        f"  Closest: {ctx.get('closest_side', 'front')} @ {ctx.get('closest_m', 0):.2f} m\n"
        f"  Vision labels: person={labels.get('person', 0)}, wall={labels.get('wall', 0)}, "
        f"furniture={labels.get('furniture', 0)}, unknown={labels.get('unknown', 0)}\n"
        f"  Inferred object: {ctx.get('object_type', 'unknown')}\n"
        f"  Nav state: {ctx.get('nav_state')} | Task: {ctx.get('current_task')}\n"
        "Respond with JSON tool one of: stop | scan_surroundings | try_alternate_route | navigate_to\n"
        "Include human reason naming object type + side + approximate distance (e.g. "
        "'wall front ~0.3m — reroute').\n"
        'Example: {"tool": "stop", "args": {}, "reason": "person front ~0.25m — stopping"}'
    )


def offset_navigate_args(ctx: Dict[str, Any], position: Optional[Any] = None) -> Dict[str, float]:
    """Lateral offset (cm) toward the clearer side for navigate_to."""
    left_m = float(ctx.get("left_m") or 0)
    right_m = float(ctx.get("right_m") or 0)
    offset_cm = 80.0
    # Prefer side with more clearance
    if left_m >= right_m:
        dx, dy = -offset_cm, offset_cm * 0.5
    else:
        dx, dy = offset_cm, offset_cm * 0.5
    x = getattr(position, "x", 0.0) if position is not None else 0.0
    y = getattr(position, "y", 0.0) if position is not None else 0.0
    return {"x": float(x) + dx, "y": float(y) + dy}


def proximity_rule_decide(ctx: Dict[str, Any], position: Optional[Any] = None) -> Dict[str, Any]:
    """Offline heuristics: person→stop, wall→reroute, furniture→slow/reroute, unknown→stop."""
    obj = ctx.get("object_type") or dominant_object_type(ctx.get("vision_labels") or {})
    side = ctx.get("closest_side") or "front"
    dist_m = float(ctx.get("closest_m") or ctx.get("front_m") or 0.0)
    safety = ctx.get("safety_m") or {"critical": 0.15, "warning": 0.35, "comfortable": 0.50}
    critical = float(safety.get("critical", 0.15))
    warning = float(safety.get("warning", 0.35))
    front_m = float(ctx.get("front_m") or dist_m)

    reason_base = f"{obj} {side} ~{dist_m:.2f}m"

    # Very close / bump risk — always stop
    if front_m < critical or dist_m < critical:
        return {
            "tool": "stop",
            "args": {},
            "reason": f"{reason_base} — critical proximity, stopping",
            "source": "proximity_rule_fallback",
        }

    if obj == "person":
        return {
            "tool": "stop",
            "args": {},
            "reason": f"{reason_base} — person nearby, stopping",
            "source": "proximity_rule_fallback",
        }

    if obj == "wall":
        return {
            "tool": "try_alternate_route",
            "args": {},
            "reason": f"{reason_base} — wall ahead, trying alternate route",
            "source": "proximity_rule_fallback",
        }

    if obj == "furniture":
        if front_m < warning:
            return {
                "tool": "try_alternate_route",
                "args": {},
                "reason": f"{reason_base} — furniture close, rerouting",
                "source": "proximity_rule_fallback",
            }
        args = offset_navigate_args(ctx, position)
        return {
            "tool": "navigate_to",
            "args": args,
            "reason": f"{reason_base} — furniture, going around",
            "source": "proximity_rule_fallback",
        }

    # unknown close → stop; slightly farther → scan
    if front_m < warning or dist_m < warning:
        return {
            "tool": "stop",
            "args": {},
            "reason": f"{reason_base} — unknown close obstacle, stopping",
            "source": "proximity_rule_fallback",
        }
    return {
        "tool": "scan_surroundings",
        "args": {},
        "reason": f"{reason_base} — unknown object, scanning",
        "source": "proximity_rule_fallback",
    }
