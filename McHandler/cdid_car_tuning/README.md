# CDID Car Tuning Assistant

AI-powered car tuning help for **CDID** (Roblox car tuning experience). Uses Ollama for local AI suggestions and problem diagnosis.

## Run

From this folder:

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5001**

## Requirements

- Python 3.7+
- Ollama installed and running (`ollama serve`, `ollama pull llama3.2`)

## Note

This app runs on port **5001** so it can run alongside the Minecraft Mod Handler web app (port 5000) if needed.
