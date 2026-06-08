"""
Path-graph–aware taxi goals and routes: explicit holding nodes, or taxiways linked to a runway
as implicit hold-short points. Used by NPCs for position text and taxi clearances.
"""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING, List, Optional, Tuple

from utils.airport_path_graph import AirportPathGraph

if TYPE_CHECKING:
    from utils.atc_npc_system import NpcAgent

from utils.atc_npc_system import NpcPhase


def _nodes_of_type(graph: AirportPathGraph, kind: str) -> List[dict]:
    k = kind.lower()
    return [n for n in graph.nodes if str(n.get("type", "")).lower() == k]


def _neighbors(graph: AirportPathGraph, nid: str) -> List[str]:
    out: List[str] = []
    for e in graph.edges:
        a, b = e.get("a"), e.get("b")
        if a == nid:
            out.append(str(b))
        elif b == nid:
            out.append(str(a))
    return out


def runways_matching_hint(graph: AirportPathGraph, hint: Optional[str]) -> List[dict]:
    rw = _nodes_of_type(graph, "runway")
    if not hint:
        return rw
    h = hint.upper().replace(" ", "")
    matched = []
    for n in rw:
        lab = (n.get("label") or "").upper().replace(" ", "")
        if h in lab or lab in h:
            matched.append(n)
        elif h in str(n.get("id", "")).upper():
            matched.append(n)
    return matched or rw


def first_runway_node_id(graph: AirportPathGraph, hint: Optional[str]) -> Optional[str]:
    """Pick a runway graph node for phraseology / takeoff snap (hint from clearance)."""
    rws = runways_matching_hint(graph, hint)
    if not rws:
        return None
    return str(rws[0].get("id", "")) or None


def holding_or_taxi_short_of_runway(graph: AirportPathGraph, runway_node_id: str) -> List[dict]:
    """Explicit holding nodes linked to this runway, plus taxiway nodes with an edge to it."""
    seen: set = set()
    out: List[dict] = []
    for n in graph.nodes:
        nid = str(n.get("id", ""))
        t = str(n.get("type", "")).lower()
        if t not in ("holding", "taxiway"):
            continue
        for nb in _neighbors(graph, nid):
            if nb == runway_node_id:
                if nid not in seen:
                    seen.add(nid)
                    out.append(n)
                break
    return out


def _unique_nodes(nodes: List[dict]) -> List[dict]:
    seen = set()
    out: List[dict] = []
    for n in nodes:
        i = str(n.get("id", ""))
        if i and i not in seen:
            seen.add(i)
            out.append(n)
    return out


def pick_taxi_goal_and_route(
    graph: AirportPathGraph,
    start_node_id: str,
    runway_hint: Optional[str],
) -> Tuple[List[str], str, str]:
    """
    Shortest-path taxi route from start to best hold-short point for the runway, else to runway node.
    Returns (node_id_path, goal_id, human_readable_chain).
    """
    if not start_node_id:
        return [], "", ""

    runway_pool = runways_matching_hint(graph, runway_hint)
    if not runway_pool:
        return [], "", ""

    candidates: List[dict] = []
    for rw in runway_pool:
        rid = str(rw["id"])
        candidates.extend(holding_or_taxi_short_of_runway(graph, rid))

    candidates = _unique_nodes(candidates)

    def fmt_path(path: List[str]) -> str:
        parts = []
        for pid in path:
            n = graph.node_by_id(pid)
            if n:
                parts.append(graph.visible_label(n))
        return " → ".join(parts) if parts else ""

    best_path: List[str] = []
    best_goal = ""
    best_len = 10**6

    for goal in candidates:
        gid = str(goal.get("id", ""))
        path = graph.shortest_path(start_node_id, gid)
        if path and len(path) < best_len:
            best_len = len(path)
            best_path = path
            best_goal = gid

    if best_path:
        return best_path, best_goal, fmt_path(best_path)

    for rw in runway_pool:
        rid = str(rw["id"])
        path = graph.shortest_path(start_node_id, rid)
        if path and len(path) < best_len:
            best_len = len(path)
            best_path = path
            best_goal = rid

    if best_path:
        return best_path, best_goal, fmt_path(best_path)

    return [], "", ""


def parse_runway_hint_from_clearance(text: str) -> Optional[str]:
    u = text.upper()
    m = re.search(r"(?:RUNWAY|RWY)\s*([0-9]{2}[LRC]?|[0-9]{2}/[0-9]{2}[LRC]?)", u)
    if m:
        return m.group(1).strip().upper()
    m2 = re.search(r"\b([0-9]{2}[LRC])\b", u)
    if m2:
        return m2.group(1).upper()
    return None


def assign_initial_path_node(rng: random.Random, graph: AirportPathGraph, ag: "NpcAgent") -> None:
    """Place agent on a gate (departure) or taxi/holding (surface), or clear for airborne phases."""
    gates = _nodes_of_type(graph, "gate")
    tw = _nodes_of_type(graph, "taxiway")
    hold = _nodes_of_type(graph, "holding")
    rw = _nodes_of_type(graph, "runway")

    if ag.inbound and ag.phase not in (
        NpcPhase.GROUND_TAXI,
        NpcPhase.VACATING,
        NpcPhase.HOLDING_SHORT,
    ):
        ag.path_node_id = None
        ag.path_route = []
        ag.path_route_human = ""
        ag.path_route_goal_id = None
        return

    pool: List[dict] = []
    if not ag.inbound and ag.phase == NpcPhase.GROUND_TAXI:
        pool = gates or tw or hold or rw
    elif ag.inbound and ag.phase in (
        NpcPhase.FINAL,
        NpcPhase.LANDING_ROLL,
        NpcPhase.APPROACH,
    ):
        pool = rw or tw
    else:
        pool = tw or gates or hold or rw

    if not pool:
        ag.path_node_id = None
        ag.path_route = []
        ag.path_route_goal_id = None
        ag.path_route_human = ""
        return
    idx = rng.randint(0, len(pool) - 1)
    n = pool[idx]
    ag.path_node_id = str(n.get("id", ""))
    ag.path_route = [ag.path_node_id] if ag.path_node_id else []
    ag.path_route_idx = 0
    ag.path_route_goal_id = None
    ag.path_route_human = graph.visible_label(n) if n else ""


def plan_taxi_after_clearance(
    graph: AirportPathGraph,
    ag: "NpcAgent",
    clearance_upper: str,
) -> Tuple[List[str], str, str]:
    """Build route after a TAXI clearance; runway parsed from text when present."""
    start = ag.path_node_id
    if not start:
        return [], "", ""
    hint = parse_runway_hint_from_clearance(clearance_upper)
    return pick_taxi_goal_and_route(graph, start, hint)
