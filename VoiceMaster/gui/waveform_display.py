from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QRect
import numpy as np

class WaveformDisplay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = None
        self.cursor_pos = 0.0 # 0.0 to 1.0
        self.setMinimumHeight(150)

    def set_data(self, data):
        """Expects 1D numpy array of audio samples."""
        if data is not None and data.ndim > 1:
            self.data = data.flatten()
        else:
            self.data = data
        self.update()

    def set_cursor_pos(self, pos):
        self.cursor_pos = max(0.0, min(1.0, pos))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        rect = self.rect()
        painter.fillRect(rect, QColor(25, 25, 25))
        
        if self.data is None or len(self.data) == 0:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Audio Data")
            return

        # Draw waveform
        painter.setPen(QPen(QColor(52, 152, 219), 1))
        
        mid_y = rect.height() / 2
        width = rect.width()
        
        # Sample the data to fit the width
        step = len(self.data) / width
        
        for x in range(width):
            start = int(x * step)
            end = int((x + 1) * step)
            if start >= len(self.data): break
            
            chunk = self.data[start:end]
            if len(chunk) == 0: continue
            
            vmin = np.min(chunk)
            vmax = np.max(chunk)
            
            y1 = mid_y + vmin * mid_y
            y2 = mid_y + vmax * mid_y
            
            painter.drawLine(x, int(y1), x, int(y2))

        # Draw cursor
        cursor_x = int(self.cursor_pos * width)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawLine(cursor_x, 0, cursor_x, rect.height())
