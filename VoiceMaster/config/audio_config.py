import sounddevice as sd

# Audio Configuration
DEFAULT_SAMPLE_RATE = 44100
DEFAULT_CHANNELS = 1  # Mono for vocals
DEFAULT_BLOCKSIZE = 1024
DEFAULT_LATENCY = 'low'

def get_audio_devices():
    """Returns a list of available audio devices."""
    return sd.query_devices()

def get_default_input_device():
    """Returns the default input device index."""
    return sd.default.device[0]

def get_default_output_device():
    """Returns the default output device index."""
    return sd.default.device[1]

def get_device_info(device_id):
    """Returns information about a specific device."""
    try:
        return sd.query_devices(device_id)
    except Exception:
        return None
