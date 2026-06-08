from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QCheckBox, 
                             QSlider, QLabel, QFormLayout, QScrollArea, QTabWidget)
from PyQt6.QtCore import Qt, pyqtSignal

class EffectsPanel(QWidget):
    setting_changed = pyqtSignal(str, str, object) # effect, key, value

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        container_layout = QVBoxLayout()
        
        # Noise Reduction
        nr_group = self.create_group("Noise Reduction", "noise_reduction", [
            ("enabled", "Enabled", "bool"),
            ("stationary", "Stationary Noise", "bool")
        ])
        container_layout.addWidget(nr_group)
        
        # Pitch Correction
        pc_group = self.create_group("Pitch Correction (Auto-Tune)", "pitch_correction", [
            ("enabled", "Enabled", "bool"),
            ("strength", "Correction Strength", "float")
        ])
        container_layout.addWidget(pc_group)
        
        # Formant Shifter
        fs_group = self.create_group("Formant Shift", "formant_shift", [
            ("enabled", "Enabled", "bool"),
            ("factor", "Shift Factor", "float", 0.5, 2.0)
        ])
        container_layout.addWidget(fs_group)
        
        # Harmonizer
        harm_group = self.create_group("Harmonizer", "harmonizer", [
            ("enabled", "Enabled", "bool")
        ])
        container_layout.addWidget(harm_group)
        
        # Reverb
        rev_group = self.create_group("Reverb", "reverb", [
            ("enabled", "Enabled", "bool"),
            ("room_size", "Room Size", "float"),
            ("wet_level", "Wet Level", "float")
        ])
        container_layout.addWidget(rev_group)
        
        container_layout.addStretch()
        container.setLayout(container_layout)
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.setLayout(layout)

    def create_group(self, title, effect_id, controls):
        group = QGroupBox(title)
        layout = QFormLayout()
        
        for ctrl_data in controls:
            key = ctrl_data[0]
            label_text = ctrl_data[1]
            type_ = ctrl_data[2]
            
            if type_ == "bool":
                cb = QCheckBox()
                cb.toggled.connect(lambda v, e=effect_id, k=key: self.setting_changed.emit(e, k, v))
                layout.addRow(label_text, cb)
            elif type_ == "float":
                min_v = ctrl_data[3] if len(ctrl_data) > 3 else 0.0
                max_v = ctrl_data[4] if len(ctrl_data) > 4 else 1.0
                
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setRange(0, 100)
                slider.setValue(int(((1.0 if len(ctrl_data) <= 5 else ctrl_data[5]) - min_v) / (max_v - min_v) * 100))
                
                # We need a proxy to convert slider int to float
                def make_callback(e, k, mn, mx):
                    return lambda v: self.setting_changed.emit(e, k, mn + (v / 100.0) * (mx - mn))
                
                slider.valueChanged.connect(make_callback(effect_id, key, min_v, max_v))
                layout.addRow(label_text, slider)
                
        group.setLayout(layout)
        return group
