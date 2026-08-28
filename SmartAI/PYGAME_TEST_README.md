# SmartAI Test Visualization Guide

## Backends (test.py)

| Backend | Command | Best for |
|---------|---------|----------|
| **enhanced** (default) | `python test.py --backend enhanced` | Demos — split map + HUD panel |
| **3d** | `python test.py --backend 3d` | Home floor walkthrough (OpenGL) |
| **pygame** | `python test.py --backend pygame` | Lightweight 2D |
| **matplotlib** | `python test.py --backend matplotlib` | Debug plots, analysis |

Optional live dashboard: `python test.py --dashboard` (Dear PyGui side window)

**Important:** `--mode 1` shows the window. Add `--headless` only if you want no UI.

```bash
python test.py --backend enhanced --mode 1          # demo + window
python test.py --backend enhanced --mode 1 --headless  # CI, no window
```

## Enhanced 2D HUD

- Left: map, path, LIDAR, robot (front caster shown as white dot)
- Right panel: nav state, sensors, rear motors, RobotMind, camera thumb
- Keys: **Space** pause · **R** reset demo · **Esc** quit

## 3D home view

Uses `src/simulation/world_3d.py` — walls, furniture, robot in a house layout.
Drag mouse to orbit camera. 2D nav coords map to 3D floor (x, z).

## Scenario config

`scenarios/demo_home.yaml` — IR-SIM-style layout reference for future adapter.

## Research-backed picks (2025–2026)

- **[IR-SIM](https://github.com/hanruihua/ir-sim)** — YAML scenarios, keyboard/mouse, collision; good 2D nav reference
- **[PyRoboSim](https://github.com/sea-bass/pyrobosim)** — ROS2 2.5D mobile robot sim
- **Dear PyGui** — GPU dashboard for live telemetry (used in `--dashboard`)
- **[Genesis](https://github.com/Genesis-Embodied-AI/Genesis)** — future upgrade for photoreal 3D + physics (heavy)

## Install

```bash
pip install pygame matplotlib opencv-python dearpygui pyopengl
```

## Path refinement (smoother over time)

The robot now **learns successful trips** and reuses them:

```bash
python test.py --backend enhanced --mode 16
```

- Same start→goal, several runs
- Amber = older plans, green = current
- Banner: waypoints, length, turns
- Menu option **16** also works
