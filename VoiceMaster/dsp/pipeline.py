from dsp.pitch_correction import apply_pitch_correction
from dsp.noise_reduction import apply_noise_reduction
from dsp.formant_shifter import apply_formant_shift
from dsp.effects import EffectsRack
from dsp.harmonizer import apply_harmonizer
from config.audio_config import DEFAULT_SAMPLE_RATE

class DSPPipeline:
    def __init__(self, sr=DEFAULT_SAMPLE_RATE):
        self.sr = sr
        self.effects_rack = EffectsRack(sr)
        self.settings = {
            'pitch_correction': {'enabled': False, 'strength': 0.8},
            'noise_reduction': {'enabled': False, 'stationary': True},
            'formant_shift': {'enabled': False, 'factor': 1.0},
            'harmonizer': {'enabled': False, 'intervals': [4, 7], 'volumes': [0.5, 0.3]},
            'reverb': {'enabled': False, 'room_size': 0.5, 'wet_level': 0.3},
            'compressor': {'enabled': False, 'threshold': -20, 'ratio': 4.0}
        }

    def update_setting(self, effect_name, key, value):
        if effect_name in self.settings:
            self.settings[effect_name][key] = value

    def process(self, audio_data):
        processed = audio_data.copy()

        # 1. Noise Reduction (usually first)
        if self.settings['noise_reduction']['enabled']:
            processed = apply_noise_reduction(
                processed, 
                self.sr, 
                self.settings['noise_reduction']['stationary']
            )

        # 2. Pitch Correction
        if self.settings['pitch_correction']['enabled']:
            processed = apply_pitch_correction(
                processed, 
                self.sr, 
                self.settings['pitch_correction']['strength']
            )

        # 3. Formant Shifting
        if self.settings['formant_shift']['enabled']:
            processed = apply_formant_shift(
                processed, 
                self.sr, 
                self.settings['formant_shift']['factor']
            )

        # 4. Harmonizer
        if self.settings['harmonizer']['enabled']:
            processed = apply_harmonizer(
                processed, 
                self.sr, 
                self.settings['harmonizer']['intervals'],
                self.settings['harmonizer']['volumes']
            )

        # 5. Effects Rack (Reverb, Comp, etc.)
        self.effects_rack.clear()
        if self.settings['compressor']['enabled']:
            self.effects_rack.add_compressor(
                threshold_db=self.settings['compressor']['threshold'],
                ratio=self.settings['compressor']['ratio']
            )
        if self.settings['reverb']['enabled']:
            self.effects_rack.add_reverb(
                room_size=self.settings['reverb']['room_size'],
                wet_level=self.settings['reverb']['wet_level']
            )
        
        processed = self.effects_rack.process(processed)

        return processed
