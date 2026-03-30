"""
test_hal_servo.py

Servo-only test through the HAL layer.

This script assumes your current HAL supports:
    hal.apply({
        "left_motor_pwm_value": ...,
        "right_motor_pwm_value": ...,
        "steering_pwm_value_us": ...,
    })

It keeps both motors at 0 and only moves the steering servo.
"""

import time

from hal import HAL
from config import SERVO_MIN_US, SERVO_CENTER_US, SERVO_MAX_US

MOVE_DELAY_S = 1.5


def apply_servo(hal, pulse_us, label):
    cmd = {
        "left_motor_pwm_value": 0.0,
        "right_motor_pwm_value": 0.0,
        "steering_pwm_value_us": pulse_us,
    }
    print(f"\n[TEST] {label}")
    print(f"[CMD] {cmd}")
    hal.apply(cmd)
    time.sleep(MOVE_DELAY_S)


def main():
    hal = HAL()

    try:
        print("[START] HAL servo test starting...")

        apply_servo(hal, SERVO_CENTER_US, f"Center ({SERVO_CENTER_US} us)")
        apply_servo(hal, SERVO_MIN_US, f"Min pulse ({SERVO_MIN_US} us)")
        apply_servo(hal, SERVO_MAX_US, f"Max pulse ({SERVO_MAX_US} us)")
        apply_servo(hal, SERVO_CENTER_US, f"Back to center ({SERVO_CENTER_US} us)")

        print("\n[DONE] Servo HAL test completed.")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Stopping test...")

    finally:
        hal.cleanup()
        print("[CLEANUP] HAL cleaned up.")


if __name__ == "__main__":
    main()