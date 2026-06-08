# VoiceMaster: AI-Powered Vocal Production Suite

VoiceMaster is a desktop application designed for singers and producers to record, refine, and tune vocal performances with the assistance of local AI via Ollama.

## Features

- **High-Quality Recording:** Low-latency audio capture.
- **Vocal DSP Pipeline:**
  - **Pitch Correction:** Snap vocals to the nearest MIDI note.
  - **Noise Reduction:** Clean up background noise.
  - **Formant Shifting:** Modify the character/gender of the voice.
  - **Effects Rack:** Professional Reverb, Compression, and more.
  - **Harmonizer:** Generate vocal harmonies automatically.
- **Ollama AI Integration:**
  - **Lyrics Generator:** Collaborative songwriting.
  - **Mixing Advisor:** Technical tips based on audio analysis.
  - **Voice Coach:** Performance feedback and improvement tips.
- **Real-time Monitoring:** Hear yourself with effects while recording.
- **Project Management:** Save your sessions and export your final mix.

## Installation

1. **Install Ollama:** Download and install from [ollama.com](https://ollama.com).
2. **Pull a Model:** Run `ollama pull llama3` in your terminal.
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run VoiceMaster:**
   ```bash
   python main.py
   ```

## Tech Stack

- **GUI:** PyQt6
- **Audio:** sounddevice, librosa, pedalboard, parselmouth, pyrubberband
- **AI:** Ollama Python Client
- **Processing:** NumPy, SciPy
