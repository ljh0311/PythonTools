"""
Emergency Scenarios for Pilot Training
Provides emergency procedure scenarios and time-critical simulations
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from data.scenarios.scenario_engine import TrainingScenario, ScenarioType, DifficultyLevel


class EmergencyType(Enum):
    """Types of emergencies"""
    ENGINE_FAILURE = "engine_failure"
    FIRE = "fire"
    SMOKE = "smoke"
    LANDING_GEAR = "landing_gear"
    MEDICAL = "medical"
    WEATHER = "weather"
    FUEL = "fuel"
    ELECTRICAL = "electrical"
    HYDRAULIC = "hydraulic"
    COMMUNICATION = "communication"


class EmergencySeverity(Enum):
    """Severity levels for emergencies"""
    MINOR = "minor"
    MODERATE = "moderate"
    SERIOUS = "serious"
    CRITICAL = "critical"


@dataclass
class EmergencyScenario:
    """Emergency training scenario"""
    emergency_id: str
    emergency_type: EmergencyType
    severity: EmergencySeverity
    phase_of_flight: str  # e.g., "takeoff", "cruise", "approach", "landing"
    description: str
    initial_conditions: Dict[str, Any]
    time_critical: bool = False
    time_limit_seconds: Optional[int] = None
    required_actions: List[str] = field(default_factory=list)
    checklist_id: Optional[str] = None
    expected_communications: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    failure_conditions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "emergency_id": self.emergency_id,
            "emergency_type": self.emergency_type.value,
            "severity": self.severity.value,
            "phase_of_flight": self.phase_of_flight,
            "description": self.description,
            "initial_conditions": self.initial_conditions,
            "time_critical": self.time_critical,
            "time_limit_seconds": self.time_limit_seconds,
            "required_actions": self.required_actions,
            "checklist_id": self.checklist_id,
            "expected_communications": self.expected_communications,
            "success_criteria": self.success_criteria,
            "failure_conditions": self.failure_conditions
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'EmergencyScenario':
        """Create from dictionary"""
        return EmergencyScenario(
            emergency_id=data["emergency_id"],
            emergency_type=EmergencyType(data["emergency_type"]),
            severity=EmergencySeverity(data["severity"]),
            phase_of_flight=data["phase_of_flight"],
            description=data["description"],
            initial_conditions=data.get("initial_conditions", {}),
            time_critical=data.get("time_critical", False),
            time_limit_seconds=data.get("time_limit_seconds"),
            required_actions=data.get("required_actions", []),
            checklist_id=data.get("checklist_id"),
            expected_communications=data.get("expected_communications", []),
            success_criteria=data.get("success_criteria", []),
            failure_conditions=data.get("failure_conditions", [])
        )


class EmergencyScenarioManager:
    """Manages emergency training scenarios"""
    
    def __init__(self):
        """Initialize emergency scenario manager"""
        self.scenarios: Dict[str, EmergencyScenario] = {}
        self._initialize_default_scenarios()
    
    def _initialize_default_scenarios(self):
        """Initialize with default emergency scenarios"""
        default_scenarios = [
            EmergencyScenario(
                emergency_id="eng_fail_takeoff_01",
                emergency_type=EmergencyType.ENGINE_FAILURE,
                severity=EmergencySeverity.CRITICAL,
                phase_of_flight="takeoff",
                description="Engine failure immediately after takeoff. Critical decision required.",
                initial_conditions={
                    "altitude": 200,
                    "airspeed": 120,
                    "runway_remaining": 0,
                    "terrain_ahead": True
                },
                time_critical=True,
                time_limit_seconds=30,
                required_actions=[
                    "Maintain aircraft control",
                    "Declare emergency",
                    "Execute engine failure checklist",
                    "Decide: continue or return",
                    "Request immediate landing clearance"
                ],
                checklist_id="engine_failure_takeoff",
                expected_communications=[
                    "Mayday Mayday Mayday",
                    "Engine failure",
                    "Request immediate return",
                    "Cleared emergency landing"
                ],
                success_criteria=[
                    "Emergency declared within 5 seconds",
                    "Aircraft control maintained",
                    "Safe landing achieved"
                ],
                failure_conditions=[
                    "Loss of aircraft control",
                    "Stall",
                    "Exceeded time limit"
                ]
            ),
            EmergencyScenario(
                emergency_id="fire_cockpit_01",
                emergency_type=EmergencyType.FIRE,
                severity=EmergencySeverity.CRITICAL,
                phase_of_flight="cruise",
                description="Smoke detected in cockpit. Immediate action required.",
                initial_conditions={
                    "altitude": 35000,
                    "airspeed": 450,
                    "nearest_airport": 50,
                    "smoke_source": "unknown"
                },
                time_critical=True,
                time_limit_seconds=120,
                required_actions=[
                    "Declare emergency",
                    "Execute smoke/fire checklist",
                    "Don oxygen masks",
                    "Request immediate descent",
                    "Divert to nearest airport"
                ],
                checklist_id="smoke_fire",
                expected_communications=[
                    "Mayday Mayday Mayday",
                    "Smoke in cockpit",
                    "Request immediate descent",
                    "Request diversion"
                ],
                success_criteria=[
                    "Emergency declared",
                    "Checklist completed",
                    "Safe landing achieved"
                ],
                failure_conditions=[
                    "Fire spreads",
                    "Loss of consciousness",
                    "Exceeded time limit"
                ]
            ),
            EmergencyScenario(
                emergency_id="gear_malfunction_01",
                emergency_type=EmergencyType.LANDING_GEAR,
                severity=EmergencySeverity.SERIOUS,
                phase_of_flight="approach",
                description="Landing gear will not extend. Troubleshooting required.",
                initial_conditions={
                    "altitude": 3000,
                    "airspeed": 180,
                    "gear_position": "unknown",
                    "manual_extension_available": True
                },
                time_critical=False,
                time_limit_seconds=600,
                required_actions=[
                    "Troubleshoot landing gear",
                    "Attempt manual extension",
                    "Declare emergency if needed",
                    "Prepare for emergency landing"
                ],
                checklist_id="landing_gear",
                expected_communications=[
                    "Landing gear problem",
                    "Attempting gear extension",
                    "Gear down and locked",
                    "Request emergency services"
                ],
                success_criteria=[
                    "Gear extended",
                    "Safe landing achieved"
                ],
                failure_conditions=[
                    "Gear collapse on landing",
                    "Runway overrun"
                ]
            ),
            EmergencyScenario(
                emergency_id="medical_emergency_01",
                emergency_type=EmergencyType.MEDICAL,
                severity=EmergencySeverity.SERIOUS,
                phase_of_flight="cruise",
                description="Passenger medical emergency requiring priority landing.",
                initial_conditions={
                    "altitude": 38000,
                    "airspeed": 480,
                    "nearest_airport": 200,
                    "medical_condition": "cardiac"
                },
                time_critical=True,
                time_limit_seconds=1800,
                required_actions=[
                    "Declare medical emergency",
                    "Request priority handling",
                    "Coordinate with medical services",
                    "Prepare for priority approach"
                ],
                checklist_id="medical_emergency",
                expected_communications=[
                    "Pan Pan Pan",
                    "Medical emergency",
                    "Request priority landing",
                    "Medical services required"
                ],
                success_criteria=[
                    "Emergency declared",
                    "Priority landing achieved",
                    "Medical services ready"
                ],
                failure_conditions=[
                    "Delayed landing",
                    "Medical services not ready"
                ]
            )
        ]
        
        for scenario in default_scenarios:
            self.scenarios[scenario.emergency_id] = scenario
    
    def get_scenario(self, emergency_id: str) -> Optional[EmergencyScenario]:
        """Get emergency scenario by ID"""
        return self.scenarios.get(emergency_id)
    
    def get_scenarios_by_type(self, emergency_type: EmergencyType) -> List[EmergencyScenario]:
        """Get all scenarios of a specific type"""
        return [s for s in self.scenarios.values() if s.emergency_type == emergency_type]
    
    def get_scenarios_by_severity(self, severity: EmergencySeverity) -> List[EmergencyScenario]:
        """Get all scenarios of a specific severity"""
        return [s for s in self.scenarios.values() if s.severity == severity]
    
    def get_time_critical_scenarios(self) -> List[EmergencyScenario]:
        """Get all time-critical scenarios"""
        return [s for s in self.scenarios.values() if s.time_critical]
    
    def add_scenario(self, scenario: EmergencyScenario):
        """Add a new emergency scenario"""
        self.scenarios[scenario.emergency_id] = scenario

