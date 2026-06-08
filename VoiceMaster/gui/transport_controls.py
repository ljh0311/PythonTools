from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSlider
from PyQt6.QtCore import Qt, pyqtSignal

class TransportControls(QWidget):
    # Signals
    play_pressed = pyqtSignal()
    pause_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()
    record_pressed = pyqtSignal()
    volume_changed = pyqtSignal(float)
    seek_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        
        self.record_btn = QPushButton("REC")
        self.record_btn.setObjectName("recordButton")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self.record_pressed.emit)
        
        self.play_btn = QPushButton("PLAY")
        self.play_btn.setObjectName("playButton")
        self.play_btn.clicked.connect(self.play_pressed.emit)
        
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.clicked.connect(self.pause_pressed.emit)
        
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.clicked.connect(self.stop_pressed.emit)
        
        layout.addWidget(self.record_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.stop_btn)
        
        layout.addSpacing(20)
        
        layout.addWidget(QLabel("Vol:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(lambda v: self.volume_changed.emit(v / 100.0))
        layout.addWidget(self.volume_slider)
        
        self.setLayout(layout)

    def set_recording(self, recording):
        self.record_btn.setChecked(recording)
        self.record_btn.setText("STOP REC" if recording else "REC")
