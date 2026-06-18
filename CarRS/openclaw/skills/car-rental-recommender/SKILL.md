---
name: car-rental-recommender
description: Get car rental recommendations from historical CSV data (headless CLI). Supports Singapore and Malaysia providers including Traditional Rental.
metadata:
  {"openclaw":{"requires":{"env":["CARRS_WORKDIR"],"bins":["python3"]},"primaryEnv":"CARRS_WORKDIR"}}
---

# Car Rental Recommender (CarRS)

Use this skill when the user asks for car rental recommendations, cost comparisons, or trip planning based on their rental history CSV.

## Configuration

| Variable | Example | Purpose |
|----------|---------|---------|
| `CARRS_WORKDIR` | `/app` or host path to `CarRS/` | Directory containing CSV and scripts |

Docker: mount the CarRS folder or use the `carrs-recommender` container on `openclaw-net`.

## Helper script

```bash
python3 {baseDir}/scripts/carrs.py recommend --distance 50 --duration 3
python3 {baseDir}/scripts/carrs.py recommend --distance 80 --duration 24 --region Malaysia --json
python3 {baseDir}/scripts/carrs.py clean "22 - Sheet1.csv" --out /tmp/cleaned.csv
python3 {baseDir}/scripts/carrs.py providers --region Malaysia
```

## Traditional Rental (Malaysia)

Provider **Traditional Rental** uses flat pricing: duration/cost + Malaysia usage add-on + deposit + fuel topped up. **No mileage charge.** Configure defaults in `pricing_config.json`.

## GUI note

The tkinter GUI (`car_rental_recommender_gui.py`) requires a display. In Docker/OpenClaw use the headless CLI only.
