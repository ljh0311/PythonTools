from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, 
                             QPushButton, QLabel, QComboBox, QHBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from ai.ollama_client import OllamaClient
from ai.lyrics_generator import LyricsGenerator
from ai.mixing_advisor import MixingAdvisor
from ai.voice_coach import VoiceCoach

class AIResponseHandler(QObject):
    response_received = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

class AIAssistantPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ollama = OllamaClient()
        self.lyrics_gen = LyricsGenerator(self.ollama)
        self.mixing_advisor = MixingAdvisor(self.ollama)
        self.voice_coach = VoiceCoach(self.ollama)
        
        self.setup_ai_response_handler()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Mode Selector
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("AI Assistant:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Lyrics", "Mixing Advice", "Voice Coach"])
        mode_layout.addWidget(self.mode_combo)
        layout.addLayout(mode_layout)
        
        # Chat Display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("AI responses will appear here...")
        layout.addWidget(self.chat_display)
        
        # Input Area
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your request here (e.g., 'Write a chorus about summer')")
        self.input_field.returnPressed.connect(self.send_request)
        layout.addWidget(self.input_field)
        
        self.send_btn = QPushButton("Send Request")
        self.send_btn.clicked.connect(self.send_request)
        layout.addWidget(self.send_btn)
        
        self.setLayout(layout)

    def send_request(self):
        text = self.input_field.text().strip()
        if not text: return
        
        mode = self.mode_combo.currentText()
        self.chat_display.append(f"<b>You ({mode}):</b> {text}")
        self.input_field.clear()
        
        self.chat_display.append("<i>AI is thinking...</i>")
        
        if mode == "Lyrics":
            self.lyrics_gen.generate_lyrics(text, callback=self.on_ai_response)
        elif mode == "Mixing Advice":
            # In a real scenario, we'd pass actual audio stats
            self.mixing_advisor.advise_on_audio({"input": text}, callback=self.on_ai_response)
        elif mode == "Voice Coach":
            self.voice_coach.provide_feedback({"input": text}, callback=self.on_ai_response)


    def setup_ai_response_handler(self):
        self.ai_response_handler = AIResponseHandler()
        self.ai_response_handler.response_received.connect(self.display_ai_response)

    def on_ai_response(self, response):
        # This method can be called from any thread.
        # It uses a Qt signal to safely update the GUI on the main thread.
        self.ai_response_handler.response_received.emit(response)

    def display_ai_response(self, response):
        self.chat_display.append(f"<b>AI:</b> {response}")
        self.chat_display.append("<br>")