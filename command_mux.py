"""
command_mux.py

Keeps both command-input paths alive on the Pi:
- CV module commands on one UDP port
- Teleop commands on a different UDP port

The original downstream control pipeline remains unchanged:
    Command source -> MotionManager -> MotorController -> ServoController -> HAL

This module only replaces the inline receive logic that used to live in main.py.
"""

from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass
from typing import Dict, Optional

from config import WHEEL_RADIUS_M


ZERO_PACKET = {"throttle": 0.0, "steering": 0.0, "measured_v": 0.0}


@dataclass
class SourceState:
    name: str
    port: int
    sock: socket.socket
    latest_packet: Dict[str, float]
    last_rx_time: float = 0.0
    connected: bool = False


class UDPCommandMux:
    """Receive commands from both CV and teleop, then expose one active source.

    Design goals:
    - keep both sources available at the same time
    - preserve the original packet shape
    - preserve the original main control pipeline after command acquisition
    - allow explicit switching between sources
    """

    def __init__(
        self,
        cv_port: int,
        teleop_port: int,
        timeout_s: float,
        bind_host: str = "0.0.0.0",
        initial_source: str = "cv",
    ) -> None:
        self.timeout_s = timeout_s
        self.bind_host = bind_host
        self.active_source = initial_source

        self.sources: Dict[str, SourceState] = {
            "cv": self._make_source("cv", cv_port),
            "teleop": self._make_source("teleop", teleop_port),
        }

    def _make_source(self, name: str, port: int) -> SourceState:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.bind_host, port))
        sock.setblocking(False)
        return SourceState(
            name=name,
            port=port,
            sock=sock,
            latest_packet=dict(ZERO_PACKET),
        )

    def close(self) -> None:
        for source in self.sources.values():
            source.sock.close()

    def switch_source(self, source_name: str) -> None:
        if source_name not in self.sources:
            raise ValueError(f"Unknown command source: {source_name}")
        self.active_source = source_name

    def toggle_source(self) -> str:
        self.active_source = "teleop" if self.active_source == "cv" else "cv"
        return self.active_source

    def _drain_socket(self, source: SourceState) -> bool:
        """Read all waiting packets and keep only the newest one."""
        received_any = False
        while True:
            try:
                data, _ = source.sock.recvfrom(1024)
            except BlockingIOError:
                break
            except OSError:
                break

            try:
                packet = json.loads(data.decode())
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            source.latest_packet = {
                "throttle": float(packet.get("throttle", 0.0)),
                "steering": float(packet.get("steering", 0.0)),
                "measured_v": float(packet.get("measured_v", 0.0)),
            }
            source.last_rx_time = time.time()
            source.connected = True
            received_any = True

        # Apply watchdog to this source independently.
        if source.connected and (time.time() - source.last_rx_time > self.timeout_s):
            source.latest_packet = dict(ZERO_PACKET)
            source.connected = False

        return received_any

    def poll(self) -> bool:
        """Poll both sockets once. Returns whether active source is alive."""
        for source in self.sources.values():
            self._drain_socket(source)
        return self.is_active_source_alive()

    def is_active_source_alive(self) -> bool:
        return self.sources[self.active_source].connected

    def get_active_packet(self) -> Dict[str, float]:
        source = self.sources[self.active_source]
        if not source.connected:
            return dict(ZERO_PACKET)
        return dict(source.latest_packet)

    def get_command(self) -> Dict[str, float]:
        packet = self.get_active_packet()
        return {
            "throttle": packet["throttle"],
            "steering": packet["steering"],
            "mode": self.active_source.upper(),
            "timestamp": time.time(),
        }

    def get_motor_feedback(self) -> Dict[str, float]:
        packet = self.get_active_packet()
        shaft_speed = packet["measured_v"] / WHEEL_RADIUS_M
        return {
            "left_shaft_speed": shaft_speed,
            "right_shaft_speed": shaft_speed,
        }

    def get_status(self) -> Dict[str, Optional[float]]:
        status = {"active_source": self.active_source}
        for name, source in self.sources.items():
            age = None
            if source.last_rx_time > 0.0:
                age = time.time() - source.last_rx_time
            status[f"{name}_connected"] = source.connected
            status[f"{name}_age_s"] = age
            status[f"{name}_port"] = source.port
        return status
