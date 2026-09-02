# SmartAI 3D design variants

Parametric OpenSCAD models for three chassis concepts. Dimensions align with `config/robot_config.yaml` (30×40 cm body, differential drive).

## Variants

| File | Concept | Best for |
|------|---------|----------|
| `variant-a-compact-home.scad` | Rounded low profile | Home assistant, tight spaces |
| `variant-b-tall-navigator.scad` | Mast + LiDAR puck | Indoor nav, camera/LiDAR |
| `variant-c-wide-stable.scad` | Wide wheelbase | Motor trim tuning, heavy battery |

## Export

1. Install [OpenSCAD](https://openscad.org/)
2. Open a `.scad` file
3. **File → Export → Export as STL** (or use `openscad -o out.stl variant-a-compact-home.scad`)

## Import settings

| Target | Scale | Orientation |
|--------|-------|-------------|
| Blender | 1 unit = 1 mm | Y-up after import |
| Unity / glTF | 0.001 scale if using meters | Z-up |
| 3D print | STL as-is | Bed = XY, height = Z |

## Pivots

- Origin at body center, Z = floor
- Wheel centers on wheelbase × track grid

## Acceptance

- [ ] Manifold mesh (OpenSCAD preview has no CSG errors)
- [ ] Wheelbase matches motor `wheel_base` (~250 mm in sim)
- [ ] Ultrasonic mounts face front/left/right per GPIO layout
