# CarRS development log

## 2026-08-28 — GUI upgrade, fleet sync, tests, repo tidy

### Progress

- Split monolithic GUI into `components/panels/` (records, recommendations, settings).
- Form-first recommendations: trip distance/duration + **Get Recommendations**; chat/Ollama under collapsible Advanced.
- Records: multi-day start/end dates, collection location text + 0–5 distance rating.
- Vision import: receipt/screenshot → local Ollama vision → pre-fill record form.
- GetGo fleet sync: scrape/cache ~82 models; Settings refresh + monthly auto-update (720 h).
- ML evaluation harness (`tests/ml_evaluation.py`, `scripts/evaluate_ml.py`).
- Automated pytest suite (29 tests); manual demos moved to `tests/manual/`.
- Docs consolidated under `docs/`; one-off dev scripts under `scripts/archive/`.
- Local/personal data removed from git tracking (`22 - Sheet1.csv`, `settings.json`, `*.xlsx`).

### Feature notes

| Feature | Behavior | Verify |
|---------|----------|--------|
| Recommendations | ML on by default; Ollama optional in Advanced | Launch GUI → enter km/hours → Get Recommendations |
| Records | Start/end dates, pickup location + rating | Records tab → add/edit row |
| Vision import | Needs Ollama + `llama3.2-vision` | Records → Import from image |
| GetGo fleet | Cache + optional live refresh (Firecrawl or requests) | Settings → Refresh GetGo fleet |
| ML eval | Compare predictions vs historical medians | `python scripts/evaluate_ml.py` |
| Privacy | CSV/settings/xlsx stay local | Confirm not in `git ls-files` after commit |

### 2026-09-03 — Multi-pass ML training

- Added `scripts/train_ml.py` + `components/ml_trainer.py` (3 passes: baseline → hyperparams → recalibrate).
- Saves local `ml_model_meta.json` + refreshed `ml_calibration.json`.
- `create_ml_recommendations` uses best params + calibration again.
- Run: `python scripts/train_ml.py --passes 3`

### 2026-09-02 — Live GetGo / Tribecar rate refresh

- Sources: [getgo.sg/rates](https://www.getgo.sg/rates), [tribecar.com/page/our-rates](https://www.tribecar.com/page/our-rates).
- GetGo petrol mileage **$0.39 → $0.44**/km; EV **$0.35 → $0.29**/km; Economy hour Normal **$5** (was flat $8); platform fee **$1.20**.
- Tribecar switched to **mileage** Economy **$0.43**/km + Off-Peak **$4.91**/hr (was fuel + $8.5/hr).
- Car Club aligned to Tribecar Standard **$0.43**/km + **$6.54**/hr.
- Hardcoded fallbacks in core/GUI updated to match.

### 2026-09-02 — Local web UI

- Added FastAPI app under `web/` + `CarRSWeb.bat` (binds `0.0.0.0:8765`).
- Phone/laptop on same Wi‑Fi; brand hero SVG assets in `web/static/assets/`.
- Docs: `docs/features/web-local.md`. Verify: `pip install -r requirements-web.txt` then `python -m pytest tests/test_web_api.py -q`.

### Known gaps

- Quick-add shortcut UI not shipped (parser/settings key reserved in `.gitignore`).
- GetGo live fetch may hit Cloudflare on `home.getgo.sg`; `www.getgo.sg` + bundled cache used as fallback.

### Test

```bash
cd CarRS
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
```
