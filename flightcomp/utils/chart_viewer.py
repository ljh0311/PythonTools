"""
Airport Chart Viewer
Displays airport charts and diagrams
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Optional
from models.airport_database import AirportDatabase, AirportLayout
from utils.logging_config import get_logger

logger = get_logger(__name__)


class ChartViewer:
    """Viewer for airport charts"""
    
    def __init__(self, parent, airport_db: AirportDatabase):
        """
        Initialize chart viewer
        
        Args:
            parent: Parent widget
            airport_db: AirportDatabase instance
        """
        self.parent = parent
        self.airport_db = airport_db
        self.current_airport: Optional[AirportLayout] = None
        self.chart_image: Optional[Image.Image] = None
    
    def display_airport_chart(self, icao: str) -> bool:
        """
        Display airport chart for given ICAO code
        
        Returns:
            True if chart displayed successfully, False otherwise
        """
        airport = self.airport_db.get_airport(icao)
        if not airport:
            return False
        
        self.current_airport = airport
        
        # chart_path is optional; paths are relative to project root. Missing file = no chart.
        if airport.chart_path:
            path = airport.chart_path
            if not os.path.isabs(path):
                root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                path = os.path.join(root, path)
            if os.path.exists(path):
                try:
                    self.chart_image = Image.open(path)
                    return True
                except Exception as e:
                    logger.warning("Error loading chart: %s", e)
                    return False
        return False
    
    def get_chart_image(self) -> Optional[Image.Image]:
        """Get current chart image"""
        return self.chart_image
    
    def create_chart_widget(self, parent_frame) -> tk.Canvas:
        """Create a canvas widget for displaying the chart"""
        canvas = tk.Canvas(parent_frame, bg="white", scrollregion=(0, 0, 1000, 1000))
        
        if self.chart_image:
            # Resize image to fit canvas
            canvas_width = canvas.winfo_reqwidth() or 800
            canvas_height = canvas.winfo_reqheight() or 600
            
            img_width, img_height = self.chart_image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            resized_image = self.chart_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
            
            canvas.create_image(canvas_width // 2, canvas_height // 2, image=photo, anchor=tk.CENTER)
            canvas.image = photo  # Keep a reference
        
        return canvas

