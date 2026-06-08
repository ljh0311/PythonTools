"""Derive NPC / UI hints from the active TrainingScenario (focus, spawn mix, brief text)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from data.scenarios.scenario_engine import TrainingScenario


_VALID_FLOWS = frozenset({"departure", "arrival", "pattern", "mixed", "emergency_airport"})


@dataclass(frozen=True)
class NpcScenarioContext:
    """What NPC traffic should assume about the training session."""

    scenario_id: str
    name: str
    scenario_type: str
    difficulty: str
    primary_flow: str
    inbound_spawn_probability: float
    npc_brief: str
    objectives_snippet: str
    emergency_narrative: str

    def pilot_remarks(self, inbound: bool) -> str:
        leg = "Inbound" if inbound else "Outbound"
        tail = self.objectives_snippet or self.npc_brief
        if len(tail) > 140:
            tail = tail[:137] + "..."
        return f"{leg} — scenario: {self.name}. {tail}"

    def row_fields(self, expected_comms: Optional[List[str]] = None) -> Dict[str, Any]:
        comms = expected_comms or []
        preview = "; ".join(comms[:4])
        if len(preview) > 200:
            preview = preview[:197] + "..."
        out: Dict[str, Any] = {
            "training_scenario_id": self.scenario_id,
            "training_scenario_name": self.name,
            "training_scenario_type": self.scenario_type,
            "training_difficulty": self.difficulty,
            "training_flow": self.primary_flow,
            "training_npc_brief": self.npc_brief,
            "training_objectives_snippet": self.objectives_snippet,
        }
        if preview:
            out["training_expected_comms_preview"] = preview
        return out


def _join_blob(scenario: "TrainingScenario") -> str:
    parts: List[str] = [
        scenario.name or "",
        scenario.description or "",
        " ".join(scenario.objectives or []),
    ]
    return " ".join(parts).lower()


def _objectives_snippet(scenario: "TrainingScenario", max_len: int = 180) -> str:
    objs = scenario.objectives or []
    if not objs:
        return ""
    s = "; ".join(objs[:3])
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _emergency_narrative(scenario: "TrainingScenario") -> str:
    meta = scenario.metadata or {}
    if meta.get("emergency_type"):
        return str(meta["emergency_type"])
    desc = (scenario.description or "").strip()
    if desc:
        cut = desc.split(". ")
        return cut[0][:160] if cut else desc[:160]
    return "Simulated emergency — respond per training"


def _infer_primary_flow(scenario: "TrainingScenario", blob: str) -> str:
    from data.scenarios.scenario_engine import ScenarioType

    override = (scenario.metadata or {}).get("training_flow")
    if isinstance(override, str) and override.lower() in _VALID_FLOWS:
        return override.lower()

    if scenario.scenario_type == ScenarioType.EMERGENCY:
        return "emergency_airport"

    if "traffic pattern" in blob or (
        "pattern" in blob and any(x in blob for x in ("downwind", "base", "traffic", "circuit"))
    ):
        return "pattern"

    dep_hits = sum(1 for k in ("departure", "takeoff", "taxi", "pushback", "surface") if k in blob)
    arr_hits = sum(
        1 for k in ("landing", "arrival", "approach", "final", "ils", "touchdown") if k in blob
    )

    if scenario.scenario_type == ScenarioType.TRAFFIC_MANAGEMENT and dep_hits < 2 and arr_hits < 2:
        return "mixed"
    if arr_hits > dep_hits:
        return "arrival"
    if dep_hits > arr_hits:
        return "departure"
    if dep_hits and arr_hits:
        return "mixed"
    return "mixed"


def _inbound_probability(flow: str) -> float:
    return {
        "departure": 0.22,
        "arrival": 0.82,
        "pattern": 0.72,
        "mixed": 0.52,
        "emergency_airport": 0.48,
    }.get(flow, 0.52)


def analyze_scenario_for_npc(scenario: "TrainingScenario") -> NpcScenarioContext:
    blob = _join_blob(scenario)
    flow = _infer_primary_flow(scenario, blob)
    st = (
        scenario.scenario_type.value
        if hasattr(scenario.scenario_type, "value")
        else str(scenario.scenario_type)
    )
    diff = (
        scenario.difficulty.value
        if hasattr(scenario.difficulty, "value")
        else str(scenario.difficulty)
    )
    brief = f"{scenario.name} — {scenario.description or 'ATC training'}".strip()
    if len(brief) > 220:
        brief = brief[:217] + "..."

    return NpcScenarioContext(
        scenario_id=scenario.scenario_id,
        name=scenario.name,
        scenario_type=st,
        difficulty=diff,
        primary_flow=flow,
        inbound_spawn_probability=_inbound_probability(flow),
        npc_brief=brief,
        objectives_snippet=_objectives_snippet(scenario),
        emergency_narrative=_emergency_narrative(scenario),
    )
