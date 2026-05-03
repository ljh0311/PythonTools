"""
Speech Module
Handles text-to-speech for ATC phrases
"""
import os
import tempfile
import threading
import time
import pygame
import pyttsx3

from utils.logging_config import get_logger

logger = get_logger(__name__)


class SpeechEngine:
    def __init__(self, rate=150, voice_gender="male"):
        self.rate = rate
        self.voice_gender = voice_gender
        self._is_speaking = False
        self.engine = None
        self.speech_available = False
        
        # Try to initialize the TTS engine with error handling
        try:
            self.engine = pyttsx3.init()
            self.setup_voice()
            self.speech_available = True
            logger.info("Speech engine initialized successfully")
        except Exception as e:
            logger.warning("Speech engine initialization failed: %s. Speech features will be disabled.", e)
            self.speech_available = False
        
        # Initialize pygame for sound playback
        try:
            pygame.mixer.init()
        except Exception as e:
            logger.warning("Audio mixer initialization failed: %s", e)
    
    def setup_voice(self):
        """Configure the TTS engine with the preferred voice and rate"""
        if not self.engine or not self.speech_available:
            return
            
        try:
            self.engine.setProperty('rate', self.rate)
            
            # Get available voices
            voices = self.engine.getProperty('voices')
            
            # Find an appropriate voice based on gender preference
            selected_voice = None
            for voice in voices:
                if self.voice_gender == "male" and "male" in voice.name.lower():
                    selected_voice = voice.id
                    break
                elif self.voice_gender == "female" and "female" in voice.name.lower():
                    selected_voice = voice.id
                    break
            
            # If no matching voice was found, use the first available
            if not selected_voice and voices:
                selected_voice = voices[0].id
                
            if selected_voice:
                self.engine.setProperty('voice', selected_voice)
        except Exception as e:
            logger.warning("Voice setup failed: %s", e)
            self.speech_available = False
    
    def speak(self, text, block=False):
        """Speak the given text, optionally blocking until speech is complete"""
        if not self.speech_available or not self.engine:
            logger.debug("Speech not available. Would have spoken: %s", text)
            return
            
        try:
            if block:
                self._is_speaking = True
                self.engine.say(text)
                self.engine.runAndWait()
                self._is_speaking = False
            else:
                # Use a thread to avoid blocking the GUI
                speech_thread = threading.Thread(target=self._speak_in_thread, args=(text,))
                speech_thread.daemon = True
                speech_thread.start()
        except Exception as e:
            logger.warning("Speech failed: %s", e)
            self.speech_available = False
    
    def _speak_in_thread(self, text):
        """Speak in a separate thread to avoid blocking the main thread"""
        if not self.speech_available or not self.engine:
            return
            
        try:
            self._is_speaking = True
            self.engine.say(text)
            self.engine.runAndWait()
            self._is_speaking = False
        except Exception as e:
            logger.warning("Speech in thread failed: %s", e)
            self._is_speaking = False
    
    def stop(self):
        """Stop any ongoing speech"""
        if self.speech_available and self.engine:
            try:
                self.engine.stop()
            except Exception as e:
                logger.warning("Stop speech failed: %s", e)
        self._is_speaking = False
    
    def is_speaking(self):
        """Check if the engine is currently speaking"""
        return self._is_speaking
    
    def set_rate(self, rate):
        """Set the speech rate"""
        self.rate = rate
        if self.speech_available and self.engine:
            try:
                self.engine.setProperty('rate', rate)
            except Exception as e:
                logger.warning("Set rate failed: %s", e)
    
    def set_voice_gender(self, gender):
        """Set the voice gender preference"""
        self.voice_gender = gender
        self.setup_voice()
    
    def is_speech_available(self):
        """Check if speech functionality is available"""
        return self.speech_available


class AudioPlayer:
    """Plays pre-recorded ATC audio files"""
    def __init__(self, audio_dir="audio"):
        self.audio_dir = audio_dir
        self.current_sound = None
        
        # Create audio directory if it doesn't exist
        if not os.path.exists(audio_dir):
            os.makedirs(audio_dir)
        
        # Initialize pygame for sound playback
        pygame.mixer.init()
    
    def play_audio(self, filename):
        """Play an audio file from the audio directory"""
        full_path = os.path.join(self.audio_dir, filename)
        
        if os.path.exists(full_path):
            self.stop()  # Stop any currently playing audio
            self.current_sound = pygame.mixer.Sound(full_path)
            self.current_sound.play()
            return True
        else:
            logger.warning("Audio file not found: %s", full_path)
            return False
    
    def stop(self):
        """Stop any currently playing audio"""
        pygame.mixer.stop()
        self.current_sound = None
    
    def text_to_audio_file(self, text, filename, speech_engine):
        """Convert text to an audio file using the speech engine"""
        if not speech_engine.speech_available or not speech_engine.engine:
            logger.debug("Speech not available. Cannot create audio file for: %s", text)
            return None
            
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_file.close()
            
            # Save speech to a temporary file
            speech_engine.engine.save_to_file(text, temp_file.name)
            speech_engine.engine.runAndWait()
            
            # Wait for file to be fully written
            time.sleep(0.5)
            
            # Save the file to the audio directory
            output_path = os.path.join(self.audio_dir, filename)
            
            # Copy the temporary file to the output path
            with open(temp_file.name, 'rb') as src, open(output_path, 'wb') as dst:
                dst.write(src.read())
                
            # Delete the temporary file
            os.unlink(temp_file.name)
            
            return output_path
        except Exception as e:
            logger.warning("Failed to create audio file: %s", e)
            return None
        
    def is_playing(self):
        """Check if audio is currently playing"""
        return pygame.mixer.get_busy()


def speech_example():
    """Example of using the speech engine"""
    engine = SpeechEngine()
    engine.speak("Tower, November One Two Three Alpha Bravo, ready for takeoff, runway two seven.")
    
    # Wait for speech to complete
    while engine.is_speaking():
        time.sleep(0.1)
        
    logger.info("Speech completed!") 