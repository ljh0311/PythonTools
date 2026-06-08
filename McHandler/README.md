# McHandler

This folder contains **two separate apps** with clear naming:

| App | Description | How to run |
|-----|-------------|------------|
| **Minecraft Mod Handler** | Mods, shaderpacks, crash analysis, compatibility (Minecraft) | `python main.py` (GUI) or `python run_web.py` (web at http://localhost:5000) |
| **CDID Car Tuning Assistant** | AI car tuning for CDID (Roblox) | `python run_cdid_web.py` (web at http://localhost:5001) |

- **Minecraft** uses: `app.py`, `main.py`, `gui.py`, `mod_manager.py`, `crash_analyzer.py`, etc., and the root `templates/` and `static/`.
- **CDID** is self-contained in the **`cdid_car_tuning/`** subfolder (its own `app.py`, templates, static). Run from repo root with `run_cdid_web.py` or from inside the folder with `python app.py`.

---

# Minecraft Mod Handler

A Python app for managing Minecraft mods and analyzing crash logs with AI (Ollama).

## Features

- **Mod Management**: View, enable/disable, and organize mods
- **Crash Log Analysis**: AI-powered crash log insights and solutions
- **Mod Compatibility**: Detect potential mod conflicts
- **Backup & Restore**: Safeguard and recover your mod collection
- **AI Suggestions**: Get smart recommendations for mod issues

---

## Requirements

- Python 3.7+
- Ollama (installed & running)
- Minecraft (with mods)

---

## Installation

1. **Clone/download** this repository.
2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   > `tkinter` is usually included with Python. If missing:
   > - **Windows/macOS**: Included by default  
   > - **Ubuntu/Debian**: `sudo apt-get install python3-tk`
3. **Install & start Ollama:**

   ```bash
   # See https://ollama.ai for full instructions
   ollama pull llama3.2
   ollama serve
   ```

---

## Usage

1. **Start the app:**

   ```bash
   python main.py
   ```

2. **Setup:**
   - Configure Ollama in the Settings tab
   - Select your Minecraft directory in Mod Management
3. **Mod Management:**
   - Browse/select your Minecraft directory
   - Click "Load Mods" to view installed mods
   - Use buttons to backup, enable/disable mods
   - Get AI suggestions for mod issues
4. **Crash Log Analysis:**
   - Select a crash log file
   - Click "Analyze" for AI-powered insights

---

## File Structure (Minecraft)

- `main.py` — GUI entry point
- `run_web.py` — Web app launcher (port 5000)
- `app.py` — Flask web app
- `gui.py` — Desktop UI
- `mod_manager.py` — Mod management logic
- `crash_analyzer.py` — AI crash log analysis
- `templates/`, `static/` — Web UI for Minecraft
- `cdid_car_tuning/` — **Separate app**: CDID Car Tuning (Roblox), port 5001
- `requirements.txt` — Dependencies for Minecraft (and shared)

---

## Supported Mod Formats

- Forge (`mcmod.info`)
- Fabric (`fabric.mod.json`)
- Legacy (`mods.toml`)

---

## Troubleshooting

**Ollama Connection**

- Ensure Ollama is running: `ollama serve`
- Check models: `ollama list`
- Verify API endpoint

**Mod Loading**

- Select the correct Minecraft directory
- Ensure the `mods` folder contains `.jar` files
- Some mods may lack metadata

**General**

- Check file permissions if mods don't appear
- Large mod lists may load slowly
- AI analysis requires internet for model downloads

---

## Contributing

Contributions and suggestions welcome!

---

## License

MIT License
