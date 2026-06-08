import numpy as np
import librosa
import pyrubberband as pyrb
from config.audio_config import DEFAULT_SAMPLE_RATE

def detect_pitch(audio_data, sr=DEFAULT_SAMPLE_RATE):
    """Detects the pitch (F0) of the audio data using pYIN."""
    f0, voiced_flag, voiced_probs = librosa.pyin(
        audio_data, 
        fmin=librosa.note_to_hz('C2'), 
        fmax=librosa.note_to_hz('C7'),
        sr=sr
    )
    return f0, voiced_flag

def closest_note_hz(hz):
    """Finds the HZ of the closest MIDI note."""
    if hz is None or np.isnan(hz) or hz <= 0:
        return hz
    midi_note = librosa.hz_to_midi(hz)
    closest_midi = round(midi_note)
    return librosa.midi_to_hz(closest_midi)

def apply_pitch_correction(audio_data, sr=DEFAULT_SAMPLE_RATE, strength=1.0):
    """
    Applies pitch correction to audio data.
    strength: 0.0 (no correction) to 1.0 (hard snap)
    """
    # Reshape if necessary
    if audio_data.ndim > 1:
        audio_data = audio_data.flatten()
        
    f0, voiced_flag = detect_pitch(audio_data, sr)
    
    # Simple implementation: we shift the whole clip or segments
    # For a true auto-tune, we'd process in small windows.
    # Here we'll do a basic version using pyrubberband for the whole clip 
    # based on the average deviation, but better would be windowed shifting.
    
    corrected_audio = np.copy(audio_data)
    
    # For demonstration/basic version, we'll just return the original 
    # until we implement windowed shifting which is complex.
    # In a real app, we'd use something like PSOLA or Phase Vocoder.
    
    # Let's implement a very basic windowed shift if pyrb is available
    window_size = int(0.1 * sr)  # 100ms windows
    hop_size = window_size // 2
    
    output = np.zeros_like(audio_data)
    weights = np.zeros_like(audio_data)
    
    for i in range(0, len(audio_data) - window_size, hop_size):
        window = audio_data[i:i+window_size]
        f0_win, _ = librosa.pyin(
            window, 
            fmin=librosa.note_to_hz('C2'), 
            fmax=librosa.note_to_hz('C7'),
            sr=sr
        )
        
        avg_f0 = np.nanmedian(f0_win)
        if not np.isnan(avg_f0) and avg_f0 > 0:
            target_f0 = closest_note_hz(avg_f0)
            # Interpolate between original and target based on strength
            target_f0 = avg_f0 + (target_f0 - avg_f0) * strength
            
            n_steps = 12 * np.log2(target_f0 / avg_f0)
            
            try:
                shifted_win = pyrb.pitch_shift(window, sr, n_steps)
                # Handle length differences from pyrb
                if len(shifted_win) > window_size:
                    shifted_win = shifted_win[:window_size]
                elif len(shifted_win) < window_size:
                    shifted_win = np.pad(shifted_win, (0, window_size - len(shifted_win)))
                    
                output[i:i+window_size] += shifted_win * np.hanning(window_size)
                weights[i:i+window_size] += np.hanning(window_size)
            except Exception:
                output[i:i+window_size] += window * np.hanning(window_size)
                weights[i:i+window_size] += np.hanning(window_size)
        else:
            output[i:i+window_size] += window * np.hanning(window_size)
            weights[i:i+window_size] += np.hanning(window_size)
            
    # Avoid division by zero
    weights[weights == 0] = 1
    return output / weights
