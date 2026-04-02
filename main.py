"""
Top-level control loop for the robot framework.

Receives commands from the laptop teleop/CV module over UDP and drives the
full control pipeline: MotionManager -> MotorController -> ServoController -> HAL.

Pipeline:
    UDP recv {
        throttle,
        steering,
        measured_v,
        manipulator_servo1_pwm_value_us,
        manipulator_servo2_pwm_value_us
    }
        -> MotionManager
        -> MotorController (PID with camera-based velocity feedback)
        -> ServoController
        -> HAL
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
_latest_packet = {
    "throttle": 0.0,
    "steering": 0.0,
    "measured_v": 0.0,
    "manipulator_servo1_pwm_value_us": 1500,
    "manipulator_servo2_pwm_value_us": 1500,
}

# Debug print throttling
DEBUG_PRINT_INTERVAL_S = 0.2
_last_debug_print_time = 0.0


def debug_print(msg):
    global _last_debug_print_time
    now = time.time()
    if now - _last_debug_print_time >= DEBUG_PRINT_INTERVAL_S:
        print(msg)
        _last_debug_print_time = now


def receive_packet(sock):
    """Receive one UDP packet and update shared state.

    Returns True if a packet was received, False on timeout.
    """
    global _latest_packet
    try:
        data, addr = sock.recvfrom(1024)
        _latest_packet = json.loads(data.decode())

        debug_print(
            "[RX] "
            f"from={addr[0]}:{addr[1]} | "
            f"throttle={_latest_packet.get('throttle', 0.0):.3f}, "
            f"steering={_latest_packet.get('steering', 0.0):.3f}, "
            f"measured_v={_latest_packet.get('measured_v', 0.0):.3f}, "
            f"manipulator_servo1_pwm_value_us={_latest_packet.get('manipulator_servo1_pwm_value_us', 1500)}, "
            f"manipulator_servo2_pwm_value_us={_latest_packet.get('manipulator_servo2_pwm_value_us', 1500)}"
        )
        return True

    except socket.timeout:
        _latest_packet = {
            "throttle": 0.0,
            "steering": 0.0,
            "measured_v": 0.0,
            "manipulator_servo1_pwm_value_us": 1500,
            "manipulator_servo2_pwm_value_us": 1500,
        }
        return False

    except json.JSONDecodeError as e:
        print(f"[RX ERROR] Invalid JSON packet: {e}")
        _latest_packet = {
            "throttle": 0.0,
            "steering": 0.0,
            "measured_v": 0.0,
            "manipulator_servo1_pwm_value_us": 1500,
            "manipulator_servo2_pwm_value_us": 1500,
        }
        return False

    except Exception as e:
        print(f"[RX ERROR] Unexpected receive error: {e}")
        _latest_packet = {
            "throttle": 0.0,
            "steering": 0.0,
            "measured_v": 0.0,
            "manipulator_servo1_pwm_value_us": 1500,
            "manipulator_servo2_pwm_value_us": 1500,
        }
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
    """Convert camera-measured velocity (m/s) to shaft speed (rad/s).

    Both motors receive the same estimate since the camera measures
    overall body velocity, not individual wheel speeds.
    """
    measured_v = _latest_packet.get("measured_v", 0.0)
    shaft_speed = measured_v / WHEEL_RADIUS_M
    return {
        "left_shaft_speed": shaft_speed,
        "right_shaft_speed": shaft_speed,
    }


def get_manipulator_servo_commands():
    """Get manipulator servo pulse-width commands directly from latest packet."""
    return {
        "manipulator_servo1_pwm_value_us": _latest_packet.get("manipulator_servo1_pwm_value_us", 1500),
        "manipulator_servo2_pwm_value_us": _latest_packet.get("manipulator_servo2_pwm_value_us", 1500),
    }


def main():
    motion_manager = MotionManager()
    motor_controller = MotorController()
    servo_controller = ServoController()
    hal = HAL()

    # UDP socket for receiving commands from laptop
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", COMMAND_PORT))
    sock.settimeout(COMMAND_TIMEOUT_S)

    period = 1.0 / CONTROL_FREQUENCY

    print(f"[START] Robot control loop listening on UDP port {COMMAND_PORT}")
    print(f"[START] Watchdog timeout: {COMMAND_TIMEOUT_S}s")
    print(f"[START] Control frequency: {CONTROL_FREQUENCY} Hz")
    print("[START] Waiting for packets...")

    try:
        while True:
            loop_start = time.time()

            # 1. Receive command from laptop (blocks up to COMMAND_TIMEOUT_S)
            connected = receive_packet(sock)
            if not connected:
                hal.stop_all()
                print("[WATCHDOG] No command received, motors stopped.")
                continue

            # 2. Read drive command
            cmd = get_command()
            debug_print(
                "[CMD] "
                f"throttle={cmd['throttle']:.3f}, "
                f"steering={cmd['steering']:.3f}, "
                f"mode={cmd['mode']}"
            )

            # 3. Motion manager: normalized command -> physical targets
            motion_target = motion_manager.update(cmd)
            debug_print(
                "[MOTION TARGET] "
                f"left_shaft_speed={motion_target['left_shaft_speed']:.3f}, "
                f"right_shaft_speed={motion_target['right_shaft_speed']:.3f}, "
                f"steering_angle={motion_target['steering_angle']:.3f}"
            )

            # 4. Read feedback for motor controller
            motor_feedback = get_motor_feedback()
            debug_print(
                "[FEEDBACK] "
                f"left_shaft_speed={motor_feedback['left_shaft_speed']:.3f}, "
                f"right_shaft_speed={motor_feedback['right_shaft_speed']:.3f}"
            )

            # 5. Motor controller: target shaft speed -> normalized motor command
            motor_target = motor_controller.update(
                cmd={
                    "left_shaft_speed": motion_target["left_shaft_speed"],
                    "right_shaft_speed": motion_target["right_shaft_speed"],
                },
                feedback=motor_feedback,
                dt=DT,
            )
            debug_print(
                "[MOTOR TARGET] "
                f"left_motor_pwm_value={motor_target['left_motor_pwm_value']:.3f}, "
                f"right_motor_pwm_value={motor_target['right_motor_pwm_value']:.3f}"
            )

            # 6. Steering servo controller: steering angle -> steering servo pulse width
            servo_target = servo_controller.update(
                cmd={
                    "steering_angle": motion_target["steering_angle"]
                }
            )
            debug_print(
                "[SERVO TARGET] "
                f"steering_pwm_value_us={servo_target['steering_pwm_value_us']}"
            )

            # 7. Read manipulator servo commands directly from packet
            manipulator_servo_target = get_manipulator_servo_commands()
            debug_print(
                "[MANIPULATOR SERVO TARGET] "
                f"manipulator_servo1_pwm_value_us={manipulator_servo_target['manipulator_servo1_pwm_value_us']}, "
                f"manipulator_servo2_pwm_value_us={manipulator_servo_target['manipulator_servo2_pwm_value_us']}"
            )

            # 8. Combine controller outputs for HAL
            hal_cmd = {
                "left_motor_pwm_value": motor_target["left_motor_pwm_value"],
                "right_motor_pwm_value": motor_target["right_motor_pwm_value"],
                "steering_pwm_value_us": servo_target["steering_pwm_value_us"],
                "manipulator_servo1_pwm_value_us": manipulator_servo_target["manipulator_servo1_pwm_value_us"],
                "manipulator_servo2_pwm_value_us": manipulator_servo_target["manipulator_servo2_pwm_value_us"],
            }

            debug_print(
                "[HAL CMD] "
                f"left_motor_pwm_value={hal_cmd['left_motor_pwm_value']:.3f}, "
                f"right_motor_pwm_value={hal_cmd['right_motor_pwm_value']:.3f}, "
                f"steering_pwm_value_us={hal_cmd['steering_pwm_value_us']}, "
                f"manipulator_servo1_pwm_value_us={hal_cmd['manipulator_servo1_pwm_value_us']}, "
                f"manipulator_servo2_pwm_value_us={hal_cmd['manipulator_servo2_pwm_value_us']}"
            )

            # 9. Send to hardware
            hal.apply(hal_cmd)

            # 10. Maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] KeyboardInterrupt received, shutting down robot...")

    finally:
        hal.cleanup()
        sock.close()
        print("[SHUTDOWN] HAL cleaned up, socket closed.")


if __name__ == "__main__":
    main()