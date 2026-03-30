"""
main.py

Top-level control loop for the robot framework.

Receives commands from the laptop CV module or laptop teleop client over UDP
and drives the full control pipeline unchanged:
    UDP recv {throttle, steering, measured_v}
        -> MotionManager
        -> MotorController (PID with camera-based velocity feedback)
        -> ServoController
        -> HAL

Only one command sender should run at a time. Both the CV module and the
teleop client use the same UDP packet format and the same COMMAND_PORT.
"""

import json
import socket
import time

from config import DT, CONTROL_FREQUENCY, COMMAND_PORT, COMMAND_TIMEOUT_S, WHEEL_RADIUS_M
from motion_manager import MotionManager
from motor_controller import MotorController
from servo_controller import ServoController
from hal import HAL


# Shared state: updated each time a UDP packet arrives.
# On timeout, reset to zeros so the robot stops (watchdog).
_latest_packet = {"throttle": 0.0, "steering": 0.0, "measured_v": 0.0}


def receive_packet(sock):
    """Receive one UDP packet and update shared state.

    Returns True if a packet was received, False on timeout.
    """
    global _latest_packet
    try:
        data, _ = sock.recvfrom(1024)
        _latest_packet = json.loads(data.decode())
        return True
    except socket.timeout:
        _latest_packet = {"throttle": 0.0, "steering": 0.0, "measured_v": 0.0}
        return False


def get_command():
    """Build command dict from the latest UDP packet."""
    return {
        "throttle": _latest_packet.get("throttle", 0.0),
        "steering": _latest_packet.get("steering", 0.0),
        "mode": "AUTONOMOUS",
        "timestamp": time.time(),
    }


def get_motor_feedback():
    """Convert measured velocity (m/s) to shaft speed (rad/s).

    Both motors receive the same estimate since the incoming command packet
    carries a single measured body velocity, not individual wheel speeds.
    """
    measured_v = _latest_packet.get("measured_v", 0.0)
    shaft_speed = measured_v / WHEEL_RADIUS_M
    return {
        "left_shaft_speed": shaft_speed,
        "right_shaft_speed": shaft_speed,
    }


def main():
    motion_manager = MotionManager()
    motor_controller = MotorController()
    servo_controller = ServoController()
    hal = HAL()

    # UDP socket for receiving commands from the laptop sender
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", COMMAND_PORT))
    sock.settimeout(COMMAND_TIMEOUT_S)

    period = 1.0 / CONTROL_FREQUENCY

    print(f"Robot control loop listening on UDP port {COMMAND_PORT}")
    print(f"Watchdog timeout: {COMMAND_TIMEOUT_S}s")

    try:
        while True:
            loop_start = time.time()

            # 1. Receive command from laptop (blocks up to COMMAND_TIMEOUT_S)
            connected = receive_packet(sock)
            if not connected:
                hal.stop_all()
                print("Watchdog: no command received, motors stopped.")
                continue

            # 2. Read command
            cmd = get_command()

            # 3. Motion manager: normalized command -> physical targets
            motion_target = motion_manager.update(cmd)

            # 4. Read feedback for motor controller
            motor_feedback = get_motor_feedback()

            # 5. Motor controller: target shaft speed -> normalized PWM
            motor_target = motor_controller.update(
                cmd={
                    "left_shaft_speed": motion_target["left_shaft_speed"],
                    "right_shaft_speed": motion_target["right_shaft_speed"],
                },
                feedback=motor_feedback,
                dt=DT,
            )

            # 6. Servo controller: steering angle -> servo pulse width
            servo_target = servo_controller.update(
                cmd={
                    "steering_angle": motion_target["steering_angle"]
                }
            )

            # 7. Combine controller outputs for HAL
            hal_cmd = {
                "left_motor_pwm_value": motor_target["left_motor_pwm_value"],
                "right_motor_pwm_value": motor_target["right_motor_pwm_value"],
                "steering_pwm_value_us": servo_target["steering_pwm_value_us"],
            }

            # 8. Send to hardware
            hal.apply(hal_cmd)

            # 9. Maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Shutting down robot...")

    finally:
        hal.cleanup()
        sock.close()


if __name__ == "__main__":
    main()
