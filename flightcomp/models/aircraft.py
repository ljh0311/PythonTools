"""
Live aircraft model: stateful aircraft with wake category, clearances, and comms history.
Use for UI and rich state; for serializable ATC records use models.atc_model.Aircraft.
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional


class AircraftType(Enum):
    """Aircraft types with display name and wake turbulence category (L/M/H/J)."""

    C152 = ("Cessna 152", "L")
    C172 = ("Cessna 172", "L")
    PA28 = ("Piper Cherokee", "L")
    B737 = ("Boeing 737", "M")
    A320 = ("Airbus A320", "M")
    E145 = ("Embraer 145", "M")
    CRJ2 = ("CRJ-200", "M")
    B747 = ("Boeing 747", "H")
    B777 = ("Boeing 777", "H")
    A330 = ("Airbus A330", "H")
    A380 = ("Airbus A380", "J")

    def __init__(self, display_name: str, wake_category: str) -> None:
        self.display_name = display_name
        self.wake_category = wake_category


class AircraftStatus(Enum):
    """Possible statuses for an aircraft (ground, departure, approach, etc.)."""

    PARKED = "Parked at gate"
    PUSHBACK = "Pushing back"
    TAXIING = "Taxiing"
    HOLDING_SHORT = "Holding short"
    RUNWAY_LINEUP = "Lined up on runway"
    TAKEOFF_ROLL = "Takeoff roll"
    DEPARTED = "Departed"
    CLIMB = "Climbing"
    APPROACH = "On approach"
    FINAL = "On final"
    LANDED = "Landed"
    LANDING_ROLL = "Landing roll"
    GO_AROUND = "Going around"
    HOLDING = "Holding"
    EMERGENCY = "Emergency"


class AircraftPosition(Enum):
    """Possible positions for an aircraft (gate, taxiway, runway, airspace)."""

    GATE = "Gate"
    RAMP = "Ramp"
    TAXIWAY = "Taxiway"
    RUNWAY = "Runway"
    DEPARTURE = "Departure"
    TERMINAL = "Terminal Airspace"
    ARRIVAL = "Arrival"
    PATTERN = "Traffic Pattern"


class LiveAircraft:
    """
    Stateful aircraft model for UI: wake category, clearances, comms history.
    For serializable ATC records use models.atc_model.Aircraft.
    """

    def __init__(
        self,
        callsign: str,
        aircraft_type: AircraftType,
        status: AircraftStatus = AircraftStatus.PARKED,
        position: AircraftPosition = AircraftPosition.GATE,
        location_details: str = "",
        altitude: int = 0,
        heading: int = 0,
        speed: int = 0,
        squawk: str = "1200",
        flight_rules: str = "VFR",
        destination: str = "",
        route: str = "",
    ) -> None:
        self.callsign = callsign
        self.aircraft_type = aircraft_type
        self.status = status
        self.position = position
        self.location_details = location_details
        self.altitude = altitude
        self.heading = heading
        self.speed = speed
        self.squawk = squawk
        self.flight_rules = flight_rules
        self.destination = destination
        self.route = route
        self.status_changed_time: float = time.time()
        self.expected_ready_time: Optional[float] = None
        self.cleared_altitude: Optional[Any] = None
        self.cleared_heading: Optional[Any] = None
        self.cleared_speed: Optional[Any] = None
        self.cleared_approach: Optional[Any] = None
        self.cleared_runway: Optional[Any] = None
        self.comms_history: List[Dict[str, Any]] = []

    def update_status(self, new_status: AircraftStatus) -> None:
        """Update status and log the change in comms history."""
        self.status = new_status
        self.status_changed_time = time.time()
        self.comms_history.append({
            "time": time.time(),
            "type": "status_change",
            "message": f"Status changed to {new_status.value}",
        })

    def update_position(self, new_position: AircraftPosition, location_details: str = "") -> None:
        """Update position and optionally location details; log in comms history."""
        self.position = new_position
        if location_details:
            self.location_details = location_details
        self.comms_history.append({
            "time": time.time(),
            "type": "position_change",
            "message": f"Position changed to {new_position.value} - {self.location_details}",
        })

    def issue_clearance(self, clearance_type: str, value: Any) -> None:
        """Set a clearance (altitude, heading, speed, approach, runway) and log it."""
        if clearance_type == "altitude":
            self.cleared_altitude = value
        elif clearance_type == "heading":
            self.cleared_heading = value
        elif clearance_type == "speed":
            self.cleared_speed = value
        elif clearance_type == "approach":
            self.cleared_approach = value
        elif clearance_type == "runway":
            self.cleared_runway = value
        self.comms_history.append({
            "time": time.time(),
            "type": "clearance",
            "message": f"Cleared {clearance_type}: {value}",
        })

    def add_communication(self, message: str, sender: str = "ATC") -> None:
        """Append a communication to comms history."""
        self.comms_history.append({
            "time": time.time(),
            "type": "communication",
            "sender": sender,
            "message": message,
        })

    def get_status_duration(self) -> float:
        """Return seconds in the current status."""
        return time.time() - self.status_changed_time

    def get_wake_category(self) -> str:
        """Return the wake turbulence category (L/M/H/J) of the aircraft type."""
        return self.aircraft_type.wake_category

    def get_display_string(self) -> str:
        """Return a string for display in lists (callsign, type, location, status/altitude)."""
        if self.position == AircraftPosition.GATE:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.status.value}"
        if self.position == AircraftPosition.TAXIWAY:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.status.value}"
        if self.position == AircraftPosition.RUNWAY:
            return f"{self.callsign} - {self.aircraft_type.display_name} - Runway {self.location_details} - {self.status.value}"
        if self.position == AircraftPosition.PATTERN:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.status.value} - Runway {self.location_details}"
        if self.position == AircraftPosition.ARRIVAL:
            if self.altitude > 0:
                return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.altitude}ft"
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details}"
        return f"{self.callsign} - {self.aircraft_type.display_name} - {self.status.value}"
