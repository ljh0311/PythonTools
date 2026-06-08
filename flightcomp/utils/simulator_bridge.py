"""
X-Plane 11 / FlyWithLua simulator bridge.
Listens for UDP JSON packets from a FlyWithLua script (position, airport, COM1)
and optionally sends training messages back for in-sim display.
"""

import json
import socket
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_LISTEN_PORT = 49000
DEFAULT_SEND_PORT = 49001


@dataclass
class SimState:
    """Last received simulator state from X-Plane / FlyWithLua."""
    icao: str = ""
    lat: float = 0.0
    lon: float = 0.0
    hdg: float = 0.0
    alt_ft: float = 0.0
    com1_hz: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimState":
        """Build SimState from a JSON dict (e.g. from UDP packet)."""
        return cls(
            icao=str(data.get("icao", "") or ""),
            lat=float(data.get("lat", 0) or 0),
            lon=float(data.get("lon", 0) or 0),
            hdg=float(data.get("hdg", 0) or 0),
            alt_ft=float(data.get("alt_ft", 0) or 0),
            com1_hz=int(data.get("com1_hz", 0) or 0),
            raw=dict(data),
        )


class SimulatorBridge:
    """
    UDP bridge between flightcomp and X-Plane 11 FlyWithLua.
    Listens for sim state (icao, position, etc.) and can send messages to Lua for on-screen display.
    """

    def __init__(
        self,
        listen_port: int = DEFAULT_LISTEN_PORT,
        send_port: int = DEFAULT_SEND_PORT,
        on_state_received: Optional[Callable[[SimState], None]] = None,
    ) -> None:
        self.listen_port = listen_port
        self.send_port = send_port
        self.on_state_received = on_state_received
        self._state = SimState()
        self._state_lock = threading.Lock()
        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def get_state(self) -> SimState:
        """Return a copy of the last received sim state (thread-safe)."""
        with self._state_lock:
            return SimState(
                icao=self._state.icao,
                lat=self._state.lat,
                lon=self._state.lon,
                hdg=self._state.hdg,
                alt_ft=self._state.alt_ft,
                com1_hz=self._state.com1_hz,
                raw=dict(self._state.raw),
            )

    def start(self) -> bool:
        """Start the UDP listener thread. Returns True if started successfully."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Simulator bridge already running")
            return True
        try:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind(("127.0.0.1", self.listen_port))
            self._sock.settimeout(1.0)
        except OSError as e:
            logger.warning("Could not bind simulator bridge port %s: %s", self.listen_port, e)
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Simulator bridge listening on UDP port %s", self.listen_port)
        return True

    def stop(self) -> None:
        """Stop the listener thread and close the socket."""
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("Simulator bridge stopped")

    def _listen_loop(self) -> None:
        while not self._stop.is_set() and self._sock:
            try:
                data, _ = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                if not self._stop.is_set():
                    logger.debug("Simulator bridge socket error")
                break
            try:
                payload = json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.debug("Invalid simulator bridge packet: %s", e)
                continue
            if not isinstance(payload, dict):
                continue
            try:
                state = SimState.from_dict(payload)
            except (TypeError, ValueError) as e:
                logger.debug("Invalid sim state fields: %s", e)
                continue
            with self._state_lock:
                self._state = state
            if self.on_state_received:
                try:
                    self.on_state_received(state)
                except Exception as e:
                    logger.warning("Simulator bridge callback error: %s", e)
        logger.debug("Simulator bridge listen loop exited")

    def send_message(self, text: str, message_type: str = "atc_message") -> bool:
        """
        Send a message to FlyWithLua for on-screen display (e.g. ATC instruction).
        Lua should listen on send_port and display the 'text' field.
        """
        if not text:
            return False
        payload = json.dumps({"type": message_type, "text": text}).encode("utf-8")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.sendto(payload, ("127.0.0.1", self.send_port))
            sock.close()
            return True
        except OSError as e:
            logger.debug("Could not send to FlyWithLua: %s", e)
            return False
