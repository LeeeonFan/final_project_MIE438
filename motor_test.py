import lgpio
import time

GPIO_CHIP = 4  # Pi 5 (use 0 for Pi 4 or earlier)
PWM_FREQUENCY = 1000  # Hz

# Pin assignments from config.py MOTOR_CONFIGS
LEFT_IN1 = 17
LEFT_IN2 = 22
LEFT_PWM = 10

RIGHT_IN1 = 23
RIGHT_IN2 = 24
RIGHT_PWM = 9

h = lgpio.gpiochip_open(GPIO_CHIP)

# Claim direction pins as outputs
for pin in [LEFT_IN1, LEFT_IN2, RIGHT_IN1, RIGHT_IN2]:
    lgpio.gpio_claim_output(h, pin)


def motor_control(motor, direction, speed):
    """Control left or right motor with direction and speed (0-100 duty %)."""
    if motor == 'left':
        in1, in2, pwm_pin = LEFT_IN1, LEFT_IN2, LEFT_PWM
    else:
        in1, in2, pwm_pin = RIGHT_IN1, RIGHT_IN2, RIGHT_PWM

    if direction == 'forward':
        lgpio.gpio_write(h, in1, 1)
        lgpio.gpio_write(h, in2, 0)
    else:
        lgpio.gpio_write(h, in1, 0)
        lgpio.gpio_write(h, in2, 1)

    lgpio.tx_pwm(h, pwm_pin, PWM_FREQUENCY, speed)


def motor_stop(motor):
    if motor == 'left':
        in1, in2, pwm_pin = LEFT_IN1, LEFT_IN2, LEFT_PWM
    else:
        in1, in2, pwm_pin = RIGHT_IN1, RIGHT_IN2, RIGHT_PWM

    lgpio.gpio_write(h, in1, 0)
    lgpio.gpio_write(h, in2, 0)
    lgpio.tx_pwm(h, pwm_pin, PWM_FREQUENCY, 0)


try:
    print("Left motor forward 75%")
    motor_control('left', 'forward', 75)
    time.sleep(2)

    print("Left motor backward 50%")
    motor_control('left', 'backward', 50)
    time.sleep(2)

    print("Right motor forward 75%")
    motor_control('right', 'forward', 75)
    time.sleep(2)

    print("Right motor backward 50%")
    motor_control('right', 'backward', 50)
    time.sleep(2)

finally:
    motor_stop('left')
    motor_stop('right')
    lgpio.gpiochip_close(h)
    print("Cleanup done")