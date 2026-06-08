"""Training-style airport schematic colors and layout (FAA marking palette: white runway, yellow taxi)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class AirportDiagramTheme:
    """Pavement-centric palette; not chart-scale."""

    grass_top: str = "#d8e8d4"
    grass_bottom: str = "#b8cfb0"
    grass_horizon: str = "#c5dcc0"
    runway_fill: str = "#2e2e32"
    runway_outline: str = "#18181a"
    runway_centerline: str = "#f5f5f5"
    taxiway_pavement: str = "#5a5d58"
    taxiway_corridor: str = "#4f524e"
    taxiway_stub: str = "#6b6e68"
    taxiway_centerline: str = "#f1c40f"
    taxiway_edge_line: str = "#3d403c"
    apron_fill: str = "#aeb2ad"
    apron_outline: str = "#7a7d78"
    apron_label: str = "#2c2c2c"
    text_title: str = "#1a2433"
    text_subtitle: str = "#34495e"
    text_note: str = "#566573"
    text_diagram_footer: str = "#7f8c8d"
    path_runway_strip_fill: str = "#3d4a52"
    path_runway_strip_outline: str = "#2c3e50"
    path_taxi_strip_fill: str = "#5a5d58"
    path_taxi_strip_outline: str = "#3d403c"
    path_other_edge: str = "#e67e22"
    path_node_runway: str = "#1abc9c"
    path_node_taxiway: str = "#f39c12"
    path_node_gate: str = "#9b59b6"
    path_node_holding: str = "#e74c3c"
    path_node_default: str = "#7f8c8d"
    path_node_outline: str = "#2c3e50"
    path_link_highlight: str = "#f1c40f"


DEFAULT_DIAGRAM_THEME = AirportDiagramTheme()


def taxiway_line_widths(scale: float) -> tuple[int, int]:
    """Parallel taxi band width and connector/corridor width from canvas scale."""
    main = int(max(10, min(16, scale * 0.017)))
    conn = int(max(8, min(13, scale * 0.014)))
    return main, conn


def compute_diagram_layout(
    canvas_width: int,
    canvas_height: int,
    n_runways: int,
    *,
    max_parallel: int = 4,
) -> Dict[str, Any]:
    """Single place for runway strip geometry and apron/taxi offsets."""
    n = min(max(n_runways, 1), max_parallel)
    scale = float(min(canvas_width, canvas_height))
    runway_length = canvas_width * 0.88
    if n > 1:
        runway_width = max(12.0, min(22.0, scale * 0.028))
    else:
        runway_width = max(16.0, min(26.0, scale * 0.034))
    south_y = canvas_height * 0.90
    north_y = canvas_height * (0.48 if n > 1 else 0.72)
    if n == 1:
        runway_ys: List[float] = [south_y]
    else:
        step = (south_y - north_y) / max(n - 1, 1)
        runway_ys = [south_y - i * step for i in range(n)]
    north_rwy_edge = min(runway_ys) - runway_width / 2
    taxi_north_offset = max(32.0, scale * 0.045)
    main_taxiway_y = north_rwy_edge - taxi_north_offset
    apron_gap = max(14.0, scale * 0.02)
    apron_top_y = main_taxiway_y - apron_gap
    apron_bottom_y = canvas_height * 0.12
    tw_main, tw_conn = taxiway_line_widths(scale)
    return {
        "n_runways": n,
        "runway_length": runway_length,
        "runway_width": runway_width,
        "runway_ys": runway_ys,
        "main_taxiway_y": main_taxiway_y,
        "apron_top_y": apron_top_y,
        "apron_bottom_y": apron_bottom_y,
        "taxi_main_width": tw_main,
        "taxi_conn_width": tw_conn,
        "scale": scale,
    }


def runway_centerline_dash(runway_length: float) -> tuple[int, int]:
    """Dash length scales slightly with strip length."""
    unit = max(18.0, runway_length / 45.0)
    return (int(unit * 1.4), int(unit * 0.85))
