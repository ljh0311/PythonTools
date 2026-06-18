# CarRS — Docker & OpenClaw

**Target:** Linux container (Python 3.11), headless CLI. GUI requires a local display and is not included in the image.

## Build and run

From the `CarRS/` directory:

```bash
docker compose build
docker compose run --rm carrs recommend --distance 50 --duration 3
docker compose run --rm carrs recommend --distance 80 --duration 24 --region Malaysia --json
docker compose run --rm carrs clean "22 - Sheet1.csv" --out /app/data/cleaned.csv
```

Entrypoint commands:

| Command | Example |
|---------|---------|
| `recommend` | `recommend --distance 50 --duration 3 --region Singapore` |
| `clean` | `clean "22 - Sheet1.csv" --out cleaned.csv` |
| `shell` | Interactive shell inside container |

## OpenClaw integration

### 1. Start CarRS container

```bash
docker compose up -d --build
```

This creates network `carrs-net` (compose project default).

### 2. Connect OpenClaw to the same network

```bash
docker network connect carrs_carrs-net YOUR_OPENCLAW_CONTAINER
```

Or add to OpenClaw `docker-compose.yml`:

```yaml
services:
  openclaw:
    networks:
      - carrs-net

networks:
  carrs-net:
    external: true
    name: carrs_carrs-net
```

### 3. Mount the skill

```yaml
volumes:
  - /absolute/path/to/CarRS/openclaw/skills/car-rental-recommender:/home/node/.openclaw/workspace/skills/car-rental-recommender:ro
```

### 4. Configure `openclaw.json`

See `openclaw/openclaw.docker.example.json5`:

```json5
{
  skills: {
    entries: {
      "car-rental-recommender": {
        enabled: true,
        env: { CARRS_WORKDIR: "/absolute/path/to/CarRS" },
      },
    },
  },
}
```

When the agent runs **inside** the CarRS container, set `CARRS_WORKDIR=/app`.

Use the skill CLI:

```bash
python3 scripts/carrs.py recommend --distance 50 --duration 3 --json
python3 scripts/carrs.py providers --region Malaysia
```

## Volumes

- `22 - Sheet1.csv` — mounted read-only; replace with your data path
- `pricing_config.json` — Traditional Rental defaults
- `carrs-data` — optional writable output for cleaned CSVs

## GUI limitation

`car_rental_recommender_gui.py` needs X11/Wayland. For Docker desktop with X11 forwarding (advanced):

```bash
docker run -e DISPLAY=$DISPLAY -v /tmp/.X11-unix:/tmp/.X11-unix ...
```

Recommended: run the GUI on the host; use Docker for headless recommendations only.

## Verify

```bash
docker compose run --rm carrs recommend --distance 10 --duration 2 --top 1
echo $?   # expect 0
```
