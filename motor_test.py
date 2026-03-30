"""
test_hal.py

Standalone hardware test for the 1-servo HAL.

Tests:
1. Servo center
2. Servo left
3. Servo right
4. Servo back to center
5. Left motor forward
6. Right motor forward
7. Both motors forward
8. Stop everything
"""

import time

from hal import HAL
from config import SERVO_CENTER_US, SERVO_MIN_US, SERVO_MAX_US


SERVO_MOVE_DELAY_S = 1.5
MOTOR_TEST_DELAY_S = 1.5
MOTOR_TEST_PWM = 0.25   # gentle motor test


def apply_and_wait(hal, cmd, delay_s, label):
    print(f"\n[TEST] {label}")
    print(f"[CMD] {cmd}")
    hal.apply(cmd)
    time.sleep(delay_s)


def main():
    hal = HAL()

    try:
        print("[START] HAL 1-servo test starting...")

        # 1. Center everything
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            SERVO_MOVE_DELAY_S,
            "Servo center",
        )

        # 2. Servo to minimum pulse
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_MIN_US,
            },
            SERVO_MOVE_DELAY_S,
            f"Servo to min pulse ({SERVO_MIN_US} us)",
        )

        # 3. Servo to maximum pulse
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_MAX_US,
            },
            SERVO_MOVE_DELAY_S,
            f"Servo to max pulse ({SERVO_MAX_US} us)",
        )

        # 4. Servo back to center
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            SERVO_MOVE_DELAY_S,
            "Servo back to center",
        )

        # 5. Left motor forward only
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": MOTOR_TEST_PWM,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            MOTOR_TEST_DELAY_S,
            f"Left motor forward ({MOTOR_TEST_PWM})",
        )

        # Stop between tests
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            0.75,
            "Stop after left motor test",
        )

        # 6. Right motor forward only
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": MOTOR_TEST_PWM,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            MOTOR_TEST_DELAY_S,
            f"Right motor forward ({MOTOR_TEST_PWM})",
        )

        # Stop between tests
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            0.75,
            "Stop after right motor test",
        )

        # 7. Both motors forward
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": MOTOR_TEST_PWM,
                "right_motor_pwm_value": MOTOR_TEST_PWM,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            MOTOR_TEST_DELAY_S,
            f"Both motors forward ({MOTOR_TEST_PWM})",
        )

        # 8. Final stop
        apply_and_wait(
            hal,
            {
                "left_motor_pwm_value": 0.0,
                "right_motor_pwm_value": 0.0,
                "steering_pwm_value_us": SERVO_CENTER_US,
            },
            1.0,
            "Final stop and servo center",
        )

        print("\n[DONE] HAL test completed.")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Stopping test...")

    finally:
        hal.cleanup()
        print("[CLEANUP] HAL cleaned up.")


if __name__ == "__main__":
    main()