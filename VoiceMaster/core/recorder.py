import sounddevice as sd
import numpy as np
import soundfile as sf
import threading
import queue
import os
from config.audio_config import DEFAULT_SAMPLE_RATE, DEFAULT_CHANNELS

class AudioRecorder:
    def __init__(self, sample_rate=DEFAULT_SAMPLE_RATE, channels=DEFAULT_CHANNELS):
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.recorded_data = []
        self.stream = None
        self.audio_queue = queue.Queue()
        self.file_path = None

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(f"Status: {status}")
        self.audio_queue.put(indata.copy())

    def start_recording(self, device_id=None):
        if self.recording:
            return
        
        self.recorded_data = []
        self.recording = True
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            device=device_id,
            callback=self._audio_callback
        )
        self.stream.start()

    def stop_recording(self, output_file=None):
        if not self.recording:
            return None
        
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
        
        # Collect all data from queue
        while not self.audio_queue.empty():
            self.recorded_data.append(self.audio_queue.get())
            
        if not self.recorded_data:
            return None
            
        full_recording = np.concatenate(self.recorded_data, axis=0)
        
        if output_file:
            sf.write(output_file, full_recording, self.sample_rate)
            self.file_path = output_file
            
        return full_recording

    def is_recording(self):
        return self.recording
