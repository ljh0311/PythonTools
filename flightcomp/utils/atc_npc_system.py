"""
NPC traffic for ATC training: metadata, procedural spawn when scenarios have no traffic,
simple flight/ground phase progression, spawn/despawn, and optional scripted emergencies.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from data.scenarios.scenario_engine import TrainingScenario, TrafficAircraft

from utils.atc_scenario_context import NpcScenarioContext, analyze_scenario_for_npc
from utils.logging_config import get_logger

logger = get_logger(__name__)


class NpcPhase(str, Enum):
    GROUND_TAXI = "ground_taxi"
    HOLDING_SHORT = "holding_short"
    DEPARTURE_ROLL = "departure_roll"
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    DOWNWIND = "downwind"
    BASE = "base"
    FINAL = "final"
    LANDING_ROLL = "landing_roll"
    VACATING = "vacating"
    EMERGENCY = "emergency"


AIRLINES: List[Tuple[str, str]] = [
    ("SIA", "Singapore Airlines"),
    ("MAS", "Malaysia Airlines"),
    ("JST", "Jetstar Asia"),
    ("AXM", "AirAsia"),
    ("QFA", "Qantas"),
    ("THA", "Thai Airways"),
    ("UAE", "Emirates"),
    ("CPA", "Cathay Pacific"),
    ("DLH", "Lufthansa"),
    ("BAW", "British Airways"),
]

AIRCRAFT_TYPES = [
    "A320neo",
    "A321",
    "A350-900",
    "B737-800",
    "B777-300ER",
    "B787-9",
    "ATR72",
]


def _status_from_phase(phase: NpcPhase) -> str:
    return {
        NpcPhase.GROUND_TAXI: "taxi",
        NpcPhase.HOLDING_SHORT: "holding short",
        NpcPhase.DEPARTURE_ROLL: "takeoff roll",
        NpcPhase.CLIMB: "climb",
        NpcPhase.CRUISE: "en route",
        NpcPhase.DESCENT: "descent",
        NpcPhase.APPROACH: "approach",
        NpcPhase.DOWNWIND: "pattern",
        NpcPhase.BASE: "base leg",
        NpcPhase.FINAL: "final",
        NpcPhase.LANDING_ROLL: "landing",
        NpcPhase.VACATING: "vacating",
        NpcPhase.EMERGENCY: "emergency",
    }.get(phase, "active")


def _position_from_phase(phase: NpcPhase, icao: str) -> str:
    if phase in (NpcPhase.GROUND_TAXI, NpcPhase.VACATING):
        return "Taxiway / apron"
    if phase == NpcPhase.HOLDING_SHORT:
        return "Holding short runway"
    if phase == NpcPhase.DEPARTURE_ROLL:
        return "Runway — departure"
    if phase in (NpcPhase.CLIMB, NpcPhase.CRUISE):
        return f"Within TMA {icao}"
    if phase == NpcPhase.DESCENT:
        return f"Arrival sequence — {icao}"
    if phase == NpcPhase.APPROACH:
        return f"ILS / RNAV — {icao}"
    if phase == NpcPhase.DOWNWIND:
        return "Downwind"
    if phase == NpcPhase.BASE:
        return "Base"
    if phase == NpcPhase.FINAL:
        return "Final approach"
    if phase == NpcPhase.LANDING_ROLL:
        return "Runway — rollout"
    if phase == NpcPhase.EMERGENCY:
        return "Priority handling"
    return icao


def _alt_heading_speed(phase: NpcPhase) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    if phase == NpcPhase.GROUND_TAXI:
        return None, random.randint(1, 3) * 90, 15
    if phase == NpcPhase.HOLDING_SHORT:
        return None, None, 0
    if phase == NpcPhase.DEPARTURE_ROLL:
        return None, random.randint(18, 22) * 10, 80
    if phase == NpcPhase.CLIMB:
        return random.randint(4000, 9000), random.randint(18, 36) * 10, 220
    if phase == NpcPhase.CRUISE:
        return random.randint(28000, 38000), random.randint(18, 36) * 10, 440
    if phase == NpcPhase.DESCENT:
        return random.randint(8000, 14000), random.randint(18, 36) * 10, 280
    if phase == NpcPhase.APPROACH:
        return random.randint(2500, 4000), random.randint(18, 22) * 10, 180
    if phase == NpcPhase.DOWNWIND:
        return random.randint(1500, 2500), random.randint(18, 22) * 10, 160
    if phase == NpcPhase.BASE:
        return random.randint(900, 1500), random.randint(18, 22) * 10, 140
    if phase == NpcPhase.FINAL:
        return random.randint(400, 900), random.randint(18, 22) * 10, 135
    if phase == NpcPhase.LANDING_ROLL:
        return 0, random.randint(18, 22) * 10, 95
    if phase == NpcPhase.VACATING:
        return None, random.randint(18, 22) * 10, 25
    if phase == NpcPhase.EMERGENCY:
        return random.randint(2000, 8000), random.randint(18, 36) * 10, 200
    return None, None, None


def _phase_from_traffic_status(status: str) -> NpcPhase:
    s = (status or "").lower().replace(" ", "_")
    mapping = {
        "landing": NpcPhase.FINAL,
        "final": NpcPhase.FINAL,
        "approach": NpcPhase.APPROACH,
        "pattern": NpcPhase.DOWNWIND,
        "downwind": NpcPhase.DOWNWIND,
        "en_route": NpcPhase.CRUISE,
        "cruise": NpcPhase.CRUISE,
        "taxi": NpcPhase.GROUND_TAXI,
        "departure": NpcPhase.CLIMB,
        "takeoff": NpcPhase.DEPARTURE_ROLL,
        "climb": NpcPhase.CLIMB,
        "ground": NpcPhase.GROUND_TAXI,
    }
    return mapping.get(s, NpcPhase.APPROACH)


def _next_phase(phase: NpcPhase, inbound: bool) -> Optional[NpcPhase]:
    """Return next phase, or None when at end of chain (caller switches to arrival or vacating)."""
    if phase == NpcPhase.EMERGENCY:
        return NpcPhase.APPROACH
    if inbound:
        order = [
            NpcPhase.CRUISE,
            NpcPhase.DESCENT,
            NpcPhase.APPROACH,
            NpcPhase.DOWNWIND,
            NpcPhase.BASE,
            NpcPhase.FINAL,
            NpcPhase.LANDING_ROLL,
            NpcPhase.VACATING,
        ]
    else:
        order = [
            NpcPhase.GROUND_TAXI,
            NpcPhase.HOLDING_SHORT,
            NpcPhase.DEPARTURE_ROLL,
            NpcPhase.CLIMB,
            NpcPhase.CRUISE,
        ]
    try:
        i = order.index(phase)
        if i + 1 < len(order):
            return order[i + 1]
    except ValueError:
        pass
    return None


def _max_aircraft_for_scenario(scenario: "TrainingScenario") -> int:
    from data.scenarios.scenario_engine import DifficultyLevel, ScenarioType

    d = scenario.difficulty
    caps = {
        DifficultyLevel.BEGINNER: 4,
        DifficultyLevel.INTERMEDIATE: 7,
        DifficultyLevel.ADVANCED: 10,
        DifficultyLevel.EXPERT: 14,
    }
    cap = caps.get(d, 6)
    if scenario.scenario_type == ScenarioType.TRAFFIC_MANAGEMENT:
        cap += 2
    return cap


def _target_count_when_empty(scenario: "TrainingScenario") -> int:
    from data.scenarios.scenario_engine import DifficultyLevel, ScenarioType

    if scenario.scenario_type == ScenarioType.EMERGENCY:
        base = 2
    elif scenario.scenario_type == ScenarioType.TRAFFIC_MANAGEMENT:
        base = 4
    else:
        base = 3
    if scenario.difficulty == DifficultyLevel.BEGINNER:
        base = max(2, base - 1)
    elif scenario.difficulty == DifficultyLevel.EXPERT:
        base += 2
    return min(base, _max_aircraft_for_scenario(scenario))


@dataclass
class NpcAgent:
    callsign: str
    aircraft_type: str
    airline: str
    destination: str
    phase: NpcPhase
    ticks_in_phase: int = 0
    ticks_until_step: int = 1
    inbound: bool = True
    remarks: str = ""
    emergency: bool = False
    lock_nav_ticks: int = 0
    snapshot_status: str = ""
    snapshot_position: str = ""
    snapshot_alt: Optional[int] = None
    snapshot_hdg: Optional[int] = None
    snapshot_spd: Optional[int] = None
    pause_auto_ticks: int = 0
    path_node_id: Optional[str] = None
    path_route: List[str] = field(default_factory=list)
    path_route_idx: int = 0
    path_route_goal_id: Optional[str] = None
    path_route_human: str = ""
    route_step_ticks: int = 0
    departure_roll_ticks: int = 0

    def apply_phase_to_dict(self, d: Dict[str, Any], icao: str) -> None:
        if self.lock_nav_ticks > 0:
            d["status"] = self.snapshot_status or _status_from_phase(self.phase)
            d["position"] = self.snapshot_position or _position_from_phase(self.phase, icao)
            d["altitude"] = self.snapshot_alt
            d["heading"] = self.snapshot_hdg
            d["speed"] = self.snapshot_spd
            d["npc_phase"] = self.phase.value
            d["airline"] = self.airline
            d["remarks"] = self.remarks
            d["emergency"] = self.emergency
            return
        alt, hdg, spd = _alt_heading_speed(self.phase)
        d["status"] = _status_from_phase(self.phase)
        d["position"] = _position_from_phase(self.phase, icao)
        d["altitude"] = alt
        d["heading"] = hdg
        d["speed"] = spd
        d["npc_phase"] = self.phase.value
        d["airline"] = self.airline
        d["remarks"] = self.remarks
        d["emergency"] = self.emergency
        if self.emergency and not self.remarks:
            d["remarks"] = "Training: declare nature of emergency when ready"


def _blip_normalized(ag: NpcAgent) -> Tuple[float, float]:
    """Approximate (nx, ny) in 0..1 for schematic overlay (y increases downward)."""
    h = (sum(ord(c) for c in ag.callsign) % 1000) / 1000.0
    p = ag.phase
    if p in (NpcPhase.GROUND_TAXI, NpcPhase.VACATING):
        return 0.14 + h * 0.2, 0.34 + (h % 0.08)
    if p == NpcPhase.HOLDING_SHORT:
        return 0.4 + h * 0.28, 0.76 + h * 0.05
    if p in (NpcPhase.DEPARTURE_ROLL, NpcPhase.LANDING_ROLL):
        return 0.28 + h * 0.48, 0.84 + (h - 0.5) * 0.04
    if p == NpcPhase.FINAL:
        return 0.58 + h * 0.22, 0.86
    if p in (NpcPhase.DOWNWIND, NpcPhase.BASE):
        return 0.74 + h * 0.14, 0.2 + h * 0.2
    if p in (NpcPhase.APPROACH, NpcPhase.DESCENT):
        return 0.54 + h * 0.22, 0.38 + h * 0.14
    if p in (NpcPhase.CLIMB, NpcPhase.CRUISE, NpcPhase.EMERGENCY):
        return 0.15 + h * 0.7, 0.08 + (h % 0.14)
    return 0.5, 0.48


class ATCNpcController:
    """Owns NPC agents; advances phases on tick; procedural fill when scenario traffic is empty."""

    def __init__(
        self,
        scenario: "TrainingScenario",
        rng: Optional[random.Random] = None,
    ):
        from data.scenarios.scenario_engine import ScenarioType

        self._scenario = scenario
        self._rng = rng or random.Random()
        self._agents: Dict[str, NpcAgent] = {}
        self._icao = (scenario.airport_icao or "XXXX").upper()
        self._tick_index = 0
        self._emergency_armed = scenario.scenario_type == ScenarioType.EMERGENCY
        self._emergency_fired = False
        self._used_callsigns: set[str] = set()
        self._path_graph_cache: Optional[Any] = None
        self._npc_ctx: NpcScenarioContext = analyze_scenario_for_npc(scenario)

        for ac in scenario.traffic_aircraft:
            self._ingest_traffic_aircraft(ac)

        if not self._agents:
            n = _target_count_when_empty(scenario)
            for _ in range(n):
                self._spawn_random_agent()

    def _ingest_traffic_aircraft(self, ac: "TrafficAircraft") -> None:
        prefix, airline = self._rng.choice(AIRLINES)
        if not ac.callsign:
            return
        cs = ac.callsign.strip().upper()
        if cs in self._used_callsigns:
            return
        self._used_callsigns.add(cs)
        if len(cs) >= 3 and cs[:3].isalpha():
            airline = next((a for p, a in AIRLINES if p == cs[:3]), airline)
        phase = _phase_from_traffic_status(ac.status)
        inbound = phase in (
            NpcPhase.FINAL,
            NpcPhase.APPROACH,
            NpcPhase.DOWNWIND,
            NpcPhase.BASE,
            NpcPhase.CRUISE,
            NpcPhase.DESCENT,
        )
        lock = 2 if (ac.altitude is not None or ac.heading is not None or ac.speed) else 0
        scen_rm = self._npc_ctx.objectives_snippet or self._npc_ctx.npc_brief[:100]
        agent = NpcAgent(
            callsign=cs,
            aircraft_type=ac.aircraft_type or self._rng.choice(AIRCRAFT_TYPES),
            airline=airline,
            destination=ac.destination or self._icao,
            phase=phase,
            inbound=inbound,
            ticks_until_step=self._rng.randint(1, 3),
            remarks=f"Scenario traffic — {scen_rm}",
            lock_nav_ticks=lock,
            snapshot_status=ac.status or "",
            snapshot_position=ac.position or "",
            snapshot_alt=ac.altitude,
            snapshot_hdg=ac.heading,
            snapshot_spd=ac.speed,
        )
        self._agents[cs] = agent

    def _spawn_random_agent(self, inbound: Optional[bool] = None) -> str:
        if inbound is None:
            inbound = self._rng.random() < self._npc_ctx.inbound_spawn_probability
        prefix, airline = self._rng.choice(AIRLINES)
        suffix = "".join(self._rng.choice(string.digits) for _ in range(3))
        cs = f"{prefix}{suffix}"
        while cs in self._used_callsigns:
            suffix = "".join(self._rng.choice(string.digits) for _ in range(3))
            cs = f"{prefix}{suffix}"
        self._used_callsigns.add(cs)
        flow = self._npc_ctx.primary_flow
        if inbound:
            if flow == "pattern":
                start = self._rng.choice(
                    [
                        NpcPhase.DOWNWIND,
                        NpcPhase.DOWNWIND,
                        NpcPhase.BASE,
                        NpcPhase.FINAL,
                    ]
                )
            elif flow == "arrival":
                start = self._rng.choice(
                    [NpcPhase.DESCENT, NpcPhase.APPROACH, NpcPhase.FINAL, NpcPhase.APPROACH]
                )
            elif flow == "emergency_airport":
                start = self._rng.choice(
                    [NpcPhase.APPROACH, NpcPhase.DOWNWIND, NpcPhase.DESCENT, NpcPhase.CRUISE]
                )
            else:
                start = self._rng.choice(
                    [NpcPhase.CRUISE, NpcPhase.DESCENT, NpcPhase.APPROACH, NpcPhase.DOWNWIND]
                )
        else:
            start = NpcPhase.GROUND_TAXI
        self._agents[cs] = NpcAgent(
            callsign=cs,
            aircraft_type=self._rng.choice(AIRCRAFT_TYPES),
            airline=airline,
            destination=self._icao,
            phase=start,
            inbound=inbound,
            ticks_until_step=self._rng.randint(1, 3),
            remarks=self._npc_ctx.pilot_remarks(inbound),
        )
        return cs

    def as_active_aircraft(
        self, path_graph: Optional[Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        from utils.atc_path_awareness import assign_initial_path_node
        from utils.atc_traffic_snapping import _nodes_of_type, _pick_stable, blip_for_agent

        if path_graph is not None:
            self._path_graph_cache = path_graph
        g = self._path_graph_cache

        out: Dict[str, Dict[str, Any]] = {}
        for cs, ag in self._agents.items():
            d: Dict[str, Any] = {
                "callsign": ag.callsign,
                "type": ag.aircraft_type,
                "position": "",
                "status": "",
                "altitude": None,
                "heading": None,
                "speed": None,
                "destination": ag.destination,
            }
            ag.apply_phase_to_dict(d, self._icao)
            if g and g.nodes and not ag.path_node_id:
                assign_initial_path_node(self._rng, g, ag)
            if g and ag.path_node_id and ag.lock_nav_ticks <= 0:
                n = g.node_by_id(ag.path_node_id)
                if n and ag.phase != NpcPhase.DEPARTURE_ROLL:
                    d["position"] = f"{g.visible_label(n)} ({self._icao} graph)"
                elif n and ag.phase == NpcPhase.DEPARTURE_ROLL:
                    nt = str(n.get("type", "")).lower()
                    if nt == "runway":
                        d["position"] = f"{g.visible_label(n)} — takeoff roll ({self._icao} graph)"
                if ag.path_route_human:
                    d["path_route"] = ag.path_route_human
                d["path_graph_node"] = ag.path_node_id
            if g and ag.phase == NpcPhase.DEPARTURE_ROLL and (
                "takeoff roll" not in (d.get("position") or "").lower()
            ):
                rwl = _nodes_of_type(g, "runway")
                rn = _pick_stable(rwl, ag.callsign) if rwl else None
                if rn:
                    d["position"] = f"{g.visible_label(rn)} — takeoff roll ({self._icao})"
            nx, ny = blip_for_agent(g, ag)
            d["map_nx"], d["map_ny"] = nx, ny
            d.update(
                self._npc_ctx.row_fields(
                    list(self._scenario.expected_communications or [])
                )
            )
            out[cs] = d
        return out

    @property
    def npc_scenario_context(self) -> NpcScenarioContext:
        return self._npc_ctx

    def apply_clearance(
        self,
        callsign: str,
        clearance: str,
        path_graph: Optional[Any] = None,
    ) -> Tuple[List[str], bool]:
        """
        React to a trainee clearance: adjust phase, pause auto progression briefly, return readback lines.
        Returns (log_lines, recognized) where log_lines are pilot-style readbacks.
        """
        from utils.atc_path_awareness import assign_initial_path_node, plan_taxi_after_clearance

        cs = (callsign or "").strip().upper()
        if cs not in self._agents:
            return ([], False)
        ag = self._agents[cs]
        if path_graph is not None:
            self._path_graph_cache = path_graph
        g = self._path_graph_cache
        ag.lock_nav_ticks = 0
        u = clearance.upper()
        parts: List[str] = []

        if "HOLD SHORT" in u:
            ag.phase = NpcPhase.HOLDING_SHORT
            ag.inbound = False
            ag.path_route = []
            ag.path_route_goal_id = None
            ag.path_route_human = ""
            ag.route_step_ticks = 0
            parts.append("Holding short")
        elif "CLEARED FOR TAKEOFF" in u or "CLEARED TAKEOFF" in u:
            ag.phase = NpcPhase.DEPARTURE_ROLL
            ag.inbound = False
            ag.path_route = []
            ag.path_route_human = ""
            ag.route_step_ticks = 0
            ag.departure_roll_ticks = 0
            if g and g.nodes:
                from utils.atc_path_awareness import (
                    first_runway_node_id,
                    parse_runway_hint_from_clearance,
                )

                rid = first_runway_node_id(g, parse_runway_hint_from_clearance(clearance))
                if rid:
                    ag.path_node_id = rid
            parts.append("Cleared for takeoff")
        elif "CLEARED TO LAND" in u or ("CLEARED" in u and " TO LAND" in u):
            ag.phase = NpcPhase.LANDING_ROLL
            ag.inbound = True
            parts.append("Cleared to land")
        elif "GO AROUND" in u:
            ag.phase = NpcPhase.DOWNWIND
            ag.inbound = True
            parts.append("Going around")
        elif "LINE UP" in u or "LINE UP AND WAIT" in u:
            ag.phase = NpcPhase.HOLDING_SHORT
            ag.inbound = False
            if g and g.nodes:
                from utils.atc_path_awareness import (
                    first_runway_node_id,
                    parse_runway_hint_from_clearance,
                )

                rid = first_runway_node_id(g, parse_runway_hint_from_clearance(clearance))
                if rid:
                    ag.path_node_id = rid
            parts.append("Line up and wait")
        elif "TAXI" in u:
            ag.phase = NpcPhase.GROUND_TAXI
            ag.inbound = False
            parts.append("Wilco, taxi")
            if g and g.nodes:
                if not ag.path_node_id:
                    assign_initial_path_node(self._rng, g, ag)
                path, goal, human = plan_taxi_after_clearance(g, ag, u)
                if path and len(path) > 1:
                    ag.path_route = path
                    ag.path_route_idx = 0
                    ag.path_node_id = path[0]
                    ag.path_route_goal_id = goal
                    ag.path_route_human = human
                    ag.route_step_ticks = 3
                    parts.append(f"Route: {human}")
                elif path and len(path) == 1:
                    ag.path_route = path
                    ag.path_route_idx = 0
                    ag.path_node_id = path[0]
                    ag.path_route_goal_id = goal
                    ag.path_route_human = human
                    ag.route_step_ticks = 0
                    parts.append("At clearance limit on graph — request further taxi if needed")
                else:
                    parts.append(
                        "No taxi route on graph (link gate/taxi to holding or runway, "
                        "or add holding node short of runway)"
                    )
        elif "HOLD POSITION" in u:
            ag.phase = NpcPhase.HOLDING_SHORT
            parts.append("Holding position")
        elif "CONTACT" in u:
            parts.append("Wilco, switching")
        elif "CLEARED APPROACH" in u or "CLEARED FOR THE APPROACH" in u:
            ag.phase = NpcPhase.APPROACH
            ag.inbound = True
            parts.append("Cleared approach")
        elif "DESCEND" in u or "DESCENT" in u:
            if ag.inbound:
                ag.phase = NpcPhase.DESCENT
            parts.append("Descend, wilco")
        else:
            parts.append("Roger")

        ag.pause_auto_ticks = 6
        ag.ticks_until_step = max(ag.ticks_until_step, 3)
        readback = f"{cs}, {', '.join(parts)}."
        return ([readback], True)

    def tick(self) -> List[str]:
        """Advance simulation; return optional log lines (spawn/despawn/emergency)."""
        self._tick_index += 1
        messages: List[str] = []
        max_ac = _max_aircraft_for_scenario(self._scenario)

        if self._emergency_armed and not self._emergency_fired and self._agents:
            if self._tick_index >= self._rng.randint(2, 5):
                victim = self._rng.choice(list(self._agents.keys()))
                ag = self._agents[victim]
                ag.phase = NpcPhase.EMERGENCY
                ag.emergency = True
                ag.remarks = self._scenario.metadata.get(
                    "emergency_type", self._npc_ctx.emergency_narrative
                )
                ag.ticks_until_step = 2
                self._emergency_fired = True
                messages.append(f"NPC: {victim} declares emergency / priority ({ag.remarks}).")

        g = self._path_graph_cache
        to_remove: List[str] = []
        for cs, ag in self._agents.items():
            if ag.lock_nav_ticks > 0:
                ag.lock_nav_ticks -= 1
                continue
            if ag.pause_auto_ticks > 0:
                ag.pause_auto_ticks -= 1
                continue
            if (
                g
                and g.nodes
                and ag.phase == NpcPhase.GROUND_TAXI
                and len(ag.path_route) > 1
            ):
                ag.route_step_ticks -= 1
                if ag.route_step_ticks > 0:
                    continue
                if ag.path_route_idx < len(ag.path_route) - 1:
                    ag.path_route_idx += 1
                    ag.path_node_id = ag.path_route[ag.path_route_idx]
                    at_goal = ag.path_route_idx >= len(ag.path_route) - 1
                    ag.route_step_ticks = 4 if at_goal else 3
                    continue
                gn = g.node_by_id(ag.path_route[-1])
                t = str(gn.get("type", "")).lower() if gn else ""
                if t in ("holding", "taxiway", "runway"):
                    ag.phase = NpcPhase.HOLDING_SHORT
                ag.path_route = []
                ag.path_route_goal_id = None
                ag.path_route_human = ""
                ag.route_step_ticks = 0
                ag.ticks_until_step = max(ag.ticks_until_step, 4)
                continue

            outbound_surface = not ag.inbound and ag.phase in (
                NpcPhase.GROUND_TAXI,
                NpcPhase.HOLDING_SHORT,
            )
            if outbound_surface:
                continue

            if not ag.inbound and ag.phase == NpcPhase.DEPARTURE_ROLL:
                ag.departure_roll_ticks += 1
                if ag.departure_roll_ticks >= 7:
                    ag.phase = NpcPhase.CLIMB
                    ag.departure_roll_ticks = 0
                    ag.ticks_until_step = self._rng.randint(2, 5)
                    ag.ticks_in_phase = 0
                continue

            ag.ticks_in_phase += 1
            ag.ticks_until_step -= 1
            if ag.ticks_until_step > 0:
                continue
            if ag.phase == NpcPhase.VACATING:
                to_remove.append(cs)
                messages.append(f"NPC: {cs} vacated and left frequency.")
                continue
            if ag.phase == NpcPhase.EMERGENCY:
                ag.phase = NpcPhase.APPROACH
                ag.ticks_until_step = self._rng.randint(2, 4)
                continue
            nxt = _next_phase(ag.phase, ag.inbound)
            if nxt is None:
                if not ag.inbound:
                    ag.inbound = True
                    ag.phase = NpcPhase.DESCENT
                else:
                    ag.phase = NpcPhase.VACATING
                ag.ticks_until_step = self._rng.randint(1, 3)
                ag.ticks_in_phase = 0
                continue
            ag.phase = nxt
            ag.ticks_until_step = self._rng.randint(1, 4)
            ag.ticks_in_phase = 0

        for cs in to_remove:
            self._agents.pop(cs, None)
            self._used_callsigns.discard(cs)

        if len(self._agents) < max_ac and self._rng.random() < 0.28:
            cs_new = self._spawn_random_agent()
            messages.append(f"NPC: New traffic {cs_new}.")

        return messages

    @classmethod
    def from_scenario(
        cls, scenario: "TrainingScenario", seed: Optional[int] = None
    ) -> "ATCNpcController":
        rng = random.Random(seed if seed is not None else hash(scenario.scenario_id) % (2**32))
        return cls(scenario, rng=rng)
