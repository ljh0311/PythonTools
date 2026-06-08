# Flightcomp Data Directory

This directory holds all application data. **JSON files are the source of truth** for training records and reference data.

## Layout

| Path | Purpose |
|------|---------|
| `airports/airport_info.json` | Airport layouts (runways, taxiways, gates, hotspots, procedures). Used by `models/airport_database.py`. |
| `scenarios/airport_scenarios.json` | Normal, weather, night, SID/STAR scenarios. |
| `scenarios/emergency_scenarios.json` | Emergency scenarios (engine, medical, fire, gear, weather). |
| `checklists/emergency_checklists.json` | Emergency checklists linked by `checklist_id` from emergency scenarios. |
| `training_records/` | Per-session (`session_<uuid>.json`) and per-pilot (`pilot_<id>.json`) progress. Used by `utils/progress_tracker.py` only. |

## Storage strategy

- **Training records**: Stored only as JSON under `training_records/`. The SQLite database (`database/schema.sql`, `database/database_manager.py`) is **deprecated** and not used by the application. Do not rely on `data/training.db`; it may be absent or outdated.

## Optional assets

- **Airport charts**: `airports/airport_info.json` may reference `chart_path` (e.g. `data/airports/airport_charts/wsss_chart.png`). Charts are optional; if the path is missing, the chart viewer skips display. Paths are relative to the project root.

## Data validation

Use **Tools → Validate data** in the application to run structural and optional AI-based validation on airports, scenarios, checklists, and training records.
