# CarRS Web (local)

Phone/laptop UI on your Wi‑Fi. Data stays on this PC.

## Start

```bat
CarRSWeb.bat
```

Or:

```bash
pip install -r requirements-web.txt
python scripts/run_web.py
```

Open:

- This PC: `http://127.0.0.1:8765`
- Phone: `http://YOUR-PC-IP:8765` (printed in the terminal)

Same Wi‑Fi. Windows Firewall may ask once — allow private networks.

## Needs

- `22 - Sheet1.csv` in the CarRS folder (or set `CARRS_CSV`)
- Python deps in `requirements.txt` + `requirements-web.txt`

## Assets

| File | Use |
|------|-----|
| `web/static/assets/carrs-mark.svg` | Favicon / brand mark |
| `web/static/assets/carrs-hero.svg` | Hero road scene (640×360) |
