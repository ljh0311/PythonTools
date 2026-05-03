"""
ATC model: airport configurations, aircraft records, and the main ATC state model.
Used for serialization and in-memory ATC state (e.g. by main.py when loading the ATC window).
"""

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _require_keys(data: Dict[str, Any], keys: List[str], context: str = "dict") -> None:
    """Raise ValueError if any required key is missing from data."""
    missing = [k for k in keys if k not in data]
    if missing:
        raise ValueError(f"{context} missing required field(s): {', '.join(missing)}")


@dataclass
class AirportConfiguration:
    """Airport configuration: ICAO, name, runways, taxiways, gates, and weather defaults."""

    icao: str
    name: str
    runways: List[str]
    taxiways: List[str]
    gates: List[str]
    wind: str = "Calm"
    visibility: str = "10 miles"
    ceiling: str = "Clear"
    runway_instructions: List[str] = field(default_factory=list)

    def get_full_name(self) -> str:
        """Return the full display name (ICAO - Name)."""
        return f"{self.icao} - {self.name}"

    @staticmethod
    def from_dict(data_dict: Dict[str, Any]) -> "AirportConfiguration":
        """Create an AirportConfiguration from a dictionary. Raises ValueError if required keys are missing."""
        _require_keys(data_dict, ["icao", "name", "runways", "taxiways", "gates"], "AirportConfiguration")
        return AirportConfiguration(
            icao=data_dict["icao"],
            name=data_dict["name"],
            runways=data_dict["runways"],
            taxiways=data_dict["taxiways"],
            gates=data_dict["gates"],
            wind=data_dict.get("wind", "Calm"),
            visibility=data_dict.get("visibility", "10 miles"),
            ceiling=data_dict.get("ceiling", "Clear"),
            runway_instructions=data_dict.get("runway_instructions", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for saving."""
        return {
            "icao": self.icao,
            "name": self.name,
            "runways": self.runways,
            "taxiways": self.taxiways,
            "gates": self.gates,
            "wind": self.wind,
            "visibility": self.visibility,
            "ceiling": self.ceiling,
            "runway_instructions": self.runway_instructions,
        }


@dataclass
class Aircraft:
    """Serializable aircraft record for the ATC system (callsign, type, location, status, comms)."""

    callsign: str
    aircraft_type: str
    location: str = "Ramp"
    status: str = "Parked"
    cleared_to: str = ""
    squawk_code: str = "1200"
    remarks: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    communication_history: List[str] = field(default_factory=list)

    def add_communication(self, message: str) -> None:
        """Append a message to the aircraft's communication history."""
        self.communication_history.append(message)

    def update_status(self, new_status: str) -> None:
        """Update the aircraft's status."""
        self.status = new_status

    def update_location(self, new_location: str) -> None:
        """Update the aircraft's location."""
        self.location = new_location

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a dictionary for saving."""
        return {
            "callsign": self.callsign,
            "aircraft_type": self.aircraft_type,
            "location": self.location,
            "status": self.status,
            "cleared_to": self.cleared_to,
            "squawk_code": self.squawk_code,
            "remarks": self.remarks,
            "id": self.id,
            "communication_history": self.communication_history,
        }

    @staticmethod
    def from_dict(data_dict: Dict[str, Any]) -> "Aircraft":
        """Create an Aircraft from a dictionary. Raises ValueError if callsign or aircraft_type is missing."""
        _require_keys(data_dict, ["callsign", "aircraft_type"], "Aircraft")
        aircraft = Aircraft(
            callsign=data_dict["callsign"],
            aircraft_type=data_dict["aircraft_type"],
        )
        aircraft.location = data_dict.get("location", "Ramp")
        aircraft.status = data_dict.get("status", "Parked")
        aircraft.cleared_to = data_dict.get("cleared_to", "")
        aircraft.squawk_code = data_dict.get("squawk_code", "1200")
        aircraft.remarks = data_dict.get("remarks", "")
        aircraft.id = data_dict.get("id", str(uuid.uuid4()))
        aircraft.communication_history = data_dict.get("communication_history", [])
        return aircraft

    def __str__(self) -> str:
        return f"{self.callsign} - {self.aircraft_type} - {self.location} - {self.status}"


@dataclass
class ATCModel:
    """Main ATC state: aircraft list, airports, and current airport selection."""

    aircraft_list: Dict[str, Aircraft] = field(default_factory=dict)
    airports: Dict[str, AirportConfiguration] = field(default_factory=dict)
    current_airport: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize with default airports if none are provided."""
        if not self.airports:
            self._initialize_default_airports()
        if not self.current_airport and self.airports:
            self.current_airport = next(iter(self.airports.keys()))

    def _initialize_default_airports(self) -> None:
        """Populate with default airport configurations (e.g. WSSS, WBGG, WSSL)."""
        default_airports = [
            AirportConfiguration(
                icao="WSSS",
                name="Singapore Changi Airport",
                runways=["02L/20R", "02C/20C", "02R/20L"],
                taxiways=["A", "B", "C", "D", "E", "J", "K", "L", "M", "N", "P", "Q", "R", "S", "T", "W"],
                gates=["A1-A20", "B1-B20", "C1-C30", "D1-D40", "E1-E10", "F1-F10"],
                wind="220° at 10kts",
                visibility="9999",
                ceiling="FEW040",
            ),
            AirportConfiguration(
                icao="WBGG",
                name="Kuching International Airport",
                runways=["07/25"],
                taxiways=["A", "B", "C", "F", "G", "J", "K"],
                gates=["1", "2", "3", "4", "5", "5R", "6", "7", "7R", "8", "8L", "8R", "9", "R1", "R2", "R3", "G1", "G2", "G3", "H1", "H2", "H3"],
                wind="040° at 8kts",
                visibility="8000",
                ceiling="SCT025",
            ),
            AirportConfiguration(
                icao="WSSL",
                name="Singapore Seletar Airport",
                runways=["03/21"],
                taxiways=["A", "B", "C", "E", "J"],
                gates=["A1-A5", "B1-B5"],
                wind="030° at 6kts",
                visibility="9999",
                ceiling="NSC",
            ),
        ]
        for airport in default_airports:
            self.add_airport(airport)
        if "WBGG - Kuching International Airport" in self.airports:
            self.airports["WBGG - Kuching International Airport"].runway_instructions = [
                "No wide body aircraft allowed to park at bay 8 and 9 when bay 8L is occupied.",
                "Pilots to follow marshaller instructions at all stands.",
            ]

    def add_airport(self, airport: AirportConfiguration) -> None:
        """Add an airport to the system (keyed by full name)."""
        self.airports[airport.get_full_name()] = airport

    def remove_airport(self, airport_name: str) -> None:
        """Remove an airport by name; updates current_airport if it was removed."""
        if airport_name in self.airports:
            del self.airports[airport_name]
            if airport_name == self.current_airport and self.airports:
                self.current_airport = next(iter(self.airports.keys()))
            elif not self.airports:
                self.current_airport = None

    def change_current_airport(self, airport_name: str) -> bool:
        """Set the current airport. Returns True if the airport exists."""
        if airport_name in self.airports:
            self.current_airport = airport_name
            return True
        return False

    def get_current_airport(self) -> Optional[AirportConfiguration]:
        """Return the current airport configuration, or None."""
        if self.current_airport and self.current_airport in self.airports:
            return self.airports[self.current_airport]
        return None

    def add_aircraft(self, aircraft: Aircraft) -> None:
        """Add an aircraft to the system (keyed by id)."""
        self.aircraft_list[aircraft.id] = aircraft

    def remove_aircraft(self, aircraft_id: str) -> None:
        """Remove an aircraft by id."""
        if aircraft_id in self.aircraft_list:
            del self.aircraft_list[aircraft_id]

    def update_aircraft(self, aircraft_id: str, **kwargs: Any) -> None:
        """Update an aircraft's attributes by id; only existing attributes are set."""
        if aircraft_id in self.aircraft_list:
            aircraft = self.aircraft_list[aircraft_id]
            for key, value in kwargs.items():
                if hasattr(aircraft, key):
                    setattr(aircraft, key, value)

    def get_aircraft(self, aircraft_id: str) -> Optional[Aircraft]:
        """Get an aircraft by id."""
        return self.aircraft_list.get(aircraft_id)

    def get_all_aircraft(self) -> List[Aircraft]:
        """Return all aircraft in the system."""
        return list(self.aircraft_list.values())

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dictionary for saving."""
        return {
            "aircraft": {aid: ac.to_dict() for aid, ac in self.aircraft_list.items()},
            "airports": {name: ap.to_dict() for name, ap in self.airports.items()},
            "current_airport": self.current_airport,
        }

    @staticmethod
    def from_dict(data_dict: Dict[str, Any]) -> "ATCModel":
        """Create an ATCModel from a dictionary. Optional keys default to empty dict/list/None."""
        model = ATCModel()
        for name, airport_data in data_dict.get("airports", {}).items():
            model.airports[name] = AirportConfiguration.from_dict(airport_data)
        for aircraft_id, aircraft_data in data_dict.get("aircraft", {}).items():
            ac = Aircraft.from_dict(aircraft_data)
            model.aircraft_list[aircraft_id] = ac
        model.current_airport = data_dict.get("current_airport")
        return model
