"""
Laptop-side WASD teleoperation client for the robot.

This version is intended for the dual-source Pi receiver:
- CV module keeps sending to COMMAND_PORT (for example 5005)
- teleop sends to a separate teleop port (default 5006)
- main_dual_source.py on the Pi selects which source is active
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from dataclasses import dataclass

DEFAULT_PI_IP = "172.20.10.3"
DEFAULT_PORT = 5006
DEFAULT_SEND_HZ = 20.0
DEFAULT_STEP = 0.1
DEFAULT_MEASURED_V = 0.0


@dataclass
class TeleopState:
    throttle: float = 0.0
    steering: float = 0.0
    measured_v: float = DEFAULT_MEASURED_V
    running: bool = True


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class PiCommandSender:
    def __init__(self, pi_ip: str, port: int, send_hz: float, state: TeleopState):
        self.pi_ip = pi_ip
        self.port = port
        self.period = 1.0 / send_hz
        self.state = state
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _payload(self) -> dict:
        return {
            "throttle": self.state.throttle,
            "steering": self.state.steering,
            "measured_v": self.state.measured_v,
        }

    def send_once(self) -> None:
        self.sock.sendto(json.dumps(self._payload()).encode("utf-8"), (self.pi_ip, self.port))

    def loop(self) -> None:
        try:
            while self.state.running:
                self.send_once()
                time.sleep(self.period)
        finally:
            stop_payload = {"throttle": 0.0, "steering": 0.0, "measured_v": self.state.measured_v}
            try:
                self.sock.sendto(json.dumps(stop_payload).encode("utf-8"), (self.pi_ip, self.port))
            except OSError:
                pass
            self.sock.close()


def print_status(state: TeleopState) -> None:
    sys.stdout.write(
        "\r"
        f"Teleop throttle={state.throttle:+.2f} steering={state.steering:+.2f} "
        "[W/S throttle, A/D steering, SPACE reset, Q quit]"
        " " * 8
    )
    sys.stdout.flush()


def run_windows_keyboard_loop(state: TeleopState, step: float) -> None:
    import msvcrt

    print_status(state)
    while state.running:
        if not msvcrt.kbhit():
            time.sleep(0.02)
            continue
        key = msvcrt.getch()
        if key in (b"w", b"W"):
            state.throttle = clamp(state.throttle + step)
        elif key in (b"s", b"S"):
            state.throttle = clamp(state.throttle - step)
        elif key in (b"a", b"A"):
            state.steering = clamp(state.steering - step)
        elif key in (b"d", b"D"):
            state.steering = clamp(state.steering + step)
        elif key == b" ":
            state.throttle = 0.0
            state.steering = 0.0
        elif key in (b"q", b"Q"):
            state.running = False
            break
        print_status(state)


def run_unix_keyboard_loop(state: TeleopState, step: float) -> None:
    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        print_status(state)
        while state.running:
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if not ready:
                continue
            key = sys.stdin.read(1)
            if key in ("w", "W"):
                state.throttle = clamp(state.throttle + step)
            elif key in ("s", "S"):
                state.throttle = clamp(state.throttle - step)
            elif key in ("a", "A"):
                state.steering = clamp(state.steering - step)
            elif key in ("d", "D"):
                state.steering = clamp(state.steering + step)
            elif key == " ":
                state.throttle = 0.0
                state.steering = 0.0
            elif key in ("q", "Q"):
                state.running = False
                break
            print_status(state)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        print()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Laptop-side WASD teleop client for dual-source Pi receiver")
    parser.add_argument("--pi-ip", default=DEFAULT_PI_IP, help="Pi 5 IP address")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP teleop command port used by main_dual_source.py")
    parser.add_argument("--send-hz", type=float, default=DEFAULT_SEND_HZ, help="How fast to stream commands")
    parser.add_argument("--step", type=float, default=DEFAULT_STEP, help="Increment per key press")
    parser.add_argument("--measured-v", type=float, default=DEFAULT_MEASURED_V, help="Value placed in measured_v field")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    state = TeleopState(measured_v=args.measured_v)
    sender = PiCommandSender(args.pi_ip, args.port, args.send_hz, state)
    sender_thread = threading.Thread(target=sender.loop, daemon=True)
    sender_thread.start()

    print(f"Sending teleop packets to Pi at {args.pi_ip}:{args.port}")
    print("Run main_dual_source.py on the Pi. Use Pi terminal keys to switch active source.")

    try:
        if sys.platform.startswith("win"):
            run_windows_keyboard_loop(state, args.step)
        else:
            run_unix_keyboard_loop(state, args.step)
    except KeyboardInterrupt:
        state.running = False
    finally:
        state.running = False
        sender_thread.join(timeout=1.0)
        print("Teleop client stopped.")


if __name__ == "__main__":
    main()
