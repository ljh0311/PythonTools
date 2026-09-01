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

### Known gaps

- Quick-add shortcut UI not shipped (parser/settings key reserved in `.gitignore`).
- GetGo live fetch may hit Cloudflare on `home.getgo.sg`; `www.getgo.sg` + bundled cache used as fallback.

### Test

```bash
cd CarRS
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
```
