import noisereduce as nr
import numpy as np
from config.audio_config import DEFAULT_SAMPLE_RATE

def apply_noise_reduction(audio_data, sr=DEFAULT_SAMPLE_RATE, stationary=True):
    """
    Applies noise reduction using noisereduce.
    """
    if audio_data.ndim > 1:
        # Process each channel separately if stereo
        reduced = np.zeros_like(audio_data)
        for i in range(audio_data.shape[1]):
            reduced[:, i] = nr.reduce_noise(y=audio_data[:, i], sr=sr, stationary=stationary)
        return reduced
    else:
        return nr.reduce_noise(y=audio_data, sr=sr, stationary=stationary)
