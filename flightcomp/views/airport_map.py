"""
Interactive Airport Map
Displays airport layout with taxiways, runways, and aircraft positions
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Tuple, Any
import time
from models.airport_database import AirportDatabase, AirportLayout, Runway, Taxiway, Gate, HotSpot


class AirportMapView:
    """Interactive airport map view"""
    
    def __init__(self, parent, airport_db: AirportDatabase):
        """
        Initialize airport map view
        
        Args:
            parent: Parent widget
            airport_db: AirportDatabase instance
        """
        self.parent = parent
        self.airport_db = airport_db
        self.current_airport: Optional[AirportLayout] = None
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.selected_element = None
        
        # UI Layers visibility
        self.layers = {
            "runways": True,
            "taxiways": True,
            "gates": True,
            "hotspots": True
        }
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the map UI"""
        main_frame = ttk.Frame(self.parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(controls_frame, text="Airport:").pack(side=tk.LEFT, padx=(0, 5))
        self.airport_var = tk.StringVar()
        self.airport_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.airport_var,
            values=self.airport_db.get_all_airports(),
            state="readonly",
            width=20
        )
        self.airport_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.airport_combo.bind("<<ComboboxSelected>>", self.on_airport_change)
        
        # Layer toggles
        for layer in self.layers:
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(controls_frame, text=layer.capitalize(), variable=var,
                          command=lambda l=layer, v=var: self.toggle_layer(l, v)).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(controls_frame, text="Refresh", command=self.refresh_map).pack(side=tk.LEFT, padx=10)
        
        # Map canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", width=800, height=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        
        # Info frame
        self.info_text = tk.Text(main_frame, height=4, wrap=tk.WORD, font=("Arial", 9))
        self.info_text.pack(fill=tk.X, pady=(10, 0))
    
    def toggle_layer(self, layer, var):
        self.layers[layer] = var.get()
        self.refresh_map()

    def load_airport(self, icao: str):
        self.current_airport = self.airport_db.get_airport(icao)
        if self.current_airport:
            self.refresh_map()
    
    def on_airport_change(self, event=None):
        self.load_airport(self.airport_var.get())
    
    def refresh_map(self):
        if self.current_airport:
            self.draw_map()
    
    def draw_map(self):
        self.canvas.delete("all")
        
        # Simplified coordinate scaling (assuming input is already lat/lon or normalized)
        # In a real app, we'd project these lat/lon to canvas coords.
        # Keeping existing logic for consistency with current model
        self.draw_elements()
    
    def draw_elements(self):
        if self.layers["runways"]:
            for runway in self.current_airport.runways:
                self.draw_runway(runway)
        if self.layers["taxiways"]:
            for taxiway in self.current_airport.taxiways:
                self.draw_taxiway(taxiway)
        if self.layers["gates"]:
            for gate in self.current_airport.gates:
                self.draw_gate(gate)
        if self.layers["hotspots"]:
            for hotspot in self.current_airport.hotspots:
                self.draw_hotspot(hotspot)

    def draw_runway(self, runway: Runway):
        x1, y1 = self.world_to_screen(runway.start_point)
        x2, y2 = self.world_to_screen(runway.end_point)
        self.canvas.create_line(x1, y1, x2, y2, width=10, fill="gray", tags=("runway", runway.runway_id))
    
    def draw_taxiway(self, taxiway: Taxiway):
        x1, y1 = self.world_to_screen(taxiway.start_point)
        x2, y2 = self.world_to_screen(taxiway.end_point)
        self.canvas.create_line(x1, y1, x2, y2, width=4, fill="yellow", tags=("taxiway", taxiway.taxiway_id))

    def draw_gate(self, gate: Gate):
        x, y = self.world_to_screen(gate.location)
        self.canvas.create_rectangle(x-5, y-5, x+5, y+5, fill="blue", tags=("gate", gate.gate_id))

    def draw_hotspot(self, hotspot: HotSpot):
        x, y = self.world_to_screen(hotspot.location)
        self.canvas.create_oval(x-8, y-8, x+8, y+8, fill="red", tags=("hotspot", hotspot.hotspot_id))

    def world_to_screen(self, point: Tuple[float, float]) -> Tuple[int, int]:
        # Placeholder projection: map lat/lon to 800x600 canvas
        # Note: Proper Mercator projection would go here
        return (int(point[1] * 1000 + 400), int(point[0] * 1000 + 300))

    def on_click(self, event):
        items = self.canvas.find_closest(event.x, event.y)
        if items:
            tags = self.canvas.gettags(items[0])
            if tags:
                self.show_element_info(tags[0], tags[1])

    def on_zoom(self, event):
        self.scale *= 1.1 if event.delta > 0 else 0.9
        self.refresh_map()

    def show_element_info(self, element_type: str, element_id: str):
        # Implementation of show_element_info ...
        pass
    
    def animate_taxi_route(self, route_ids: List[str]):
        """Animates a path on the map."""
        # Simple animation: Highlight segments one by one
        for taxiway_id in route_ids:
            self.canvas.itemconfig(taxiway_id, fill="green", width=6)
            self.parent.update()
            time.sleep(0.5)
            self.canvas.itemconfig(taxiway_id, fill="yellow", width=4)
    
    def request_taxi_route(self, start_id: str, end_id: str):
        """Request and animate a taxi route"""
        if not self.current_airport:
            return
            
        route = self.current_airport.find_taxi_route(start_id, end_id)
        if route:
            self.animate_taxi_route(route)
        else:
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(tk.END, "No route found between those points.")
