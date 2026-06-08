"""
Editable airport path graph: runway / taxiway / gate nodes in normalized canvas
coordinates, undirected edges for taxi routing. Persisted per ICAO under data/airports/path_graphs/.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from collections import deque
from typing import Any, Dict, List, Optional


def _new_id() -> str:
    return uuid.uuid4().hex[:10]


class AirportPathGraph:
    """Nodes (normalized 0–1 x,y) and edges for schematic taxi / runway connectivity."""

    def __init__(self, icao: str) -> None:
        self.icao = (icao or "XXXX").upper()
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, str]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {"icao": self.icao, "nodes": self.nodes, "edges": self.edges}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AirportPathGraph":
        g = AirportPathGraph(str(data.get("icao", "XXXX")))
        g.nodes = [dict(n) for n in data.get("nodes", []) if isinstance(n, dict)]
        g.edges = [dict(e) for e in data.get("edges", []) if isinstance(e, dict)]
        return g

    @staticmethod
    def default_graph_dir(base_data_dir: str) -> str:
        return os.path.join(base_data_dir, "airports", "path_graphs")

    @classmethod
    def load_for_icao(cls, icao: str, base_data_dir: str) -> "AirportPathGraph":
        path = os.path.join(cls.default_graph_dir(base_data_dir), f"{icao.upper()}.json")
        g = cls(icao)
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    raw = json.load(f)
                if isinstance(raw, dict):
                    g = cls.from_dict(raw)
            except (OSError, json.JSONDecodeError):
                pass
        return g

    def save(self, base_data_dir: str) -> str:
        d = self.default_graph_dir(base_data_dir)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"{self.icao}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")
        return path

    def node_by_id(self, nid: str) -> Optional[Dict[str, Any]]:
        for n in self.nodes:
            if n.get("id") == nid:
                return n
        return None

    def visible_label(self, n: Dict[str, Any]) -> str:
        lab = (n.get("label") or "").strip()
        if lab:
            return lab
        t = str(n.get("type", "node"))
        short = str(n.get("id", ""))[:4]
        return f"{t}-{short}"

    def combobox_location(self, n: Dict[str, Any]) -> str:
        return f"[path:{n['id']}] {self.visible_label(n)}"

    @staticmethod
    def parse_location_token(s: str) -> Optional[str]:
        if not isinstance(s, str):
            return None
        m = re.match(r"^\[path:([^]]+)\]\s*", s.strip())
        return m.group(1) if m else None

    def add_node(self, kind: str, nx: float, ny: float, label: str = "") -> str:
        nid = _new_id()
        self.nodes.append(
            {
                "id": nid,
                "type": kind,
                "nx": max(0.0, min(1.0, float(nx))),
                "ny": max(0.0, min(1.0, float(ny))),
                "label": (label or "").strip(),
            }
        )
        return nid

    def remove_node(self, nid: str) -> None:
        self.nodes = [n for n in self.nodes if n.get("id") != nid]
        self.edges = [
            e for e in self.edges if e.get("a") != nid and e.get("b") != nid
        ]

    def pop_last_node(self) -> bool:
        if not self.nodes:
            return False
        last = self.nodes[-1]["id"]
        self.remove_node(last)
        return True

    def add_edge(self, a: str, b: str) -> bool:
        if not a or not b or a == b:
            return False
        for e in self.edges:
            x, y = e.get("a"), e.get("b")
            if {x, y} == {a, b}:
                return False
        self.edges.append({"a": a, "b": b})
        return True

    def find_node_at_normalized(
        self, nx: float, ny: float, threshold: float = 0.045
    ) -> Optional[str]:
        best: Optional[str] = None
        best_d = threshold * threshold
        for n in self.nodes:
            dx = float(n["nx"]) - nx
            dy = float(n["ny"]) - ny
            d2 = dx * dx + dy * dy
            if d2 <= best_d:
                best_d = d2
                best = str(n["id"])
        return best

    def shortest_path(self, start_id: str, end_id: str) -> List[str]:
        if start_id == end_id:
            return [start_id]
        adj: Dict[str, List[str]] = {n["id"]: [] for n in self.nodes}
        for e in self.edges:
            a, b = e.get("a"), e.get("b")
            if a in adj and b in adj:
                adj[a].append(b)
                adj[b].append(a)
        if start_id not in adj or end_id not in adj:
            return []
        q: deque[str] = deque([start_id])
        prev: Dict[str, Optional[str]] = {start_id: None}
        while q:
            cur = q.popleft()
            if cur == end_id:
                out: List[str] = []
                p: Optional[str] = end_id
                while p is not None:
                    out.append(p)
                    p = prev.get(p)  # type: ignore[assignment]
                out.reverse()
                return out
            for nb in adj.get(cur, []):
                if nb not in prev:
                    prev[nb] = cur
                    q.append(nb)
        return []

    def location_choices(self) -> List[str]:
        return [self.combobox_location(n) for n in self.nodes]

    def display_category(self, n: Dict[str, Any]) -> str:
        """Human-readable name, e.g. 'Taxiway A' or 'Runway-a1b2' when no custom label."""
        t = str(n.get("type", "node")).title()
        lab = (n.get("label") or "").strip()
        if lab:
            return f"{t} {lab}"
        return f"{t}-{str(n.get('id', ''))[:4]}"

    def adjacency_ids(self) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {str(n["id"]): [] for n in self.nodes}
        ids = set(adj.keys())
        for e in self.edges:
            a, b = e.get("a"), e.get("b")
            if a in ids and b in ids:
                adj[str(a)].append(str(b))
                adj[str(b)].append(str(a))
        for k in adj:
            adj[k] = sorted(set(adj[k]))
        return adj

    def connectivity_summary_lines(self) -> List[str]:
        """One line per node: 'Taxiway A → Gate 1, Gate 2, Runway …'."""
        adj = self.adjacency_ids()
        order = {"runway": 0, "holding": 1, "taxiway": 2, "gate": 3}

        def sort_key(n: Dict[str, Any]) -> tuple:
            return (
                order.get(str(n.get("type", "")).lower(), 9),
                self.display_category(n).lower(),
            )

        lines: List[str] = []
        for n in sorted(self.nodes, key=sort_key):
            nid = str(n.get("id", ""))
            nbrs = adj.get(nid, [])
            src = self.display_category(n)
            if not nbrs:
                lines.append(f"{src} → (no links)")
                continue
            labels: List[str] = []
            for bid in sorted(
                nbrs,
                key=lambda x: self.display_category(self.node_by_id(x) or {}).lower(),
            ):
                bn = self.node_by_id(bid)
                if bn:
                    labels.append(self.display_category(bn))
            lines.append(f"{src} → {', '.join(labels)}")
        return lines
