"""
Models package for the Pilot ATC Assistant.

Provides:
- ATC model: AirportConfiguration, Aircraft (serializable), ATCModel (main ATC state).
- Live aircraft: LiveAircraft, AircraftType, AircraftStatus, AircraftPosition (stateful UI model).
- Training records: TrainingSession, CommunicationRecord, PilotProgress, SkillProgress, SessionStatus.
- Airport database: AirportDatabase, AirportLayout, Runway, Taxiway, Gate, HotSpot, AirportProcedure.
"""

from .atc_model import ATCModel, AirportConfiguration, Aircraft
from .aircraft import AircraftPosition, AircraftStatus, AircraftType, LiveAircraft
from .training_record import (
    CommunicationRecord,
    DATA_VERSION,
    PilotProgress,
    SessionStatus,
    SkillProgress,
    TrainingSession,
    TREND_HISTORY_MAX,
)
from .airport_database import (
    AirportDatabase,
    AirportLayout,
    AirportProcedure,
    Gate,
    HotSpot,
    HotSpotType,
    Runway,
    Taxiway,
)

__all__ = [
    # atc_model
    "ATCModel",
    "AirportConfiguration",
    "Aircraft",
    # aircraft (live)
    "LiveAircraft",
    "AircraftType",
    "AircraftStatus",
    "AircraftPosition",
    # training_record
    "TrainingSession",
    "CommunicationRecord",
    "PilotProgress",
    "SkillProgress",
    "SessionStatus",
    "DATA_VERSION",
    "TREND_HISTORY_MAX",
    # airport_database
    "AirportDatabase",
    "AirportLayout",
    "Runway",
    "Taxiway",
    "Gate",
    "HotSpot",
    "HotSpotType",
    "AirportProcedure",
]
