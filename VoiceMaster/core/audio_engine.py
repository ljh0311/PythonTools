import threading
import numpy as np
import sounddevice as sd
from core.recorder import AudioRecorder
from core.player import AudioPlayer
from dsp.pipeline import DSPPipeline
from config.audio_config import get_default_input_device, get_default_output_device, DEFAULT_SAMPLE_RATE, DEFAULT_CHANNELS, DEFAULT_BLOCKSIZE

class AudioEngine:
    def __init__(self):
        self.recorder = AudioRecorder()
        self.player = AudioPlayer()
        self.pipeline = DSPPipeline()
        self.input_device = get_default_input_device()
        self.output_device = get_default_output_device()
        
        # Real-time state
        self.realtime_active = False
        self.rt_stream = None
        self.monitoring_enabled = False

    def _realtime_callback(self, indata, outdata, frames, time, status):
        """Callback for real-time audio processing."""
        if status:
            print(f"RT Status: {status}")
        
        # Process input through pipeline
        processed = self.pipeline.process(indata)
        
        # Output processed audio
        if processed.ndim == 1:
            processed = processed.reshape(-1, 1)
        
        # Ensure output buffer size matches
        outdata[:len(processed)] = processed
        if len(processed) < frames:
            outdata[len(processed):].fill(0)

    def start_realtime(self):
        """Starts real-time processing loop."""
        if self.realtime_active:
            return
            
        self.realtime_active = True
        self.rt_stream = sd.Stream(
            device=(self.input_device, self.output_device),
            samplerate=DEFAULT_SAMPLE_RATE,
            blocksize=DEFAULT_BLOCKSIZE,
            channels=DEFAULT_CHANNELS,
            callback=self._realtime_callback
        )
        self.rt_stream.start()

    def stop_realtime(self):
        """Stops real-time processing loop."""
        self.realtime_active = False
        if self.rt_stream:
            self.rt_stream.stop()
            self.rt_stream.close()
            self.rt_stream = None

    def set_input_device(self, device_id):
        self.input_device = device_id

    def set_output_device(self, device_id):
        self.output_device = device_id

    def start_recording(self, output_file=None):
        self.recorder.start_recording(device_id=self.input_device)

    def stop_recording(self, output_file=None):
        data = self.recorder.stop_recording(output_file=output_file)
        if data is not None:
            self.player.set_data(data)
        return data

    def play(self):
        self.player.play(device_id=self.output_device)

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def set_volume(self, volume):
        self.player.set_volume(volume)

    def toggle_monitoring(self, enabled):
        """Enable/disable hearing input through output."""
        self.monitoring_enabled = enabled
        # This will be more complex in real-time mode (Phase 3)
        # For now, we'll keep it simple or implement via a direct callback if needed.
        pass

    def load_audio(self, file_path):
        self.player.load_file(file_path)

    def get_recorded_data(self):
        return self.player.data

    def get_playback_progress(self):
        return self.player.get_progress()

    def seek(self, progress):
        self.player.seek(progress)
