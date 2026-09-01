# SmartAI development log

## 2026-09-01 — Motor trim, UI/UX, test infrastructure

**Progress**
- Motor trim learning + persistence (`MotorTrimLearner`, JSON config, API).
- Desktop Settings sliders + auto-calibrate on startup toggle.
- Web dashboard: motor trim controls, responsive layout, dark-mode contrast fixes.
- `test.py`: mocks in `tests/fixtures/`, `--headless --mode N`, modes 6–8 implemented.
- Pytest scenario smoke tests (navigation, sensor fusion, motor trim).

**Remaining**
- Real-hardware auto-learn needs encoders or heading sensor.
- `stuck_locations.json` is runtime data — do not commit large learning dumps.
- Pre-existing sensor API shape (`ultrasonic` key) still breaks some GUI collector paths on sim.

**Verification**
```bash
cd SmartAI
python -m pytest tests/test_motor_trim_learner.py tests/test_navigation_scenarios.py tests/test_sensor_fusion.py -q
python test.py --headless --mode 7
python main.py
```
