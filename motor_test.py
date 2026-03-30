"""
test_hal_motors.py

Motor-only test through the HAL layer.

This script assumes:
- HAL drives motors through direct GPIO enable pins (no tx_pwm)
- HAL still accepts:
    "left_motor_pwm_value"
    "right_motor_pwm_value"
    "steering_pwm_value_us"

Tests:
1. Left motor forward
2. Stop
3. Left motor reverse
4. Stop
5. Right motor forward
6. Stop
7. Right motor reverse
8. Stop
9. Both motors forward
10. Stop
11. Both motors reverse
12. Stop
"""

import time

from hal import HAL
from config import SERVO_CENTER_US

TEST_DURATION_S = 2.0
STOP_DURATION_S = 1.0


def apply_cmd(hal, left, right, label, duration_s):
    cmd = {
        "left_motor_pwm_value": left,
        "right_motor_pwm_value": right,
        "steering_pwm_value_us": SERVO_CENTER_US,
    }
    print(f"\n[TEST] {label}")
    print(f"[CMD] {cmd}")
    hal.apply(cmd)
    time.sleep(duration_s)


def main():
    hal = HAL()

    try:
        print("[START] HAL motor test starting...")

        apply_cmd(hal,  1.0,  0.0, "Left motor forward",  TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Stop",                STOP_DURATION_S)

        apply_cmd(hal, -1.0,  0.0, "Left motor reverse",  TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Stop",                STOP_DURATION_S)

        apply_cmd(hal,  0.0,  1.0, "Right motor forward", TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Stop",                STOP_DURATION_S)

        apply_cmd(hal,  0.0, -1.0, "Right motor reverse", TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Stop",                STOP_DURATION_S)

        apply_cmd(hal,  1.0,  1.0, "Both motors forward", TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Stop",                STOP_DURATION_S)

        apply_cmd(hal, -1.0, -1.0, "Both motors reverse", TEST_DURATION_S)
        apply_cmd(hal,  0.0,  0.0, "Final stop",          STOP_DURATION_S)

        print("\n[DONE] HAL motor test completed.")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Stopping test...")

    finally:
        hal.cleanup()
        print("[CLEANUP] HAL cleaned up.")


if __name__ == "__main__":
    main()