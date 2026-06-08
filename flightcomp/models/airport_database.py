"""
Enhanced Airport Database: layouts, runways, taxiways, gates, hotspots, procedures.
Loads/saves airport_info.json; from_dict methods validate required keys.
"""

import json
import os
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


def _require_keys(data: Dict[str, Any], keys: List[str], context: str = "dict") -> None:
    """Raise ValueError if any required key is missing."""
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"{context} missing required field(s): {', '.join(missing)}")


class HotSpotType(Enum):
    """Types of airport hot spots"""
    TAXIWAY_INTERSECTION = "taxiway_intersection"
    RUNWAY_CROSSING = "runway_crossing"
    GATE_AREA = "gate_area"
    HOLD_SHORT = "hold_short"
    CONSTRUCTION = "construction"
    RESTRICTED_AREA = "restricted_area"


@dataclass
class HotSpot:
    """Represents an airport hot spot"""
    hotspot_id: str
    name: str
    hotspot_type: HotSpotType
    location: Tuple[float, float]  # (x, y) coordinates
    description: str
    procedures: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hotspot_id": self.hotspot_id,
            "name": self.name,
            "hotspot_type": self.hotspot_type.value,
            "location": list(self.location),
            "description": self.description,
            "procedures": self.procedures,
            "restrictions": self.restrictions
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "HotSpot":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["hotspot_id", "name", "hotspot_type", "location", "description"], "HotSpot")
        return HotSpot(
            hotspot_id=data["hotspot_id"],
            name=data["name"],
            hotspot_type=HotSpotType(data["hotspot_type"]),
            location=tuple(data["location"]),
            description=data["description"],
            procedures=data.get("procedures", []),
            restrictions=data.get("restrictions", [])
        )


@dataclass
class Taxiway:
    """Represents a taxiway"""
    taxiway_id: str
    name: str
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    width: float = 25.0  # meters
    restrictions: List[str] = field(default_factory=list)
    connects_to: List[str] = field(default_factory=list)  # Other taxiway/runway IDs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "taxiway_id": self.taxiway_id,
            "name": self.name,
            "start_point": list(self.start_point),
            "end_point": list(self.end_point),
            "width": self.width,
            "restrictions": self.restrictions,
            "connects_to": self.connects_to
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Taxiway":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["taxiway_id", "name", "start_point", "end_point"], "Taxiway")
        return Taxiway(
            taxiway_id=data["taxiway_id"],
            name=data["name"],
            start_point=tuple(data["start_point"]),
            end_point=tuple(data["end_point"]),
            width=data.get("width", 25.0),
            restrictions=data.get("restrictions", []),
            connects_to=data.get("connects_to", [])
        )


@dataclass
class Runway:
    """Represents a runway"""
    runway_id: str
    designation: str  # e.g., "02L", "27R"
    start_point: Tuple[float, float]
    end_point: Tuple[float, float]
    length: float  # meters
    width: float = 45.0  # meters
    surface: str = "concrete"
    ils_available: bool = False
    ils_frequency: Optional[str] = None
    restrictions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "runway_id": self.runway_id,
            "designation": self.designation,
            "start_point": list(self.start_point),
            "end_point": list(self.end_point),
            "length": self.length,
            "width": self.width,
            "surface": self.surface,
            "ils_available": self.ils_available,
            "ils_frequency": self.ils_frequency,
            "restrictions": self.restrictions
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Runway":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["runway_id", "designation", "start_point", "end_point", "length"], "Runway")
        return Runway(
            runway_id=data["runway_id"],
            designation=data["designation"],
            start_point=tuple(data["start_point"]),
            end_point=tuple(data["end_point"]),
            length=data["length"],
            width=data.get("width", 45.0),
            surface=data.get("surface", "concrete"),
            ils_available=data.get("ils_available", False),
            ils_frequency=data.get("ils_frequency"),
            restrictions=data.get("restrictions", [])
        )


@dataclass
class Gate:
    """Represents an aircraft gate"""
    gate_id: str
    gate_number: str
    location: Tuple[float, float]
    aircraft_types: List[str] = field(default_factory=list)
    taxiway_access: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "gate_id": self.gate_id,
            "gate_number": self.gate_number,
            "location": list(self.location),
            "aircraft_types": self.aircraft_types,
            "taxiway_access": self.taxiway_access
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Gate":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["gate_id", "gate_number", "location"], "Gate")
        return Gate(
            gate_id=data["gate_id"],
            gate_number=data["gate_number"],
            location=tuple(data["location"]),
            aircraft_types=data.get("aircraft_types", []),
            taxiway_access=data.get("taxiway_access", [])
        )


@dataclass
class AirportProcedure:
    """Represents an airport-specific procedure"""
    procedure_id: str
    name: str
    procedure_type: str  # e.g., "departure", "arrival", "taxi"
    description: str
    steps: List[str] = field(default_factory=list)
    applicable_runways: List[str] = field(default_factory=list)
    restrictions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "procedure_id": self.procedure_id,
            "name": self.name,
            "procedure_type": self.procedure_type,
            "description": self.description,
            "steps": self.steps,
            "applicable_runways": self.applicable_runways,
            "restrictions": self.restrictions
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AirportProcedure":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["procedure_id", "name", "procedure_type", "description"], "AirportProcedure")
        return AirportProcedure(
            procedure_id=data["procedure_id"],
            name=data["name"],
            procedure_type=data["procedure_type"],
            description=data["description"],
            steps=data.get("steps", []),
            applicable_runways=data.get("applicable_runways", []),
            restrictions=data.get("restrictions", [])
        )


@dataclass
class AirportLayout:
    """Complete airport layout information"""
    airport_icao: str
    airport_name: str
    runways: List[Runway] = field(default_factory=list)
    taxiways: List[Taxiway] = field(default_factory=list)
    gates: List[Gate] = field(default_factory=list)
    hotspots: List[HotSpot] = field(default_factory=list)
    procedures: List[AirportProcedure] = field(default_factory=list)
    chart_path: Optional[str] = None  # Path to airport chart image/PDF
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "airport_icao": self.airport_icao,
            "airport_name": self.airport_name,
            "runways": [r.to_dict() for r in self.runways],
            "taxiways": [t.to_dict() for t in self.taxiways],
            "gates": [g.to_dict() for g in self.gates],
            "hotspots": [h.to_dict() for h in self.hotspots],
            "procedures": [p.to_dict() for p in self.procedures],
            "chart_path": self.chart_path,
            "metadata": self.metadata
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AirportLayout":
        """Create from dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data, ["airport_icao", "airport_name"], "AirportLayout")
        return AirportLayout(
            airport_icao=data["airport_icao"],
            airport_name=data["airport_name"],
            runways=[Runway.from_dict(r) for r in data.get("runways", [])],
            taxiways=[Taxiway.from_dict(t) for t in data.get("taxiways", [])],
            gates=[Gate.from_dict(g) for g in data.get("gates", [])],
            hotspots=[HotSpot.from_dict(h) for h in data.get("hotspots", [])],
            procedures=[AirportProcedure.from_dict(p) for p in data.get("procedures", [])],
            chart_path=data.get("chart_path"),
            metadata=data.get("metadata", {})
        )
    
    def get_taxiway_by_name(self, name: str) -> Optional[Taxiway]:
        """Get taxiway by name"""
        for taxiway in self.taxiways:
            if taxiway.name == name:
                return taxiway
        return None
    
    def get_runway_by_designation(self, designation: str) -> Optional[Runway]:
        """Get runway by designation"""
        for runway in self.runways:
            if runway.designation == designation:
                return runway
        return None
    
    def get_hotspots_near_location(self, location: Tuple[float, float], radius: float = 50.0) -> List[HotSpot]:
        """Get hotspots near a location"""
        nearby = []
        for hotspot in self.hotspots:
            dx = hotspot.location[0] - location[0]
            dy = hotspot.location[1] - location[1]
            distance = (dx**2 + dy**2)**0.5
            if distance <= radius:
                nearby.append(hotspot)
        return nearby
    
    def find_taxi_route(self, start: str, end: str) -> Optional[List[str]]:
        """
        Find taxi route between two points
        
        Args:
            start: Starting taxiway/gate ID
            end: Ending taxiway/gate ID
        
        Returns:
            List of taxiway IDs forming the route, or None if no route found
        """
        # Simple BFS pathfinding
        queue = [(start, [start])]
        visited = {start}
        
        while queue:
            current, path = queue.pop(0)
            
            if current == end:
                return path
            
            # Find connections
            connections = []
            for taxiway in self.taxiways:
                if taxiway.taxiway_id == current:
                    connections.extend(taxiway.connects_to)
            
            for connection in connections:
                if connection not in visited:
                    visited.add(connection)
                    queue.append((connection, path + [connection]))
        
        return None


class AirportDatabase:
    """Database of airport layouts and information"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize airport database
        
        Args:
            data_dir: Directory containing airport data. Defaults to data/airports/
        """
        if data_dir is None:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(current_dir, "data", "airports")
        
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.airports: Dict[str, AirportLayout] = {}
        self._load_airports()
    
    def _load_airports(self) -> None:
        """Load airport data from airport_info.json in data_dir."""
        airport_info_file = os.path.join(self.data_dir, "airport_info.json")
        if os.path.exists(airport_info_file):
            with open(airport_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                airports_list = data.get("airports", [])
                for airport_data in airports_list:
                    layout = AirportLayout.from_dict(airport_data)
                    self.airports[layout.airport_icao] = layout
    
    def get_airport(self, icao: str) -> Optional[AirportLayout]:
        """Get airport layout by ICAO code"""
        return self.airports.get(icao.upper())
    
    def add_airport(self, layout: AirportLayout) -> None:
        """Add or update airport layout by ICAO."""
        self.airports[layout.airport_icao.upper()] = layout

    def save_airport(self, icao: str) -> None:
        """Save airport data to airport_info.json; no-op if ICAO not in database."""
        airport = self.airports.get(icao.upper())
        if not airport:
            return
        
        airport_info_file = os.path.join(self.data_dir, "airport_info.json")
        
        # Load existing data
        airports_list = []
        if os.path.exists(airport_info_file):
            with open(airport_info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                airports_list = data.get("airports", [])
        
        # Update or add airport
        updated = False
        for i, ap_data in enumerate(airports_list):
            if ap_data["airport_icao"] == icao.upper():
                airports_list[i] = airport.to_dict()
                updated = True
                break
        
        if not updated:
            airports_list.append(airport.to_dict())
        
        # Save
        with open(airport_info_file, 'w', encoding='utf-8') as f:
            json.dump({"airports": airports_list}, f, indent=2, ensure_ascii=False)
    
    def get_all_airports(self) -> List[str]:
        """Get list of all airport ICAO codes"""
        return list(self.airports.keys())

