#!/usr/bin/env python3
"""Headless Blender script: build SmartAI chassis variants and export GLB.

Dimensions align with config/robot_config.yaml (30x40 cm body, 250 mm wheel_distance).
Drive layout: 2 rear driven wheels (L/R) + 1 front-centre castor.
Units: millimeters. glTF export: Y-up.

Usage:
    python generate_variants.py          # launches Blender if in PATH
    blender --background --python generate_variants.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXPORTS_DIR = os.path.join(SCRIPT_DIR, "exports")

# robot_config.yaml robot section (cm -> mm)
ROBOT_CONFIG = {
    "body_w": 300,
    "body_l": 400,
    "wheel_d": 65,
    "wheel_w": 20,
    "wheel_distance": 250,
    "drive_axle_y": -135,
    "castor_y": 150,
    "castor_d": 40,
    "castor_w": 14,
}

VARIANTS = {
    "variant-a": {
        "label": "Compact Home",
        "body_w": ROBOT_CONFIG["body_w"],
        "body_l": ROBOT_CONFIG["body_l"],
        "body_h": 120,
        "wheel_d": 65,
        "wheel_w": 20,
        "wheel_distance": ROBOT_CONFIG["wheel_distance"],
        "drive_axle_y": ROBOT_CONFIG["drive_axle_y"],
        "castor_y": ROBOT_CONFIG["castor_y"],
        "castor_d": 40,
        "castor_w": 14,
        "mast_h": 40,
        "mast_d": 22,
        "mast_y_offset": -155,
        "deck_style": "rounded",
        "fillet": 12,
    },
    "variant-b": {
        "label": "Tall Navigator",
        "body_w": ROBOT_CONFIG["body_w"],
        "body_l": ROBOT_CONFIG["body_l"],
        "body_h": 100,
        "wheel_d": 70,
        "wheel_w": 22,
        "wheel_distance": 250,
        "drive_axle_y": -135,
        "castor_y": 150,
        "castor_d": 42,
        "castor_w": 14,
        "mast_h": 180,
        "mast_d": 35,
        "mast_y_offset": -100,
        "deck_style": "box",
        "wall": 10,
    },
    "variant-c": {
        "label": "Wide Stable",
        "body_w": 360,
        "body_l": 420,
        "body_h": 90,
        "wheel_d": 80,
        "wheel_w": 25,
        "wheel_distance": 280,
        "drive_axle_y": -145,
        "castor_y": 160,
        "castor_d": 45,
        "castor_w": 16,
        "mast_h": 0,
        "mast_d": 0,
        "mast_y_offset": 0,
        "deck_style": "wide",
        "corner_r": 22,
        "wall": 15,
    },
}


def find_blender() -> str | None:
    return shutil.which("blender")


def launch_blender() -> int:
    blender = find_blender()
    if not blender:
        print(
            "ERROR: Blender not found in PATH.\n"
            "  Install Blender (https://www.blender.org/download/) and add it to PATH,\n"
            "  or run directly:\n"
            "    blender --background --python generate_variants.py"
        )
        return 1

    cmd = [blender, "--background", "--python", os.path.abspath(__file__)]
    print(f"Launching: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=SCRIPT_DIR)
    return result.returncode


def _clear_scene(bpy) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)


def _setup_scene_units(bpy) -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 0.001  # 1 BU = 1 mm


def _make_material(bpy, name: str, rgba: tuple[float, float, float, float]):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def _assign_material(obj, mat) -> None:
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def _add_box(bpy, name, size, location, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        _assign_material(obj, mat)
    return obj


def _add_cylinder(bpy, name, radius, depth, location, rotation=(0, 0, 0), mat=None):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location, rotation=rotation
    )
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        _assign_material(obj, mat)
    return obj


def _add_wheel(bpy, x, y, wheel_d, wheel_w, mat):
    z = wheel_d / 2
    return _add_cylinder(
        bpy,
        f"wheel_{x}_{y}",
        wheel_d / 2,
        wheel_w,
        (x, y, z),
        rotation=(1.5708, 0, 0),
        mat=mat,
    )


def _deck_bottom_z(wheel_d: float) -> float:
    return wheel_d


def _build_deck(bpy, cfg, z0, mats):
    bw, bl, bh = cfg["body_w"], cfg["body_l"], cfg["body_h"]
    style = cfg["deck_style"]
    z_center = z0 + bh / 2

    if style == "rounded":
        fillet = cfg.get("fillet", 12)
        inner = (
            max(bw - 2 * fillet, 10),
            max(bl - 2 * fillet, 10),
            max(bh - 2 * fillet, 10),
        )
        _add_box(bpy, "deck_core", inner, (0, 0, z_center), mats["body"])
        for sx, sy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            ox = sx * (bw / 2 - fillet)
            oy = sy * (bl / 2 - fillet)
            _add_cylinder(
                bpy, f"deck_corner_{sx}_{sy}", fillet, bh, (ox, oy, z_center), mat=mats["body"]
            )
        _add_box(bpy, "deck_edge_x", (bw - 2 * fillet, inner[1], bh), (0, 0, z_center), mats["body"])
        _add_box(bpy, "deck_edge_y", (inner[0], bl - 2 * fillet, bh), (0, 0, z_center), mats["body"])
    else:
        _add_box(bpy, "deck_platform", (bw, bl, bh), (0, 0, z_center), mats["body"])


def _build_variant(bpy, variant_id: str, cfg: dict) -> None:
    _clear_scene(bpy)
    _setup_scene_units(bpy)

    mats = {
        "body": _make_material(bpy, "Body", (0.22, 0.24, 0.28, 1.0)),
        "wheel": _make_material(bpy, "Wheel", (0.12, 0.12, 0.12, 1.0)),
        "sensor": _make_material(bpy, "Sensor", (0.25, 0.45, 0.72, 1.0)),
        "mast": _make_material(bpy, "Mast", (0.35, 0.35, 0.38, 1.0)),
        "bumper": _make_material(bpy, "Bumper", (0.7, 0.1, 0.12, 1.0)),
        "accent": _make_material(bpy, "Accent", (0.18, 0.18, 0.2, 1.0)),
    }

    wheel_d = cfg["wheel_d"]
    z0 = _deck_bottom_z(wheel_d)
    z_top = z0 + cfg["body_h"]

    _build_deck(bpy, cfg, z0, mats)

    for x in (-cfg["wheel_distance"] / 2, cfg["wheel_distance"] / 2):
        _add_wheel(bpy, x, cfg["drive_axle_y"], wheel_d, cfg["wheel_w"], mats["wheel"])
        _add_box(
            bpy,
            f"motor_{x}",
            (25, 12, 8),
            (x, cfg["drive_axle_y"], wheel_d / 2 + 4),
            mats["accent"],
        )

    _add_wheel(
        bpy,
        0,
        cfg["castor_y"],
        cfg["castor_d"],
        cfg["castor_w"],
        mats["wheel"],
    )

    # HC-SR04 triplet (front +Y, left -X, right +X)
    us_z = z_top - 4
    us_positions = [
        (0, cfg["body_l"] / 2 - 28, us_z, 0),
        (-cfg["body_w"] / 2 + 28, 0, us_z, 1.5708),
        (cfg["body_w"] / 2 - 28, 0, us_z, -1.5708),
    ]
    for i, (ux, uy, uz, rot_z) in enumerate(us_positions):
        _add_box(bpy, f"ultrasonic_{i}", (45, 16, 20), (ux, uy, uz), mats["sensor"])

    # Bumper lip at front
    _add_box(
        bpy,
        "bumper_lip",
        (cfg["body_w"] - 40, 4, 8),
        (0, cfg["body_l"] / 2 - 2, z0 + 4),
        mats["bumper"],
    )

    # Pi 5 bay cutout visual (green slab)
    _add_box(bpy, "pi5_stack", (85, 56, 25), (0, 20, z_top + 12), mats["accent"])

    if cfg["mast_h"] > 0:
        my = cfg["mast_y_offset"]
        _add_cylinder(
            bpy,
            "mast",
            cfg["mast_d"] / 2,
            cfg["mast_h"],
            (0, my, z_top + cfg["mast_h"] / 2),
            mat=mats["mast"],
        )
        if variant_id == "variant-b":
            _add_cylinder(
                bpy,
                "lidar",
                35,
                30,
                (0, my, z_top + cfg["mast_h"] + 15),
                mat=mats["sensor"],
            )

    if variant_id == "variant-c":
        _add_box(
            bpy,
            "battery_tray",
            (140, 80, 24),
            (0, cfg["body_l"] / 2 - 50, z_top + 12),
            mats["accent"],
        )

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.join()
    root = bpy.context.active_object
    root.name = variant_id


def _export_glb(bpy, variant_id: str) -> str:
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    out_path = os.path.join(EXPORTS_DIR, f"{variant_id}.glb")
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=False,
        export_yup=True,
        export_apply=True,
    )
    return out_path


def build_all_variants() -> int:
    import bpy

    print("SmartAI chassis GLB export (mm units, Y-up glTF)")
    print(f"Config: body {ROBOT_CONFIG['body_w']}x{ROBOT_CONFIG['body_l']} mm, "
          f"wheel_distance {ROBOT_CONFIG['wheel_distance']} mm")
    print(f"Output: {EXPORTS_DIR}\n")

    for variant_id, cfg in VARIANTS.items():
        print(f"Building {variant_id} ({cfg['label']})...")
        _build_variant(bpy, variant_id, cfg)
        path = _export_glb(bpy, variant_id)
        print(f"  -> {path}")

    print(f"\nDone. {len(VARIANTS)} GLB files exported.")
    return 0


def main() -> int:
    try:
        import bpy  # noqa: F401
    except ImportError:
        return launch_blender()
    return build_all_variants()


if __name__ == "__main__":
    sys.exit(main())
