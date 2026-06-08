import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
from config.audio_config import DEFAULT_SAMPLE_RATE

class AudioPlayer:
    def __init__(self):
        self.stream = None
        self.is_playing = False
        self.current_frame = 0
        self.data = None
        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.volume = 1.0
        self._lock = threading.Lock()

    def load_file(self, file_path):
        self.data, self.sample_rate = sf.read(file_path, always_2d=True)
        self.current_frame = 0

    def set_data(self, data, sample_rate=DEFAULT_SAMPLE_RATE):
        self.data = data if data.ndim == 2 else data.reshape(-1, 1)
        self.sample_rate = sample_rate
        self.current_frame = 0

    def _audio_callback(self, outdata, frames, time, status):
        if status:
            print(f"Status: {status}")
        
        with self._lock:
            if not self.is_playing or self.data is None:
                outdata.fill(0)
                return

            chunksize = min(len(self.data) - self.current_frame, frames)
            outdata[:chunksize] = self.data[self.current_frame:self.current_frame + chunksize] * self.volume
            
            if chunksize < frames:
                outdata[chunksize:].fill(0)
                self.is_playing = False
                # Callback to notify end of playback could be added here
            
            self.current_frame += chunksize

    def play(self, device_id=None):
        if self.data is None:
            return
            
        with self._lock:
            self.is_playing = True
            
        if self.stream is None or not self.stream.active:
            self.stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.data.shape[1],
                device=device_id,
                callback=self._audio_callback
            )
            self.stream.start()

    def pause(self):
        with self._lock:
            self.is_playing = False

    def stop(self):
        with self._lock:
            self.is_playing = False
            self.current_frame = 0
        if self.stream:
            self.stream.stop()

    def set_volume(self, volume):
        """Volume from 0.0 to 1.0"""
        with self._lock:
            self.volume = max(0.0, min(1.0, volume))

    def get_progress(self):
        if self.data is None or len(self.data) == 0:
            return 0
        return self.current_frame / len(self.data)

    def seek(self, progress):
        """Seek to progress (0.0 to 1.0)"""
        if self.data is None:
            return
        with self._lock:
            self.current_frame = int(progress * len(self.data))
