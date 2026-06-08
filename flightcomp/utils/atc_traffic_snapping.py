"""Place NPC traffic blips on path-graph nodes (runway / taxiway / gate) when available."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Tuple

from utils.airport_path_graph import AirportPathGraph

if TYPE_CHECKING:
    from utils.atc_npc_system import NpcAgent

from utils.atc_npc_system import NpcPhase, _blip_normalized


def _nodes_of_type(graph: AirportPathGraph, kind: str) -> List[dict]:
    k = kind.lower()
    return [n for n in graph.nodes if str(n.get("type", "")).lower() == k]


def _pick_stable(nodes: List[dict], callsign: str) -> Optional[dict]:
    if not nodes:
        return None
    idx = sum(ord(c) for c in callsign) % len(nodes)
    return nodes[idx]


def _jitter_norm(callsign: str, nx: float, ny: float) -> Tuple[float, float]:
    h = sum(ord(c) for c in callsign)
    jx = ((h % 5) - 2) * 0.0045
    jy = ((h // 5 % 5) - 2) * 0.0045
    return max(0.02, min(0.98, nx + jx)), max(0.02, min(0.98, ny + jy))


def _runway_ids(graph: AirportPathGraph) -> set:
    return {str(n["id"]) for n in _nodes_of_type(graph, "runway")}


def _taxiways_linked_to_runway(graph: AirportPathGraph) -> List[dict]:
    rw = _runway_ids(graph)
    if not rw:
        return []
    linked: List[dict] = []
    for n in _nodes_of_type(graph, "taxiway"):
        nid = str(n.get("id", ""))
        for e in graph.edges:
            a, b = e.get("a"), e.get("b")
            if a == nid and b in rw:
                linked.append(n)
                break
            if b == nid and a in rw:
                linked.append(n)
                break
    return linked


def _midpoint_runway_edge(graph: AirportPathGraph, callsign: str) -> Optional[Tuple[float, float]]:
    rw = _nodes_of_type(graph, "runway")
    if len(rw) < 2:
        return None
    rw_ids = {str(n["id"]) for n in rw}
    for e in graph.edges:
        a, b = e.get("a"), e.get("b")
        if a in rw_ids and b in rw_ids:
            na = next((x for x in rw if str(x["id"]) == a), None)
            nb = next((x for x in rw if str(x["id"]) == b), None)
            if na and nb:
                h = sum(ord(c) for c in callsign) % 5
                t = 0.35 + (h / 10.0)
                nx = float(na["nx"]) * (1 - t) + float(nb["nx"]) * t
                ny = float(na["ny"]) * (1 - t) + float(nb["ny"]) * t
                return nx, ny
    n = _pick_stable(rw, callsign)
    if n:
        return float(n["nx"]), float(n["ny"])
    return None


def blip_for_agent(
    graph: Optional[AirportPathGraph],
    ag: "NpcAgent",
) -> Tuple[float, float]:
    """Normalized map coords on path nodes/edges, or schematic fallback if graph empty."""
    if graph is None or not graph.nodes:
        return _blip_normalized(ag)

    cs = ag.callsign
    if ag.phase == NpcPhase.DEPARTURE_ROLL:
        rw = _nodes_of_type(graph, "runway")
        n = _pick_stable(rw, cs) if rw else None
        if n:
            return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))
    if ag.path_node_id:
        n = graph.node_by_id(ag.path_node_id)
        if n:
            return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))

    phase = ag.phase
    rw = _nodes_of_type(graph, "runway")
    tw = _nodes_of_type(graph, "taxiway")
    gates = _nodes_of_type(graph, "gate")

    def fb() -> Tuple[float, float]:
        return _blip_normalized(ag)

    if phase in (NpcPhase.GROUND_TAXI, NpcPhase.VACATING):
        pool = tw or gates or rw
        n = _pick_stable(pool, cs)
        if not n:
            return fb()
        return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))

    if phase == NpcPhase.HOLDING_SHORT:
        pool = _nodes_of_type(graph, "holding") or _taxiways_linked_to_runway(graph) or tw or rw
        n = _pick_stable(pool, cs)
        if not n:
            return fb()
        return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))

    if phase in (NpcPhase.DEPARTURE_ROLL, NpcPhase.LANDING_ROLL):
        mid = _midpoint_runway_edge(graph, cs)
        if mid:
            return _jitter_norm(cs, mid[0], mid[1])
        n = _pick_stable(rw, cs)
        if not n:
            return fb()
        return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))

    if phase == NpcPhase.FINAL:
        n = _pick_stable(rw, cs)
        if not n:
            return fb()
        nx, ny = float(n["nx"]), float(n["ny"])
        # Short final: offset toward field entry (assume runway roughly E–W, approach from east)
        nx = max(0.04, nx - 0.055)
        return _jitter_norm(cs, nx, ny)

    if phase in (NpcPhase.DOWNWIND, NpcPhase.BASE):
        pool = gates or tw
        n = _pick_stable(pool, cs + "pat")
        if not n:
            return fb()
        return _jitter_norm(cs, float(n["nx"]), float(n["ny"]))

    if phase in (NpcPhase.APPROACH, NpcPhase.DESCENT):
        rw_n = _pick_stable(rw, cs)
        tw_n = _pick_stable(tw or gates or rw, cs + "app")
        if rw_n and tw_n and id(rw_n) != id(tw_n):
            a = 0.62
            nx = a * float(rw_n["nx"]) + (1 - a) * float(tw_n["nx"])
            ny = a * float(rw_n["ny"]) + (1 - a) * float(tw_n["ny"])
            return _jitter_norm(cs, nx, ny)
        if rw_n:
            return _jitter_norm(cs, float(rw_n["nx"]), float(rw_n["ny"]))
        return fb()

    if phase in (NpcPhase.CLIMB, NpcPhase.CRUISE, NpcPhase.EMERGENCY):
        if rw:
            mx = sum(float(n["nx"]) for n in rw) / len(rw)
            my = sum(float(n["ny"]) for n in rw) / len(rw)
            return _jitter_norm(cs, mx, max(0.04, my - 0.22))
        return fb()

    return fb()
