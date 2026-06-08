import sys
import os
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QDockWidget)
from PyQt6.QtCore import Qt, QTimer
from gui.waveform_display import WaveformDisplay
from gui.transport_controls import TransportControls
from gui.effects_panel import EffectsPanel
from gui.ai_assistant_panel import AIAssistantPanel
from core.audio_engine import AudioEngine

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VoiceMaster - AI Vocal Studio")
        self.resize(1200, 800)
        
        self.audio_engine = AudioEngine()
        
        self.init_ui()
        self.load_styles()
        
        # Timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(50) # 20 FPS

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("VoiceMaster")
        header.setObjectName("titleLabel")
        main_layout.addWidget(header)
        
        # Waveform
        self.waveform = WaveformDisplay()
        main_layout.addWidget(self.waveform)
        
        # Controls
        self.controls = TransportControls()
        self.controls.record_pressed.connect(self.toggle_recording)
        self.controls.play_pressed.connect(self.audio_engine.play)
        self.controls.pause_pressed.connect(self.audio_engine.pause)
        self.controls.stop_pressed.connect(self.audio_engine.stop)
        self.controls.volume_changed.connect(self.audio_engine.set_volume)
        main_layout.addWidget(self.controls)
        
        # Effects Panel (Dockable)
        self.fx_dock = QDockWidget("Vocal Effects", self)
        self.fx_panel = EffectsPanel()
        self.fx_panel.setting_changed.connect(self.audio_engine.pipeline.update_setting)
        self.fx_dock.setWidget(self.fx_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.fx_dock)
        
        # AI Assistant Panel (Dockable)
        self.ai_dock = QDockWidget("AI Assistant", self)
        self.ai_panel = AIAssistantPanel()
        self.ai_dock.setWidget(self.ai_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.ai_dock)
        
        # Real-time Toggle
        self.rt_btn = QPushButton("Enable Real-time Monitoring")
        self.rt_btn.setCheckable(True)
        self.rt_btn.clicked.connect(self.toggle_realtime)
        main_layout.addWidget(self.rt_btn)
        
        # Status Bar
        self.statusBar().showMessage("Ready")

    def load_styles(self):
        style_path = os.path.join(os.path.dirname(__file__), "styles", "dark_theme.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())

    def toggle_recording(self):
        if self.audio_engine.recorder.is_recording():
            data = self.audio_engine.stop_recording()
            self.waveform.set_data(data)
            self.controls.set_recording(False)
            self.statusBar().showMessage("Recording stopped")
        else:
            self.audio_engine.start_recording()
            self.controls.set_recording(True)
            self.statusBar().showMessage("Recording...")

    def toggle_realtime(self, checked):
        if checked:
            self.audio_engine.start_realtime()
            self.rt_btn.setText("Disable Real-time Monitoring")
            self.statusBar().showMessage("Real-time monitoring active")
        else:
            self.audio_engine.stop_realtime()
            self.rt_btn.setText("Enable Real-time Monitoring")
            self.statusBar().showMessage("Real-time monitoring stopped")

    def update_ui(self):
        # Update progress cursor
        progress = self.audio_engine.get_playback_progress()
        self.waveform.set_cursor_pos(progress)
