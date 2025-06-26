import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class AirportConfiguration:
    """Class representing an airport configuration"""
    icao: str
    name: str
    runways: List[str]
    taxiways: List[str]
    gates: List[str]
    wind: str = "Calm"
    visibility: str = "10 miles"
    ceiling: str = "Clear"
    runway_instructions: List[str] = field(default_factory=list)
    
    def get_full_name(self):
        """Get the full name of the airport (ICAO - Name)"""
        return f"{self.icao} - {self.name}"
    
    @staticmethod
    def from_dict(data_dict):
        """Create an AirportConfiguration from a dictionary"""
        return AirportConfiguration(
            icao=data_dict["icao"],
            name=data_dict["name"],
            runways=data_dict["runways"],
            taxiways=data_dict["taxiways"],
            gates=data_dict["gates"],
            wind=data_dict.get("wind", "Calm"),
            visibility=data_dict.get("visibility", "10 miles"),
            ceiling=data_dict.get("ceiling", "Clear"),
            runway_instructions=data_dict.get("runway_instructions", [])
        )
    
    def to_dict(self):
        """Convert the airport configuration to a dictionary for saving"""
        return {
            "icao": self.icao,
            "name": self.name,
            "runways": self.runways,
            "taxiways": self.taxiways,
            "gates": self.gates,
            "wind": self.wind,
            "visibility": self.visibility,
            "ceiling": self.ceiling,
            "runway_instructions": self.runway_instructions
        }

@dataclass
class Aircraft:
    """Class representing an aircraft in the ATC system"""
    callsign: str
    aircraft_type: str
    location: str = "Ramp"
    status: str = "Parked"
    cleared_to: str = ""
    squawk_code: str = "1200"
    remarks: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    communication_history: List[str] = field(default_factory=list)
    
    def add_communication(self, message: str):
        """Add a communication message to the aircraft's history"""
        self.communication_history.append(message)
    
    def update_status(self, new_status: str):
        """Update the aircraft's status"""
        self.status = new_status
    
    def update_location(self, new_location: str):
        """Update the aircraft's location"""
        self.location = new_location
    
    def to_dict(self):
        """Convert the aircraft to a dictionary for saving"""
        return {
            "callsign": self.callsign,
            "aircraft_type": self.aircraft_type,
            "location": self.location,
            "status": self.status,
            "cleared_to": self.cleared_to,
            "squawk_code": self.squawk_code,
            "remarks": self.remarks,
            "id": self.id,
            "communication_history": self.communication_history
        }
    
    @staticmethod
    def from_dict(data_dict):
        """Create an Aircraft from a dictionary"""
        aircraft = Aircraft(
            callsign=data_dict["callsign"],
            aircraft_type=data_dict["aircraft_type"]
        )
        aircraft.location = data_dict.get("location", "Ramp")
        aircraft.status = data_dict.get("status", "Parked")
        aircraft.cleared_to = data_dict.get("cleared_to", "")
        aircraft.squawk_code = data_dict.get("squawk_code", "1200")
        aircraft.remarks = data_dict.get("remarks", "")
        aircraft.id = data_dict.get("id", str(uuid.uuid4()))
        aircraft.communication_history = data_dict.get("communication_history", [])
        return aircraft
    
    def __str__(self):
        return f"{self.callsign} - {self.aircraft_type} - {self.location} - {self.status}"


@dataclass
class ATCModel:
    """Main model class for the ATC system"""
    aircraft_list: Dict[str, Aircraft] = field(default_factory=dict)
    airports: Dict[str, AirportConfiguration] = field(default_factory=dict)
    current_airport: Optional[str] = None
    
    def __post_init__(self):
        """Initialize with default airports if none are provided"""
        if not self.airports:
            self._initialize_default_airports()
        
        if not self.current_airport and self.airports:
            self.current_airport = next(iter(self.airports.keys()))
    
    def _initialize_default_airports(self):
        """Initialize with default airport configurations"""
        # Add default airports
        default_airports = [
            AirportConfiguration(
                icao="WSSS",
                name="Singapore Changi Airport",
                runways=["02L/20R", "02C/20C", "02R/20L"],
                taxiways=["A", "B", "C", "D", "E", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "W"],
                gates=["A1-A20", "B1-B20", "C1-C30", "D1-D40", "E1-E10", "F1-F10"],
                wind="220° at 10kts",
                visibility="9999",
                ceiling="FEW040"
            ),
            AirportConfiguration(
                icao="WBGG",
                name="Kuching International Airport",
                runways=["07/25"],
                taxiways=["A", "B", "C", "F", "G", "J", "K"],
                gates=["1", "2", "3", "4", "5", "5R", "6", "7", "7R", "8", "8L", "8R", "9", "R1", "R2", "R3", "G1", "G2", "G3", "H1", "H2", "H3"],
                wind="040° at 8kts",
                visibility="8000",
                ceiling="SCT025"
            ),
            AirportConfiguration(
                icao="WSSL",
                name="Singapore Seletar Airport",
                runways=["03/21"],
                taxiways=["A", "B", "C", "E", "J"],
                gates=["A1-A5", "B1-B5"],
                wind="030° at 6kts",
                visibility="9999",
                ceiling="NSC"
            )
        ]
        
        # Add them to the airports dictionary
        for airport in default_airports:
            self.add_airport(airport)
        
        # Add specific instructions after initialization
        if "WBGG - Kuching International Airport" in self.airports:
            self.airports["WBGG - Kuching International Airport"].runway_instructions = [
                "No wide body aircraft allowed to park at bay 8 and 9 when bay 8L is occupied.",
                "Pilots to follow marshaller instructions at all stands."
            ]
    
    def add_airport(self, airport: AirportConfiguration):
        """Add an airport to the system"""
        full_name = airport.get_full_name()
        self.airports[full_name] = airport
    
    def remove_airport(self, airport_name: str):
        """Remove an airport from the system"""
        if airport_name in self.airports:
            del self.airports[airport_name]
            
            # If we removed the current airport, set a new one if any left
            if airport_name == self.current_airport and self.airports:
                self.current_airport = next(iter(self.airports.keys()))
            elif not self.airports:
                self.current_airport = None
    
    def change_current_airport(self, airport_name: str):
        """Change the current airport"""
        if airport_name in self.airports:
            self.current_airport = airport_name
            return True
        return False
    
    def get_current_airport(self) -> Optional[AirportConfiguration]:
        """Get the current airport configuration"""
        if self.current_airport and self.current_airport in self.airports:
            return self.airports[self.current_airport]
        return None
    
    def add_aircraft(self, aircraft: Aircraft):
        """Add an aircraft to the system"""
        self.aircraft_list[aircraft.id] = aircraft
    
    def remove_aircraft(self, aircraft_id: str):
        """Remove an aircraft from the system"""
        if aircraft_id in self.aircraft_list:
            del self.aircraft_list[aircraft_id]
    
    def update_aircraft(self, aircraft_id: str, **kwargs):
        """Update an aircraft's attributes"""
        if aircraft_id in self.aircraft_list:
            aircraft = self.aircraft_list[aircraft_id]
            for key, value in kwargs.items():
                if hasattr(aircraft, key):
                    setattr(aircraft, key, value)
    
    def get_aircraft(self, aircraft_id: str) -> Optional[Aircraft]:
        """Get an aircraft by ID"""
        return self.aircraft_list.get(aircraft_id)
    
    def get_all_aircraft(self) -> List[Aircraft]:
        """Get all aircraft in the system"""
        return list(self.aircraft_list.values())
    
    def to_dict(self):
        """Convert the model to a dictionary for saving"""
        return {
            "aircraft": {aircraft_id: aircraft.to_dict() for aircraft_id, aircraft in self.aircraft_list.items()},
            "airports": {name: airport.to_dict() for name, airport in self.airports.items()},
            "current_airport": self.current_airport
        }
    
    @staticmethod
    def from_dict(data_dict):
        """Create an ATCModel from a dictionary"""
        model = ATCModel()
        
        # Load airports
        airports_dict = data_dict.get("airports", {})
        for name, airport_data in airports_dict.items():
            airport = AirportConfiguration.from_dict(airport_data)
            model.airports[name] = airport
        
        # Load aircraft
        aircraft_dict = data_dict.get("aircraft", {})
        for aircraft_id, aircraft_data in aircraft_dict.items():
            aircraft = Aircraft.from_dict(aircraft_data)
            model.aircraft_list[aircraft_id] = aircraft
        
        # Set current airport
        model.current_airport = data_dict.get("current_airport")
        
        return model 