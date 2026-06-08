from pedalboard import Pedalboard, Reverb, Compressor, Chorus, Delay, Distortion, HighpassFilter, LowpassFilter
import numpy as np
from config.audio_config import DEFAULT_SAMPLE_RATE

class EffectsRack:
    def __init__(self, sr=DEFAULT_SAMPLE_RATE):
        self.sr = sr
        self.board = Pedalboard()
        self._effects = {}

    def add_reverb(self, room_size=0.5, damping=0.5, wet_level=0.33, dry_level=0.4):
        reverb = Reverb(room_size=room_size, damping=damping, wet_level=wet_level, dry_level=dry_level)
        self.board.append(reverb)
        self._effects['reverb'] = reverb

    def add_compressor(self, threshold_db=-20, ratio=4.0):
        compressor = Compressor(threshold_db=threshold_db, ratio=ratio)
        self.board.append(compressor)
        self._effects['compressor'] = compressor

    def add_chorus(self, rate_hz=1.0, depth=0.25, centre_delay_ms=7.0, feedback=0.0, mix=0.5):
        chorus = Chorus(rate_hz=rate_hz, depth=depth, centre_delay_ms=centre_delay_ms, feedback=feedback, mix=mix)
        self.board.append(chorus)
        self._effects['chorus'] = chorus

    def add_delay(self, delay_seconds=0.5, feedback=0.5, mix=0.5):
        delay = Delay(delay_seconds=delay_seconds, feedback=feedback, mix=mix)
        self.board.append(delay)
        self._effects['delay'] = delay

    def add_eq(self, low_cutoff=100, high_cutoff=10000):
        hp = HighpassFilter(cutoff_frequency_hz=low_cutoff)
        lp = LowpassFilter(cutoff_frequency_hz=high_cutoff)
        self.board.append(hp)
        self.board.append(lp)
        self._effects['hp_filter'] = hp
        self._effects['lp_filter'] = lp

    def process(self, audio_data):
        # Pedalboard expects (channels, samples) or (samples,)
        # Our data is (samples, channels)
        if audio_data.ndim > 1:
            input_data = audio_data.T
            processed = self.board(input_data, self.sr)
            return processed.T
        else:
            return self.board(audio_data, self.sr)

    def clear(self):
        self.board = Pedalboard()
        self._effects = {}
