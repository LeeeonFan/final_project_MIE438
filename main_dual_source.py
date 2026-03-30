"""
main_dual_source.py

Pi-side entry point that preserves the original control pipeline while allowing
switching between two command-input sources:
- CV module
- WASD teleop client

Only the command acquisition stage changes. The downstream pipeline is unchanged:
    selected command source -> MotionManager -> MotorController -> ServoController -> HAL

Controls on the Pi terminal:
    t = switch to teleop source
    c = switch to CV source
    m = toggle source
    q = quit
"""

from __future__ import annotations

import select
import sys
import time

from config import COMMAND_PORT, COMMAND_TIMEOUT_S, CONTROL_FREQUENCY, DT
from hal import HAL
from motion_manager import MotionManager
from motor_controller import MotorController
from servo_controller import ServoController
from command_mux import UDPCommandMux


# New dedicated teleop port. Keep the old COMMAND_PORT for CV.
TELEOP_COMMAND_PORT = 5006
INITIAL_COMMAND_SOURCE = "cv"
PRINT_STATUS_EVERY_S = 1.0


def read_stdin_key_nonblocking() -> str | None:
    if not sys.stdin.isatty():
        return None
    ready, _, _ = select.select([sys.stdin], [], [], 0.0)
    if ready:
        return sys.stdin.read(1)
    return None


def main() -> None:
    motion_manager = MotionManager()
    motor_controller = MotorController()
    servo_controller = ServoController()
    hal = HAL()

    mux = UDPCommandMux(
        cv_port=COMMAND_PORT,
        teleop_port=TELEOP_COMMAND_PORT,
        timeout_s=COMMAND_TIMEOUT_S,
        initial_source=INITIAL_COMMAND_SOURCE,
    )

    period = 1.0 / CONTROL_FREQUENCY
    last_status_print = 0.0

    print(f"Robot control loop listening for CV on UDP port {COMMAND_PORT}")
    print(f"Robot control loop listening for teleop on UDP port {TELEOP_COMMAND_PORT}")
    print(f"Initial active source: {INITIAL_COMMAND_SOURCE}")
    print("Press 'c' for CV, 't' for teleop, 'm' to toggle, 'q' to quit.")

    try:
        while True:
            loop_start = time.time()

            key = read_stdin_key_nonblocking()
            if key == "c":
                mux.switch_source("cv")
                print("\nSwitched active command source to CV")
            elif key == "t":
                mux.switch_source("teleop")
                print("\nSwitched active command source to teleop")
            elif key == "m":
                new_source = mux.toggle_source()
                print(f"\nToggled active command source to {new_source}")
            elif key == "q":
                break

            connected = mux.poll()
            if not connected:
                hal.stop_all()
                now = time.time()
                if now - last_status_print >= PRINT_STATUS_EVERY_S:
                    status = mux.get_status()
                    print(
                        "Watchdog: active source has no recent command. "
                        f"active={status['active_source']} "
                        f"cv_connected={status['cv_connected']} "
                        f"teleop_connected={status['teleop_connected']}"
                    )
                    last_status_print = now

                elapsed = time.time() - loop_start
                sleep_time = period - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                continue

            # Original downstream pipeline starts here and is unchanged in shape.
            cmd = mux.get_command()

            motion_target = motion_manager.update(cmd)

            motor_feedback = mux.get_motor_feedback()

            motor_target = motor_controller.update(
                cmd={
                    "left_shaft_speed": motion_target["left_shaft_speed"],
                    "right_shaft_speed": motion_target["right_shaft_speed"],
                },
                feedback=motor_feedback,
                dt=DT,
            )

            servo_target = servo_controller.update(
                cmd={"steering_angle": motion_target["steering_angle"]}
            )

            hal_cmd = {
                "left_motor_pwm_value": motor_target["left_motor_pwm_value"],
                "right_motor_pwm_value": motor_target["right_motor_pwm_value"],
                "steering_pwm_value_us": servo_target["steering_pwm_value_us"],
            }

            hal.apply(hal_cmd)

            now = time.time()
            if now - last_status_print >= PRINT_STATUS_EVERY_S:
                status = mux.get_status()
                print(
                    f"active={status['active_source']} "
                    f"cv_connected={status['cv_connected']} "
                    f"teleop_connected={status['teleop_connected']}"
                )
                last_status_print = now

            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nShutting down robot...")
    finally:
        hal.cleanup()
        mux.close()


if __name__ == "__main__":
    main()
