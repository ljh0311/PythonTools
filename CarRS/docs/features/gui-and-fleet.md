# GUI panels, recommendations UX, GetGo fleet

## Panels

- **Recommendations** — primary trip form (distance, duration, region) and ranked results.
- **Records** — CSV history, add/edit with dates, collection location, vision import.
- **Settings** — data path, GetGo fleet refresh, Ollama/ML toggles.

## GetGo fleet sync

- Bundled `getgo_fleet_cache.json` seeds the car-model combobox.
- **Settings → Refresh GetGo fleet** updates from the web (Firecrawl CLI preferred).
- Auto-refresh default: every **720 hours** (1 month).

## Local data

Rental CSV, `settings.json`, and spreadsheets are gitignored and must remain on your machine only.
