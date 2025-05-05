"""
Aircraft Model
Represents an aircraft in the ATC system with relevant properties and state
"""
import time
from enum import Enum

class AircraftType(Enum):
    """Aircraft types with their wake turbulence categories"""
    # Light (L)
    C152 = ("Cessna 152", "L")
    C172 = ("Cessna 172", "L")
    PA28 = ("Piper Cherokee", "L")
    
    # Medium (M)
    B737 = ("Boeing 737", "M")
    A320 = ("Airbus A320", "M")
    E145 = ("Embraer 145", "M")
    CRJ2 = ("CRJ-200", "M")
    
    # Heavy (H)
    B747 = ("Boeing 747", "H")
    B777 = ("Boeing 777", "H")
    A330 = ("Airbus A330", "H")
    
    # Super (J)
    A380 = ("Airbus A380", "J")
    
    def __init__(self, display_name, wake_category):
        self.display_name = display_name
        self.wake_category = wake_category


class AircraftStatus(Enum):
    """Possible statuses for an aircraft"""
    # Ground statuses
    PARKED = "Parked at gate"
    PUSHBACK = "Pushing back"
    TAXIING = "Taxiing"
    HOLDING_SHORT = "Holding short"
    RUNWAY_LINEUP = "Lined up on runway"
    
    # Departure statuses
    TAKEOFF_ROLL = "Takeoff roll"
    DEPARTED = "Departed"
    CLIMB = "Climbing"
    
    # Approach/Arrival statuses
    APPROACH = "On approach"
    FINAL = "On final"
    LANDED = "Landed"
    LANDING_ROLL = "Landing roll"
    
    # Other statuses
    GO_AROUND = "Going around"
    HOLDING = "Holding"
    EMERGENCY = "Emergency"


class AircraftPosition(Enum):
    """Possible positions for an aircraft"""
    # Ground positions
    GATE = "Gate"
    RAMP = "Ramp"
    TAXIWAY = "Taxiway"
    RUNWAY = "Runway"
    
    # Airborne positions
    DEPARTURE = "Departure"
    TERMINAL = "Terminal Airspace"
    ARRIVAL = "Arrival"
    PATTERN = "Traffic Pattern"


class Aircraft:
    """Represents an aircraft in the ATC system"""
    def __init__(
        self, 
        callsign, 
        aircraft_type, 
        status=AircraftStatus.PARKED, 
        position=AircraftPosition.GATE,
        location_details="",
        altitude=0,
        heading=0,
        speed=0,
        squawk="1200",
        flight_rules="VFR",
        destination="",
        route=""
    ):
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
        
        # Track timing information
        self.status_changed_time = time.time()
        self.expected_ready_time = None
        
        # Track clearance information
        self.cleared_altitude = None
        self.cleared_heading = None
        self.cleared_speed = None
        self.cleared_approach = None
        self.cleared_runway = None
        
        # Track communication history
        self.comms_history = []
    
    def update_status(self, new_status):
        """Update the status of the aircraft"""
        self.status = new_status
        self.status_changed_time = time.time()
        
        # Log status change to comms history
        self.comms_history.append({
            "time": time.time(),
            "type": "status_change",
            "message": f"Status changed to {new_status.value}"
        })
    
    def update_position(self, new_position, location_details=""):
        """Update the position of the aircraft"""
        self.position = new_position
        
        if location_details:
            self.location_details = location_details
        
        # Log position change to comms history
        self.comms_history.append({
            "time": time.time(),
            "type": "position_change",
            "message": f"Position changed to {new_position.value} - {self.location_details}"
        })
    
    def issue_clearance(self, clearance_type, value):
        """Issue a clearance to the aircraft"""
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
        
        # Log clearance to comms history
        self.comms_history.append({
            "time": time.time(),
            "type": "clearance",
            "message": f"Cleared {clearance_type}: {value}"
        })
    
    def add_communication(self, message, sender="ATC"):
        """Add a communication with this aircraft"""
        self.comms_history.append({
            "time": time.time(),
            "type": "communication",
            "sender": sender,
            "message": message
        })
    
    def get_status_duration(self):
        """Get the duration in the current status"""
        return time.time() - self.status_changed_time
    
    def get_wake_category(self):
        """Get the wake turbulence category of the aircraft"""
        return self.aircraft_type.wake_category
    
    def get_display_string(self):
        """Get a string representation for display in lists"""
        if self.position == AircraftPosition.GATE:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.status.value}"
        elif self.position == AircraftPosition.TAXIWAY:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.status.value}"
        elif self.position == AircraftPosition.RUNWAY:
            return f"{self.callsign} - {self.aircraft_type.display_name} - Runway {self.location_details} - {self.status.value}"
        elif self.position == AircraftPosition.PATTERN:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.status.value} - Runway {self.location_details}"
        elif self.position == AircraftPosition.ARRIVAL:
            if self.altitude > 0:
                return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details} - {self.altitude}ft"
            else:
                return f"{self.callsign} - {self.aircraft_type.display_name} - {self.location_details}"
        else:
            return f"{self.callsign} - {self.aircraft_type.display_name} - {self.status.value}" 