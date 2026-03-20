"""
main.py

Top-level control loop for the robot framework.

Pipeline:
    Command Input
        -> Motion Manager
        -> Motor Controller
        -> Servo Controller
        -> HAL
"""

import time

from config import DT, CONTROL_FREQUENCY
from motion_manager import MotionManager
from motor_controller import MotorController
from servo_controller import ServoController
from hal import HAL


def get_command():
    """
    Placeholder command source.

    Replace this with:
    - keyboard input
    - joystick input
    - network command
    - autonomous planner

    Returns
    -------
    dict
        {
            "throttle": float in [-1, 1],
            "steering": float in [-1, 1],
            "mode": str,
            "timestamp": float
        }
    """
    return {
        "throttle": 0.0,
        "steering": 0.0,
        "mode": "MANUAL",
        "timestamp": time.time(),
    }


def get_motor_feedback():
    """
    Placeholder feedback source.

    Replace this with encoder-based shaft speed measurement.

    Returns
    -------
    dict
        {
            "left_shaft_speed": float,   # rad/s
            "right_shaft_speed": float   # rad/s
        }
    """
    return {
        "left_shaft_speed": 0.0,
        "right_shaft_speed": 0.0,
    }


def main():
    motion_manager = MotionManager()
    motor_controller = MotorController()
    servo_controller = ServoController()
    hal = HAL()

    period = 1.0 / CONTROL_FREQUENCY

    try:
        while True:
            loop_start = time.time()

            # 1. Read command
            cmd = get_command()

            # 2. Motion manager: normalized command -> physical targets
            motion_target = motion_manager.update(cmd)

            # 3. Read feedback for motor controller
            motor_feedback = get_motor_feedback()

            # 4. Motor controller: target shaft speed -> normalized PWM
            motor_target = motor_controller.update(
                cmd={
                    "left_shaft_speed": motion_target["left_shaft_speed"],
                    "right_shaft_speed": motion_target["right_shaft_speed"],
                },
                feedback=motor_feedback,
                dt=DT,
            )

            # 5. Servo controller: steering angle -> servo pulse width
            servo_target = servo_controller.update(
                cmd={
                    "steering_angle": motion_target["steering_angle"]
                }
            )

            # 6. Combine controller outputs for HAL
            hal_cmd = {
                "left_motor_pwm_value": motor_target["left_motor_pwm_value"],
                "right_motor_pwm_value": motor_target["right_motor_pwm_value"],
                "steering_pwm_value_us": servo_target["steering_pwm_value_us"],
            }

            # 7. Send to hardware
            hal.apply(hal_cmd)

            # 8. Maintain loop rate
            elapsed = time.time() - loop_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("Shutting down robot...")

    finally:
        hal.cleanup()


if __name__ == "__main__":
    main()