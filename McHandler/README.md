# McHandler

Two apps in one folder:

| App | Description | Run |
|-----|-------------|-----|
| **Minecraft Mod Handler** | Mods, shaderpacks, crash analysis, compatibility | `python main.py` (GUI) or `python run_web.py` → http://localhost:5000 |
| **CDID Car Tuning** | AI car tuning for CDID (Roblox) | `python run_cdid_web.py` or `python cdid.py` → http://localhost:5001 |

Install once from this folder:

```bash
pip install -r requirements.txt
```

Ollama must be running for AI features (`ollama serve`, `ollama pull llama3.2`).

---

## Minecraft Mod Handler

### Features

- Mod management (enable/disable, backup, organize)
- Shaderpack management
- AI crash log analysis (Ollama)
- Mod compatibility checking

### Configuration

Copy `config.example.json` to `config.json` and set your Minecraft instance path (GUI Settings tab or web Settings page can also persist paths and Ollama options).

Optional web env vars: `FLASK_HOST` (default `127.0.0.1`), `FLASK_PORT`, `FLASK_DEBUG`, `SECRET_KEY`.

### Layout

```
McHandler/
├── main.py, gui.py              # Desktop GUI
├── run_web.py, app.py           # Web app (port 5000)
├── mod_manager.py               # Mod logic
├── crash_analyzer.py            # Crash analysis
├── ollama_client.py             # Shared Ollama HTTP client
├── flask_config.py              # Flask env-based runtime config
├── compatibility_checker.py     # Compatibility checks
├── shaderpack_manager.py        # Shaderpacks
├── settings_manager.py          # config.json persistence
├── templates/, static/          # Minecraft web UI
├── config.example.json          # Settings template
└── cdid_car_tuning/             # CDID app (see below)
```

### Supported mod metadata

- Forge (`mcmod.info`)
- Fabric (`fabric.mod.json`)
- Legacy (`mods.toml`)

---

## CDID Car Tuning Assistant

Self-contained in `cdid_car_tuning/` (own `app.py`, templates, static). The root launchers `run_cdid_web.py` and `cdid.py` start it on port **5001** so it can run beside the Minecraft web app.

From `cdid_car_tuning/` you can also run `python app.py` directly.

See [cdid_car_tuning/README.md](cdid_car_tuning/README.md).

---

## Troubleshooting

**Ollama** — `ollama serve`, check `ollama list`, verify URL in settings.

**Mods not loading** — Confirm instance directory (e.g. ATLauncher instance folder, not only `.minecraft`).

**Web** — Minecraft: `run_web.py`. CDID: `run_cdid_web.py`. Check the terminal for Flask errors.

---

## License

MIT
