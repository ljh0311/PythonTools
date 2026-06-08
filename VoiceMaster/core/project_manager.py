import json
import os
import soundfile as sf
import numpy as np

class ProjectManager:
    def __init__(self, projects_dir="projects"):
        self.projects_dir = projects_dir
        os.makedirs(self.projects_dir, exist_ok=True)

    def save_project(self, project_name, audio_data, settings, sr=44100):
        project_path = os.path.join(self.projects_dir, project_name)
        os.makedirs(project_path, exist_ok=True)
        
        # Save Audio
        audio_file = os.path.join(project_path, "recording.wav")
        sf.write(audio_file, audio_data, sr)
        
        # Save Settings
        config_file = os.path.join(project_path, "config.json")
        with open(config_file, "w") as f:
            json.dump(settings, f, indent=4)
            
        return project_path

    def load_project(self, project_name):
        project_path = os.path.join(self.projects_dir, project_name)
        if not os.path.exists(project_path):
            return None, None
            
        # Load Audio
        audio_file = os.path.join(project_path, "recording.wav")
        audio_data, sr = sf.read(audio_file)
        
        # Load Settings
        config_file = os.path.join(project_path, "config.json")
        with open(config_file, "r") as f:
            settings = json.load(f)
            
        return audio_data, settings

    def export_audio(self, output_path, audio_data, sr=44100):
        sf.write(output_path, audio_data, sr)
