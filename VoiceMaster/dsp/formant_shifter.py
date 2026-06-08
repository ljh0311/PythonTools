import parselmouth
from parselmouth.praat import call
import numpy as np
from config.audio_config import DEFAULT_SAMPLE_RATE

def apply_formant_shift(audio_data, sr=DEFAULT_SAMPLE_RATE, formant_factor=1.0, pitch_factor=1.0):
    """
    Shifts formants using Praat (via parselmouth).
    formant_factor: > 1.0 makes voice deeper/larger, < 1.0 makes it brighter/smaller.
    pitch_factor: Changes pitch without changing duration.
    """
    # Convert to parselmouth Sound object
    # Praat expects mono or stereo in a specific format
    if audio_data.ndim > 1:
        # Praat parselmouth handles mono better for this specific call usually
        # but let's try to handle 1D
        audio_data = audio_data.flatten()
        
    sound = parselmouth.Sound(audio_data, sampling_frequency=sr)
    
    # Use Praat's Change Gender function for formant/pitch shifting
    # Parameters: (sound, formant_shift_ratio, new_pitch_median, pitch_range_factor, duration_factor)
    # We'll use 0 for pitch parameters to keep them unchanged or use pitch_factor
    
    # pitch_median = 0 means no change
    new_sound = call(sound, "Change gender", 75, 600, formant_factor, 0, pitch_factor, 1.0)
    
    return new_sound.values.T # Returns 2D array [samples, channels]
