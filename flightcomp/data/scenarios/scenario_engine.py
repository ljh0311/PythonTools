"""
Scenario Engine for Pilot Training
Manages training scenarios with progressive difficulty, weather integration, and traffic variations
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple

from enum import Enum
from dataclasses import dataclass, field
import random
import ollama
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DifficultyLevel(Enum):
    """Difficulty levels for training scenarios"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class ScenarioType(Enum):
    """Types of training scenarios"""

    NORMAL_OPERATIONS = "normal_operations"
    TRAFFIC_MANAGEMENT = "traffic_management"
    WEATHER = "weather"
    EMERGENCY = "emergency"
    NIGHT_OPERATIONS = "night_operations"
    LOW_VISIBILITY = "low_visibility"


@dataclass
class WeatherCondition:
    """Weather condition for scenarios, allows AI-powered augmentation using Ollama if enabled."""

    wind_direction: int = 0
    wind_speed: int = 0
    visibility: str = "10 miles"
    ceiling: str = "Clear"
    precipitation: str = "None"
    temperature: int = 20
    qnh: float = 1013.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "wind_direction": self.wind_direction,
            "wind_speed": self.wind_speed,
            "visibility": self.visibility,
            "ceiling": self.ceiling,
            "precipitation": self.precipitation,
            "temperature": self.temperature,
            "qnh": self.qnh,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], use_ollama: bool = False) -> "WeatherCondition":
        """
        Create WeatherCondition from dictionary.
        If use_ollama is True and Ollama is available, use Ollama to fill or augment weather details.
        """
        # Try using Ollama for data enrichment if requested
        if use_ollama:
            try:
                import ollama
                import json as _json

                prompt = (
                    "Given the following partial or full weather data as JSON:\n"
                    f"{_json.dumps(data)}\n"
                    "Fill in any missing details with realistic, aviation-appropriate values. "
                    "Output as compact JSON with keys: wind_direction, wind_speed, visibility, ceiling, "
                    "precipitation, temperature, qnh."
                )
                res = ollama.generate(model="llama2", prompt=prompt, stream=False)
                generated = _json.loads(res["response"])
                # Update only missing fields in data, not overwrite supplied ones
                for key in generated:
                    if data.get(key) is None:
                        data[key] = generated[key]
            except Exception as e:
                logger.warning(f"Ollama augmentation failed: {e}")

        return WeatherCondition(
            wind_direction=data.get("wind_direction", 0),
            wind_speed=data.get("wind_speed", 0),
            visibility=data.get("visibility", "10 miles"),
            ceiling=data.get("ceiling", "Clear"),
            precipitation=data.get("precipitation", "None"),
            temperature=data.get("temperature", 20),
            qnh=data.get("qnh", 1013.0),
        )


@dataclass
class TrafficAircraft:
    """Aircraft in traffic scenario"""

    callsign: str
    aircraft_type: str
    position: str
    altitude: Optional[int] = None
    heading: Optional[int] = None
    speed: Optional[int] = None
    status: str = "en_route"
    destination: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "callsign": self.callsign,
            "aircraft_type": self.aircraft_type,
            "position": self.position,
            "altitude": self.altitude,
            "heading": self.heading,
            "speed": self.speed,
            "status": self.status,
            "destination": self.destination,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any], use_ollama: bool = False) -> "TrafficAircraft":
        """
        Create TrafficAircraft from dictionary.
        If use_ollama is True and Ollama is available, use Ollama to fill or augment aircraft details.
        """
        # Try using Ollama for data enrichment if requested
        if use_ollama:
            try:
                import ollama
                import json as _json

                prompt = (
                    "Given the following partial or full traffic aircraft data as JSON:\n"
                    f"{_json.dumps(data)}\n"
                    "Fill in any missing details (altitude, heading, speed, status, destination) with realistic values relevant for an ATC/training scenario. "
                    "If information is already present, retain it. Output as compact JSON with keys: callsign, aircraft_type, position, altitude, heading, speed, status, destination."
                )
                res = ollama.generate(model="llama2", prompt=prompt, stream=False)
                generated = _json.loads(res["response"])
                # Update only missing fields in data, not overwrite supplied ones
                for key in generated:
                    if data.get(key) is None:
                        data[key] = generated[key]
            except Exception as e:
                import logging

                logger = logging.getLogger("scenario_engine.traffic_aircraft")
                logger.warning(f"Ollama augmentation for TrafficAircraft failed: {e}")

        return TrafficAircraft(
            callsign=data.get("callsign"),
            aircraft_type=data.get("aircraft_type"),
            position=data.get("position"),
            altitude=data.get("altitude"),
            heading=data.get("heading"),
            speed=data.get("speed"),
            status=data.get("status", "en_route"),
            destination=data.get("destination", ""),
        )


@dataclass
class TrainingScenario:
    """Training scenario definition"""

    scenario_id: str
    name: str
    description: str
    airport_icao: str
    difficulty: DifficultyLevel
    scenario_type: ScenarioType
    weather: WeatherCondition
    traffic_aircraft: List[TrafficAircraft] = field(default_factory=list)
    objectives: List[str] = field(default_factory=list)
    expected_communications: List[str] = field(default_factory=list)
    time_limit: Optional[int] = None  # in minutes
    metadata: Dict[str, Any] = field(default_factory=dict)
    checklist_id: Optional[str] = (
        None  # for emergency scenarios; links to emergency_checklists
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "airport_icao": self.airport_icao,
            "difficulty": self.difficulty.value,
            "scenario_type": self.scenario_type.value,
            "weather": self.weather.to_dict(),
            "traffic_aircraft": [ac.to_dict() for ac in self.traffic_aircraft],
            "objectives": self.objectives,
            "expected_communications": self.expected_communications,
            "time_limit": self.time_limit,
            "metadata": self.metadata,
            "checklist_id": self.checklist_id,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TrainingScenario":
        """Create from dictionary"""
        return TrainingScenario(
            scenario_id=data["scenario_id"],
            name=data["name"],
            description=data["description"],
            airport_icao=data["airport_icao"],
            difficulty=DifficultyLevel(data["difficulty"]),
            scenario_type=ScenarioType(data["scenario_type"]),
            weather=WeatherCondition.from_dict(data["weather"]),
            traffic_aircraft=[
                TrafficAircraft.from_dict(ac) for ac in data.get("traffic_aircraft", [])
            ],
            objectives=data.get("objectives", []),
            expected_communications=data.get("expected_communications", []),
            time_limit=data.get("time_limit"),
            metadata=data.get("metadata", {}),
            checklist_id=data.get("checklist_id"),
        )


def debrief_benchmarks_for_scenario(
    scenario: Optional[TrainingScenario],
) -> Tuple[float, float]:
    """
    Target score (0-100) and target response time (seconds) for trainee debrief.
    Uses scenario.metadata keys target_score / target_response_sec when present,
    otherwise defaults by difficulty; falls back to 80 / 8 when scenario is None.
    """
    if scenario is None:
        return 80.0, 8.0
    md = scenario.metadata or {}
    ts = md.get("target_score")
    tr = md.get("target_response_sec")
    try:
        if ts is not None and tr is not None:
            return float(ts), float(tr)
    except (TypeError, ValueError):
        pass

    by_difficulty = {
        DifficultyLevel.BEGINNER: (75.0, 10.0),
        DifficultyLevel.INTERMEDIATE: (80.0, 8.0),
        DifficultyLevel.ADVANCED: (85.0, 7.0),
        DifficultyLevel.EXPERT: (90.0, 6.0),
    }
    return by_difficulty.get(scenario.difficulty, (80.0, 8.0))


class ScenarioEngine:
    """Engine for managing and loading training scenarios, with Ollama integration for scenario generation"""

    def __init__(self, scenarios_dir: Optional[str] = None):
        """
        Initialize the scenario engine

        Args:
            scenarios_dir: Directory containing scenario JSON files.
                           Defaults to data/scenarios/ relative to this file
        """
        if scenarios_dir is None:
            # Get directory relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            scenarios_dir = current_dir

        self.scenarios_dir = scenarios_dir
        self.scenarios: Dict[str, TrainingScenario] = {}
        self._load_scenarios()

    def _load_scenarios(self):
        """Load all scenarios from JSON files"""
        # Load airport scenarios
        airport_file = os.path.join(self.scenarios_dir, "airport_scenarios.json")
        if os.path.exists(airport_file):
            self._load_scenarios_from_file(airport_file)

        # Load emergency scenarios
        emergency_file = os.path.join(self.scenarios_dir, "emergency_scenarios.json")
        if os.path.exists(emergency_file):
            self._load_scenarios_from_file(emergency_file)

    def _load_scenarios_from_file(self, filepath: str):
        """Load scenarios from a JSON file"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                scenarios_list = data.get("scenarios", [])
                for scenario_data in scenarios_list:
                    scenario = TrainingScenario.from_dict(scenario_data)
                    self.scenarios[scenario.scenario_id] = scenario
        except Exception as e:
            logger.warning("Error loading scenarios from %s: %s", filepath, e)

    def get_scenario(self, scenario_id: str) -> Optional[TrainingScenario]:
        """Get a scenario by ID"""
        return self.scenarios.get(scenario_id)

    def get_scenarios_by_difficulty(
        self, difficulty: DifficultyLevel
    ) -> List[TrainingScenario]:
        """Get all scenarios for a specific difficulty level"""
        return [s for s in self.scenarios.values() if s.difficulty == difficulty]

    def get_scenarios_by_airport(self, airport_icao: str) -> List[TrainingScenario]:
        """Get all scenarios for a specific airport"""
        return [s for s in self.scenarios.values() if s.airport_icao == airport_icao]

    def get_scenarios_by_type(
        self, scenario_type: ScenarioType
    ) -> List[TrainingScenario]:
        """Get all scenarios of a specific type"""
        return [s for s in self.scenarios.values() if s.scenario_type == scenario_type]

    def get_all_scenarios(self) -> List[TrainingScenario]:
        """Get all available scenarios"""
        return list(self.scenarios.values())

    def get_random_scenario(
        self,
        difficulty: Optional[DifficultyLevel] = None,
        airport_icao: Optional[str] = None,
        scenario_type: Optional[ScenarioType] = None,
        use_ollama: bool = False,
        ollama_model: str = "llama3",
        system_prompt: Optional[str] = None,
    ) -> Optional[TrainingScenario]:
        """
        Get a random scenario matching optional filters.
        If use_ollama is True, generate a scenario using the Ollama API.
        """
        if use_ollama:
            # Use Ollama to generate a scenario matching constraints
            prompt = self._build_ollama_prompt(
                difficulty, airport_icao, scenario_type, system_prompt=system_prompt
            )
            try:
                response = ollama.generate(
                    model=ollama_model, prompt=prompt, temperature=0.8
                )
                import ast

                # Try parsing dictionary in python or JSON format from output
                scenario_dict = None
                try:
                    scenario_dict = json.loads(response["response"])
                except Exception:
                    try:
                        scenario_dict = ast.literal_eval(response["response"])
                    except Exception:
                        scenario_dict = None
                if scenario_dict and isinstance(scenario_dict, dict):
                    return TrainingScenario.from_dict(scenario_dict)
            except Exception as e:
                logger.warning("Ollama scenario generation failed: %s", e)
            # If Ollama fails, fallback to local scenarios

        filtered = self.scenarios.values()
        if difficulty:
            filtered = [s for s in filtered if s.difficulty == difficulty]
        if airport_icao:
            filtered = [s for s in filtered if s.airport_icao == airport_icao]
        if scenario_type:
            filtered = [s for s in filtered if s.scenario_type == scenario_type]

        if filtered:
            return random.choice(list(filtered))
        return None

    def _build_ollama_prompt(
        self, difficulty, airport_icao, scenario_type, system_prompt=None
    ):
        """
        Build a prompt for Ollama to generate a training scenario.
        """
        prompt = ""
        if system_prompt:
            prompt += system_prompt + "\n\n"
        prompt += "Generate a JSON object for a realistic flight training scenario with fields:\n"
        prompt += (
            "scenario_id, name, description, airport_icao, difficulty (beginner/intermediate/advanced/expert), "
            "scenario_type (normal_operations, traffic_management, emergency), weather (as dict), traffic_aircraft (list), "
            "objectives (list), expected_communications (list), time_limit (int), metadata (dict), checklist_id (str, optional).\n"
        )
        prompt += "Fields:\n"
        if difficulty:
            prompt += f"- Difficulty: {difficulty.value}\n"
        if airport_icao:
            prompt += f"- Airport: {airport_icao}\n"
        if scenario_type:
            prompt += f"- Scenario type: {scenario_type.value}\n"
        prompt += "Do not include any explanation. Only return a valid JSON object for the scenario."
        return prompt

    def add_scenario(self, scenario: TrainingScenario):
        """Add a new scenario to the engine"""
        self.scenarios[scenario.scenario_id] = scenario

    def save_scenarios_to_file(
        self, filepath: str, scenario_ids: Optional[List[str]] = None
    ):
        """Save scenarios to a JSON file"""
        scenarios_to_save = self.scenarios.values()
        if scenario_ids:
            scenarios_to_save = [
                s for s in scenarios_to_save if s.scenario_id in scenario_ids
            ]

        data = {"scenarios": [s.to_dict() for s in scenarios_to_save]}

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
