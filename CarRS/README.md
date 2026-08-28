# Car Rental Recommendation System

Personalized car rental recommendations from your historical trip CSV. Supports Singapore car-sharing providers and Malaysia providers (SoCar, **Traditional Rental**).

## Quick start (Windows)

```bat
CarRentalApp.bat
```

Or manually:

```bash
pip install -r requirements.txt
python car_rental_recommender_gui.py
```

## Headless CLI (containers / agents)

```bash
python run_recommendations.py --distance 50 --duration 3
python run_recommendations.py --distance 80 --duration 24 --region Malaysia --json
```

## Project layout

| Path | Purpose |
|------|---------|
| `car_rental_recommender_gui.py` | Main tkinter GUI |
| `car_rental_recommender_core.py` | Core logic (pricing, ML, cleaning) |
| `run_recommendations.py` | Headless recommendation CLI |
| `run_cleaning_pipeline.py` | Standalone CSV cleaning |
| `22 - Sheet1.csv` | Default rental history data |
| `pricing_config.json` | Provider pricing (incl. Traditional Rental) |
| `components/panels/` | Records, recommendations, settings tab UI |
| `components/rental_dates.py` | Multi-day start/end date helpers |
| `components/collection_location.py` | Pickup location + distance rating |
| `components/getgo_fleet_sync.py` | GetGo fleet catalog web sync |
| `getgo_fleet_cache.json` | Cached GetGo models (auto-refreshed) |
| `requirements.txt` | Local Python deps (Windows-friendly pins) |
| `requirements-container.txt` | Python 3.11+ pins for Docker |
| `openclaw/skills/car-rental-recommender/` | OpenClaw agent skill |
| `docs/` | Feature docs (ML, Ollama, Docker) |
| `tests/` | Automated pytest suite |
| `tests/manual/` | Optional demo scripts (pygame, preferences) |
| `scripts/` | CLI helpers (`evaluate_ml.py`, etc.) |
| `data/` | Local spreadsheets (gitignored) |

Feature docs: [docs/ML_RECOMMENDATIONS_README.md](docs/ML_RECOMMENDATIONS_README.md), [docs/OLLAMA_INTEGRATION_README.md](docs/OLLAMA_INTEGRATION_README.md).

## Traditional Rental (Malaysia)

Category **Traditional Rental** uses a flat fee model — **no mileage charge**:

- Rental duration/cost (e.g. RM300 weekend)
- Malaysia usage add-on (optional)
- Deposit
- Fuel topped up

Total = duration/cost + Malaysia add-on + deposit + fuel.

Configure defaults in **Calculator → Pricing Configuration → Traditional Rental**, or enter values per record in **Records Management** when provider is Traditional Rental.

Legacy CSV rows labeled `NormalRental` are normalized to Traditional Rental on load.

## Android (Samsung Galaxy S23 Ultra / Termux)

The phone install uses the **headless CLI** only (no tkinter GUI). See [android/INSTALL.md](android/INSTALL.md).

```powershell
# On Windows PC — build transfer zip
powershell -ExecutionPolicy Bypass -File android\package.ps1
```

On the phone in Termux: unzip → `bash android/install.sh` → `carrs recommend --distance 50 --duration 3`.

## Docker / OpenClaw

The container runs the **headless CLI** only (no tkinter display). See [docs/DOCKER.md](docs/DOCKER.md).

```bash
docker compose build
docker compose run --rm carrs recommend --distance 50 --duration 3 --json
```

Mount the OpenClaw skill:

```yaml
volumes:
  - /path/to/CarRS/openclaw/skills/car-rental-recommender:/home/node/.openclaw/workspace/skills/car-rental-recommender:ro
```

## Data cleaning pipeline

```bash
python run_cleaning_pipeline.py "22 - Sheet1.csv" --out cleaned.csv
```

Loading CSV in the GUI runs the same pipeline automatically (schema check, normalize, dedupe, quality report).

## Development / tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python scripts/evaluate_ml.py          # human-readable ML learning report
python scripts/evaluate_ml.py --json   # machine-readable
```

## Troubleshooting

1. Place your rental CSV in the CarRS folder (default name `22 - Sheet1.csv`) or use **Settings** to pick another file. This file is listed in `.gitignore` so personal trip data stays local; copy column headers from an existing export or from the app after adding one record.
2. Python 3.8+ for GUI; Python 3.11+ recommended for Docker.
3. Ollama features are optional (off by default) — recommendations use CSV history, `pricing_config.json`, and local ML when enabled.
