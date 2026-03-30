#!/usr/bin/env python3
"""
PS5 controller → robot bridge.

Reads PS5 controller input via ControllerManager and streams
throttle/steering commands to the Pi over UDP (same format as teleop_client.py).

Control mapping:
  - Left Stick Y: throttle (forward/backward)
  - Right Stick X: steering (left/right)

Alternatively, set --triggers flag to use:
  - R2: forward, L2: backward
  - Right Stick X: steering

Usage:
  python controller_servo_example.py
  python controller_servo_example.py --pi-ip 192.168.1.50 --port 5006
  python controller_servo_example.py --triggers
"""

import argparse
import json
import os
import socket
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from controller.controller import ControllerManager

DEFAULT_PI_IP = "172.20.10.3"
DEFAULT_PORT = 5006
DEFAULT_SEND_HZ = 20.0


def parse_args():
    parser = argparse.ArgumentParser(
        description="PS5 controller teleoperation client"
    )
    parser.add_argument(
        "--pi-ip", default=DEFAULT_PI_IP,
        help=f"Pi IP address (default: {DEFAULT_PI_IP})"
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"UDP command port on the Pi (default: {DEFAULT_PORT})"
    )
    parser.add_argument(
        "--send-hz", type=float, default=DEFAULT_SEND_HZ,
        help=f"Command send rate in Hz (default: {DEFAULT_SEND_HZ})"
    )
    parser.add_argument(
        "--triggers", action="store_true",
        help="Use R2/L2 triggers for throttle instead of left stick"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    period = 1.0 / args.send_hz

    print("Initializing ControllerManager...")
    controller = ControllerManager(use_triggers_for_throttle=args.triggers)

    print("Waiting for controller connection...")
    while not controller.is_connected():
        import pygame
        pygame.event.pump()
        time.sleep(0.1)

    print(f"Controller connected: {controller.joystick.get_name()}")
    print(f"Sending to {args.pi_ip}:{args.port} at {args.send_hz} Hz")
    print("\nControl mapping:")
    if args.triggers:
        print("  R2: forward throttle  |  L2: reverse throttle")
    else:
        print("  Left Stick Y: throttle (up=forward, down=backward)")
    print("  Right Stick X: steering (left=-1, right=+1)")
    print("  Steering angle range: +/-{:.0f} deg".format(
        controller.servo_controller.max_steering_angle
    ))
    print("\nPress Ctrl+C to stop\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        while True:
            loop_start = time.time()

            import pygame
            pygame.event.pump()

            payload = controller.get_command_payload()

            if payload:
                throttle = payload["throttle"]
                steering = payload["steering"]
                pwm = payload["steering_pwm_us"]
                angle = payload["steering_angle"]

                udp_packet = {
                    "throttle": throttle,
                    "steering": steering,
                    "measured_v": 0.0,
                }
                sock.sendto(
                    json.dumps(udp_packet).encode("utf-8"),
                    (args.pi_ip, args.port),
                )

                sys.stdout.write(
                    f"\rthrottle={throttle:+.2f}  steering={steering:+.2f}  "
                    f"angle={angle:+.1f} deg  pwm={pwm} us"
                    "        "
                )
                sys.stdout.flush()

            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        stop_packet = {"throttle": 0.0, "steering": 0.0, "measured_v": 0.0}
        try:
            sock.sendto(
                json.dumps(stop_packet).encode("utf-8"),
                (args.pi_ip, args.port),
            )
        except OSError:
            pass
        sock.close()
        print("Controller client stopped.")


if __name__ == "__main__":
    main()
