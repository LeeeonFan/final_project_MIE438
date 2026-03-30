"""
test_motors_direct.py

Standalone direct test for 2 DC motors through L298N using lgpio.

This version reads motor pin settings from:
    MOTOR_CONFIGS
    MOTOR_PWM_FREQUENCY

Tests:
1. Left motor forward
2. Left motor reverse
3. Right motor forward
4. Right motor reverse
5. Both motors forward
6. Both motors reverse
7. Stop
"""

import time
import lgpio

from config import MOTOR_CONFIGS, MOTOR_PWM_FREQUENCY

GPIO_CHIP = 4   # Pi 5; use 0 on older Pi models

TEST_PWM = 80.0       # duty cycle percent, 0 to 100
TEST_DURATION_S = 2.0
STOP_DURATION_S = 1.0


left_cfg = MOTOR_CONFIGS[0]
right_cfg = MOTOR_CONFIGS[1]

LEFT_MOTOR_IN1 = left_cfg["in1"]
LEFT_MOTOR_IN2 = left_cfg["in2"]
LEFT_MOTOR_PWM = left_cfg["pwm"]

RIGHT_MOTOR_IN1 = right_cfg["in1"]
RIGHT_MOTOR_IN2 = right_cfg["in2"]
RIGHT_MOTOR_PWM = right_cfg["pwm"]


def set_motor(h, in1, in2, pwm_pin, pwm_percent):
    """
    Drive one motor with L298N.

    pwm_percent:
        positive -> forward
        negative -> reverse
        zero     -> stop
    """
    pwm_percent = max(-100.0, min(100.0, pwm_percent))
    duty = abs(pwm_percent)

    if pwm_percent > 0:
        lgpio.gpio_write(h, in1, 1)
        lgpio.gpio_write(h, in2, 0)
    elif pwm_percent < 0:
        lgpio.gpio_write(h, in1, 0)
        lgpio.gpio_write(h, in2, 1)
    else:
        lgpio.gpio_write(h, in1, 0)
        lgpio.gpio_write(h, in2, 0)

    lgpio.tx_pwm(h, pwm_pin, MOTOR_PWM_FREQUENCY, duty)


def stop_all(h):
    set_motor(h, LEFT_MOTOR_IN1, LEFT_MOTOR_IN2, LEFT_MOTOR_PWM, 0.0)
    set_motor(h, RIGHT_MOTOR_IN1, RIGHT_MOTOR_IN2, RIGHT_MOTOR_PWM, 0.0)


def run_step(h, label, left_pwm, right_pwm, duration_s):
    print(f"\n[TEST] {label}")
    print(f"  left_pwm_percent  = {left_pwm}")
    print(f"  right_pwm_percent = {right_pwm}")

    set_motor(h, LEFT_MOTOR_IN1, LEFT_MOTOR_IN2, LEFT_MOTOR_PWM, left_pwm)
    set_motor(h, RIGHT_MOTOR_IN1, RIGHT_MOTOR_IN2, RIGHT_MOTOR_PWM, right_pwm)
    time.sleep(duration_s)


def main():
    print("[INFO] Using config:")
    print(f"  LEFT  motor: IN1={LEFT_MOTOR_IN1}, IN2={LEFT_MOTOR_IN2}, PWM={LEFT_MOTOR_PWM}")
    print(f"  RIGHT motor: IN1={RIGHT_MOTOR_IN1}, IN2={RIGHT_MOTOR_IN2}, PWM={RIGHT_MOTOR_PWM}")
    print(f"  PWM frequency: {MOTOR_PWM_FREQUENCY} Hz")
    print(f"  GPIO chip: {GPIO_CHIP}")

    h = lgpio.gpiochip_open(GPIO_CHIP)

    try:
        print("\n[START] Direct L298N motor test starting...")

        lgpio.gpio_claim_output(h, LEFT_MOTOR_IN1)
        lgpio.gpio_claim_output(h, LEFT_MOTOR_IN2)
        lgpio.gpio_claim_output(h, RIGHT_MOTOR_IN1)
        lgpio.gpio_claim_output(h, RIGHT_MOTOR_IN2)

        stop_all(h)
        time.sleep(1.0)

        run_step(h, "Left motor forward",  TEST_PWM, 0.0, TEST_DURATION_S)
        run_step(h, "Stop",                0.0, 0.0, STOP_DURATION_S)

        run_step(h, "Left motor reverse", -TEST_PWM, 0.0, TEST_DURATION_S)
        run_step(h, "Stop",                0.0, 0.0, STOP_DURATION_S)

        run_step(h, "Right motor forward", 0.0, TEST_PWM, TEST_DURATION_S)
        run_step(h, "Stop",                0.0, 0.0, STOP_DURATION_S)

        run_step(h, "Right motor reverse", 0.0, -TEST_PWM, TEST_DURATION_S)
        run_step(h, "Stop",                0.0, 0.0, STOP_DURATION_S)

        run_step(h, "Both motors forward", TEST_PWM, TEST_PWM, TEST_DURATION_S)
        run_step(h, "Stop",                0.0, 0.0, STOP_DURATION_S)

        run_step(h, "Both motors reverse", -TEST_PWM, -TEST_PWM, TEST_DURATION_S)
        run_step(h, "Stop",                 0.0, 0.0, STOP_DURATION_S)

        print("\n[DONE] Direct motor test completed.")

    except KeyboardInterrupt:
        print("\n[INTERRUPT] Stopping test...")

    finally:
        stop_all(h)
        lgpio.gpiochip_close(h)
        print("[CLEANUP] Motors stopped, gpiochip closed.")


if __name__ == "__main__":
    main()