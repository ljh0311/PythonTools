"""Optional Dear PyGui live dashboard (GPU-accelerated side panel)."""

import threading
from typing import Optional

from loguru import logger

from .hud_state import HudState

DPG_AVAILABLE = False
try:
    import dearpygui.dearpygui as dpg

    DPG_AVAILABLE = True
except ImportError:
    dpg = None


class DpgDashboard:
    """Runs Dear PyGui in a background thread; reads shared HudState."""

    def __init__(self, hud: HudState, title: str = "SmartAI Live Dashboard"):
        self.hud = hud
        self.title = title
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._tag_prefix = "smartai_"

    def start(self):
        if not DPG_AVAILABLE:
            logger.warning("Dear PyGui not installed. pip install dearpygui")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if DPG_AVAILABLE and dpg.is_dearpygui_running():
            dpg.stop_dearpygui()

    def _run(self):
        dpg.create_context()
        with dpg.window(label=self.title, tag="main_window", width=420, height=640):
            dpg.add_text("Navigation", tag=f"{self._tag_prefix}nav")
            dpg.add_text("Position", tag=f"{self._tag_prefix}pos")
            dpg.add_text("Speed", tag=f"{self._tag_prefix}spd")
            dpg.add_separator()
            dpg.add_text("Sensors", tag=f"{self._tag_prefix}sensors")
            dpg.add_separator()
            dpg.add_text("RobotMind", tag=f"{self._tag_prefix}mind")
            dpg.add_text("Decision", tag=f"{self._tag_prefix}decision")
            dpg.add_separator()
            dpg.add_text("Motors L/R", tag=f"{self._tag_prefix}motors")

        dpg.create_viewport(title=self.title, width=440, height=660)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("main_window", True)

        while self._running and dpg.is_dearpygui_running():
            self._refresh()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

    def _refresh(self):
        h = self.hud
        dpg.set_value(f"{self._tag_prefix}nav", f"State: {h.nav_state}" + (" [PAUSED]" if h.paused else ""))
        dpg.set_value(f"{self._tag_prefix}pos", f"Pos: ({h.position[0]:.2f}, {h.position[1]:.2f})")
        dpg.set_value(f"{self._tag_prefix}spd", f"Speed: {h.linear_speed:.2f} m/s · WP: {h.waypoints}")
        sens = " · ".join(f"{k}={v:.2f}m" for k, v in h.sensors.items()) or "—"
        dpg.set_value(f"{self._tag_prefix}sensors", f"Sensors: {sens}")
        dpg.set_value(f"{self._tag_prefix}mind", f"Think: {(h.robotmind_thought or '—')[:80]}")
        dpg.set_value(
            f"{self._tag_prefix}decision",
            f"Decide: {h.robotmind_decision or h.vision_action or '—'}",
        )
        dpg.set_value(f"{self._tag_prefix}motors", f"Rear L={h.motor_left:.0f} R={h.motor_right:.0f}")