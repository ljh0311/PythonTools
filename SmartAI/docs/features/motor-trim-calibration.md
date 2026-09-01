# Motor trim calibration

## Purpose

Correct left/right motor imbalance so the robot drives straight when commanded.

## Behavior

- Trim multipliers (`left_trim`, `right_trim`, range 0.5–1.5) apply on every `set_speeds()` call.
- Values persist to `config/motor_calibration.json`.
- `MotorTrimLearner` iteratively measures speed imbalance in simulation and adjusts trim.
- Startup auto-calibrate runs when `auto_calibrate_on_startup` is true (JSON or YAML).

## Usage

| Surface | Action |
|---------|--------|
| Desktop GUI | Settings → sliders, Save, Auto-calibrate, startup toggle |
| Web UI | Manual Control → Motor Trim section |
| API | `GET/POST /api/motor_calibration`, `POST /api/motor_calibration/auto` |
| CLI test | `python test.py --headless --mode 7` |

## Configuration

`config/robot_config.yaml` → `motor_calibration` section.  
`config/motor_calibration.json` → persisted trim + startup flag.

## Verification

```bash
python test.py --headless --mode 7
curl http://127.0.0.1:5000/api/motor_calibration
```
