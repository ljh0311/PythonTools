# CDID Car Tuning Assistant

AI car tuning help for **CDID** (Roblox). Uses local Ollama for suggestions and problem diagnosis.

## Run

From the **McHandler** root (recommended):

```bash
pip install -r requirements.txt
python run_cdid_web.py
```

Or from this folder:

```bash
pip install -r requirements.txt
python app.py
```

Open **http://localhost:5001**

Port 5001 avoids conflicting with the Minecraft Mod Handler web app (5000).

## Requirements

- Python 3.7+
- Ollama (`ollama serve`, `ollama pull llama3.2`)

## Layout

```
cdid_car_tuning/
├── app.py           # Flask app
├── cdid_tuner.py    # Ollama tuning logic
├── templates/       # Web UI
└── static/          # CSS + app.js
```
