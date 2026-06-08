import numpy as np
import librosa

def get_audio_stats(audio_data, sr=44100):
    """Computes basic statistics for audio analysis."""
    if audio_data is None or len(audio_data) == 0:
        return {}
        
    # Convert to mono for analysis if needed
    if audio_data.ndim > 1:
        mono_data = np.mean(audio_data, axis=1)
    else:
        mono_data = audio_data

    stats = {
        "peak": float(np.max(np.abs(mono_data))),
        "rms": float(np.sqrt(np.mean(mono_data**2))),
        "duration": float(len(mono_data) / sr)
    }
    
    # Simple spectral balance
    try:
        spectral_centroid = librosa.feature.spectral_centroid(y=mono_data, sr=sr)
        stats["avg_spectral_centroid"] = float(np.mean(spectral_centroid))
    except Exception:
        pass
        
    return stats
