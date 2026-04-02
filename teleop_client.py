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

DEFAULT_SERVO_STEP_US = 50
DEFAULT_SERVO_MIN_US = 500
DEFAULT_SERVO_CENTER_US = 1500
DEFAULT_SERVO_MAX_US = 2500


@dataclass
class TeleopState:
    throttle: float = 0.0
    steering: float = 0.0
    measured_v: float = DEFAULT_MEASURED_V

    manipulator_servo1_pwm_value_us: int = DEFAULT_SERVO_CENTER_US
    manipulator_servo2_pwm_value_us: int = DEFAULT_SERVO_CENTER_US

    running: bool = True


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def clamp_servo_us(value: int, low: int = DEFAULT_SERVO_MIN_US, high: int = DEFAULT_SERVO_MAX_US) -> int:
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
            "manipulator_servo1_pwm_value_us": self.state.manipulator_servo1_pwm_value_us,
            "manipulator_servo2_pwm_value_us": self.state.manipulator_servo2_pwm_value_us,
        }

    def send_once(self) -> None:
        self.sock.sendto(json.dumps(self._payload()).encode("utf-8"), (self.pi_ip, self.port))

    def loop(self) -> None:
        try:
            while self.state.running:
                self.send_once()
                time.sleep(self.period)
        finally:
            stop_payload = {
                "throttle": 0.0,
                "steering": 0.0,
                "measured_v": self.state.measured_v,
                "manipulator_servo1_pwm_value_us": self.state.manipulator_servo1_pwm_value_us,
                "manipulator_servo2_pwm_value_us": self.state.manipulator_servo2_pwm_value_us,
            }
            try:
                self.sock.sendto(json.dumps(stop_payload).encode("utf-8"), (self.pi_ip, self.port))
            except OSError:
                pass
            self.sock.close()


def print_status(state: TeleopState) -> None:
    sys.stdout.write(
        "\r"
        f"Teleop throttle={state.throttle:+.2f} "
        f"steering={state.steering:+.2f} "
        f"servo2={state.manipulator_servo1_pwm_value_us}us "
        f"servo3={state.manipulator_servo2_pwm_value_us}us "
        "[W/S throttle, A/D steering, I/K servo2, J/L servo3, SPACE reset, Q quit]"
        " " * 8
    )
    sys.stdout.flush()


def run_windows_keyboard_loop(state: TeleopState, step: float, servo_step_us: int) -> None:
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
        elif key in (b"i", b"I"):
            state.manipulator_servo1_pwm_value_us = clamp_servo_us(
                state.manipulator_servo1_pwm_value_us + servo_step_us
            )
        elif key in (b"k", b"K"):
            state.manipulator_servo1_pwm_value_us = clamp_servo_us(
                state.manipulator_servo1_pwm_value_us - servo_step_us
            )
        elif key in (b"j", b"J"):
            state.manipulator_servo2_pwm_value_us = clamp_servo_us(
                state.manipulator_servo2_pwm_value_us - servo_step_us
            )
        elif key in (b"l", b"L"):
            state.manipulator_servo2_pwm_value_us = clamp_servo_us(
                state.manipulator_servo2_pwm_value_us + servo_step_us
            )
        elif key == b" ":
            state.throttle = 0.0
            state.steering = 0.0
            state.manipulator_servo1_pwm_value_us = DEFAULT_SERVO_CENTER_US
            state.manipulator_servo2_pwm_value_us = DEFAULT_SERVO_CENTER_US
        elif key in (b"q", b"Q"):
            state.running = False
            break

        print_status(state)


def run_unix_keyboard_loop(state: TeleopState, step: float, servo_step_us: int) -> None:
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
            elif key in ("i", "I"):
                state.manipulator_servo1_pwm_value_us = clamp_servo_us(
                    state.manipulator_servo1_pwm_value_us + servo_step_us
                )
            elif key in ("k", "K"):
                state.manipulator_servo1_pwm_value_us = clamp_servo_us(
                    state.manipulator_servo1_pwm_value_us - servo_step_us
                )
            elif key in ("j", "J"):
                state.manipulator_servo2_pwm_value_us = clamp_servo_us(
                    state.manipulator_servo2_pwm_value_us - servo_step_us
                )
            elif key in ("l", "L"):
                state.manipulator_servo2_pwm_value_us = clamp_servo_us(
                    state.manipulator_servo2_pwm_value_us + servo_step_us
                )
            elif key == " ":
                state.throttle = 0.0
                state.steering = 0.0
                state.manipulator_servo1_pwm_value_us = DEFAULT_SERVO_CENTER_US
                state.manipulator_servo2_pwm_value_us = DEFAULT_SERVO_CENTER_US
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
    parser.add_argument("--step", type=float, default=DEFAULT_STEP, help="Increment per key press for throttle/steering")
    parser.add_argument("--servo-step-us", type=int, default=DEFAULT_SERVO_STEP_US, help="Servo pulse increment per key press")
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
            run_windows_keyboard_loop(state, args.step, args.servo_step_us)
        else:
            run_unix_keyboard_loop(state, args.step, args.servo_step_us)
    except KeyboardInterrupt:
        state.running = False
    finally:
        state.running = False
        sender_thread.join(timeout=1.0)
        print("Teleop client stopped.")


if __name__ == "__main__":
    main()