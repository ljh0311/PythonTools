import numpy as np
import pyrubberband as pyrb
from config.audio_config import DEFAULT_SAMPLE_RATE

def create_harmony(audio_data, sr=DEFAULT_SAMPLE_RATE, interval_semitones=4, volume=0.5):
    """
    Creates a harmony voice shifted by interval_semitones.
    """
    try:
        shifted = pyrb.pitch_shift(audio_data, sr, n_steps=interval_semitones)
        
        # Match lengths
        if len(shifted) > len(audio_data):
            shifted = shifted[:len(audio_data)]
        elif len(shifted) < len(audio_data):
            # Pad with zeros if it's 2D
            if audio_data.ndim > 1:
                padding = ((0, len(audio_data) - len(shifted)), (0, 0))
            else:
                padding = (0, len(audio_data) - len(shifted))
            shifted = np.pad(shifted, padding)
            
        return shifted * volume
    except Exception as e:
        print(f"Error creating harmony: {e}")
        return np.zeros_like(audio_data)

def apply_harmonizer(audio_data, sr=DEFAULT_SAMPLE_RATE, intervals=[4, 7], volumes=[0.5, 0.4]):
    """
    Applies multiple harmonies to the audio.
    """
    result = np.copy(audio_data)
    for interval, vol in zip(intervals, volumes):
        harmony = create_harmony(audio_data, sr, interval, vol)
        result += harmony
    return result
