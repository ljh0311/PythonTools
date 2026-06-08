"""
Interactive Airport Map
Displays airport layout with taxiways, runways, and aircraft positions
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List, Tuple, Any
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
        
        ttk.Button(
            controls_frame,
            text="Refresh",
            command=self.refresh_map
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            controls_frame,
            text="Reset View",
            command=self.reset_view
        ).pack(side=tk.LEFT)
        
        # Map canvas
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        self.canvas = tk.Canvas(
            canvas_frame,
            bg="white",
            width=800,
            height=600
        )
        
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        
        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Map Information", padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.info_text = tk.Text(info_frame, height=4, wrap=tk.WORD, font=("Arial", 9))
        self.info_text.pack(fill=tk.X)
    
    def load_airport(self, icao: str):
        """Load airport layout"""
        self.current_airport = self.airport_db.get_airport(icao)
        if self.current_airport:
            self.airport_var.set(icao)
            self.draw_map()
    
    def on_airport_change(self, event=None):
        """Handle airport selection change"""
        icao = self.airport_var.get()
        if icao:
            self.load_airport(icao)
    
    def refresh_map(self):
        """Refresh the map display"""
        if self.current_airport:
            self.draw_map()
    
    def reset_view(self):
        """Reset map view to default"""
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        if self.current_airport:
            self.draw_map()
    
    def draw_map(self):
        """Draw the airport map"""
        if not self.current_airport:
            return
        
        self.canvas.delete("all")
        
        # Calculate bounds
        all_points = []
        for runway in self.current_airport.runways:
            all_points.extend([runway.start_point, runway.end_point])
        for taxiway in self.current_airport.taxiways:
            all_points.extend([taxiway.start_point, taxiway.end_point])
        for gate in self.current_airport.gates:
            all_points.append(gate.location)
        
        if not all_points:
            self.canvas.create_text(
                400, 300,
                text="No airport layout data available",
                font=("Arial", 12)
            )
            return
        
        # Calculate scale to fit
        min_x = min(p[0] for p in all_points)
        max_x = max(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        max_y = max(p[1] for p in all_points)
        
        width = max_x - min_x if max_x > min_x else 1000
        height = max_y - min_y if max_y > min_y else 1000
        
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 600
        
        scale_x = (canvas_width - 100) / width if width > 0 else 1
        scale_y = (canvas_height - 100) / height if height > 0 else 1
        self.scale = min(scale_x, scale_y) * 0.8
        
        # Center offset
        self.offset_x = (canvas_width - (width * self.scale)) / 2 - (min_x * self.scale)
        self.offset_y = (canvas_height - (height * self.scale)) / 2 - (min_y * self.scale)
        
        # Draw runways
        for runway in self.current_airport.runways:
            self.draw_runway(runway)
        
        # Draw taxiways
        for taxiway in self.current_airport.taxiways:
            self.draw_taxiway(taxiway)
        
        # Draw gates
        for gate in self.current_airport.gates:
            self.draw_gate(gate)
        
        # Draw hotspots
        for hotspot in self.current_airport.hotspots:
            self.draw_hotspot(hotspot)
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def draw_runway(self, runway: Runway):
        """Draw a runway on the map"""
        x1, y1 = self.world_to_screen(runway.start_point)
        x2, y2 = self.world_to_screen(runway.end_point)
        
        # Draw runway (thicker line)
        self.canvas.create_line(
            x1, y1, x2, y2,
            width=int(runway.width * self.scale / 10),
            fill="gray",
            tags=("runway", runway.runway_id)
        )
        
        # Draw runway designation
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.create_text(
            mid_x, mid_y,
            text=runway.designation,
            font=("Arial", 10, "bold"),
            fill="black",
            tags=("runway_label", runway.runway_id)
        )
    
    def draw_taxiway(self, taxiway: Taxiway):
        """Draw a taxiway on the map"""
        x1, y1 = self.world_to_screen(taxiway.start_point)
        x2, y2 = self.world_to_screen(taxiway.end_point)
        
        # Draw taxiway (thinner line)
        self.canvas.create_line(
            x1, y1, x2, y2,
            width=int(taxiway.width * self.scale / 20),
            fill="yellow",
            tags=("taxiway", taxiway.taxiway_id)
        )
        
        # Draw taxiway name
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        self.canvas.create_text(
            mid_x, mid_y,
            text=f"TW {taxiway.name}",
            font=("Arial", 8),
            fill="black",
            tags=("taxiway_label", taxiway.taxiway_id)
        )
    
    def draw_gate(self, gate: Gate):
        """Draw a gate on the map"""
        x, y = self.world_to_screen(gate.location)
        size = 10
        
        # Draw gate (square)
        self.canvas.create_rectangle(
            x - size, y - size, x + size, y + size,
            fill="blue",
            outline="black",
            tags=("gate", gate.gate_id)
        )
        
        # Draw gate label
        self.canvas.create_text(
            x, y - size - 5,
            text=gate.gate_number,
            font=("Arial", 7),
            fill="black",
            tags=("gate_label", gate.gate_id)
        )
    
    def draw_hotspot(self, hotspot: HotSpot):
        """Draw a hotspot on the map"""
        x, y = self.world_to_screen(hotspot.location)
        size = 15
        
        # Draw hotspot (red circle)
        self.canvas.create_oval(
            x - size, y - size, x + size, y + size,
            fill="red",
            outline="darkred",
            width=2,
            tags=("hotspot", hotspot.hotspot_id)
        )
        
        # Draw hotspot label
        self.canvas.create_text(
            x, y + size + 10,
            text=hotspot.name,
            font=("Arial", 7, "bold"),
            fill="red",
            tags=("hotspot_label", hotspot.hotspot_id)
        )
    
    def world_to_screen(self, point: Tuple[float, float]) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates"""
        x = int(point[0] * self.scale + self.offset_x)
        y = int(point[1] * self.scale + self.offset_y)
        return (x, y)
    
    def on_click(self, event):
        """Handle mouse click on map"""
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Find clicked element
        items = self.canvas.find_closest(x, y)
        if items:
            item_id = items[0]
            tags = self.canvas.gettags(item_id)
            
            if tags:
                element_type = tags[0]
                element_id = tags[1] if len(tags) > 1 else None
                
                if element_id:
                    self.selected_element = (element_type, element_id)
                    self.show_element_info(element_type, element_id)
    
    def on_drag(self, event):
        """Handle mouse drag"""
        # Pan the map
        pass
    
    def on_release(self, event):
        """Handle mouse release"""
        pass
    
    def on_zoom(self, event):
        """Handle mouse wheel zoom"""
        # Zoom in/out
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale *= 0.9
        
        if self.current_airport:
            self.draw_map()
    
    def show_element_info(self, element_type: str, element_id: str):
        """Show information about selected element"""
        if not self.current_airport:
            return
        
        info = ""
        
        if element_type == "runway":
            runway = self.current_airport.get_runway_by_designation(element_id.split("_")[-1])
            if runway:
                info = f"""Runway: {runway.designation}
Length: {runway.length}m
Width: {runway.width}m
Surface: {runway.surface}
ILS: {'Available' if runway.ils_available else 'Not available'}
ILS Frequency: {runway.ils_frequency or 'N/A'}"""
        
        elif element_type == "taxiway":
            taxiway = self.current_airport.get_taxiway_by_name(element_id.split("_")[-1])
            if taxiway:
                info = f"""Taxiway: {taxiway.name}
Width: {taxiway.width}m
Connects to: {', '.join(taxiway.connects_to)}"""
        
        elif element_type == "gate":
            gate = next((g for g in self.current_airport.gates if g.gate_id == element_id), None)
            if gate:
                info = f"""Gate: {gate.gate_number}
Aircraft Types: {', '.join(gate.aircraft_types) if gate.aircraft_types else 'All'}
Taxiway Access: {', '.join(gate.taxiway_access)}"""
        
        elif element_type == "hotspot":
            hotspot = next((h for h in self.current_airport.hotspots if h.hotspot_id == element_id), None)
            if hotspot:
                info = f"""Hotspot: {hotspot.name}
Type: {hotspot.hotspot_type.value}
Description: {hotspot.description}
Procedures: {', '.join(hotspot.procedures)}"""
        
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, info)

