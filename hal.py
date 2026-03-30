"""
hal.py

Hardware Abstraction Layer with:
- 2 DC motors through L298N + lgpio
- 1 standard servo through Adafruit ServoKit (PCA9685 over I2C)

This version keeps the existing HAL.apply(cmd) interface compatible with
the current pipeline.

Expected cmd dictionary:
    {
        "left_motor_pwm_value": float in [-1, 1],
        "right_motor_pwm_value": float in [-1, 1],
        "steering_pwm_value_us": int,
    }
"""

import lgpio
import board
import busio
from adafruit_servokit import ServoKit

import config
from utils import clamp

GPIO_CHIP = 4  # Pi 5


class DCMotorL298N:
    def __init__(self, gpio_handle, name, in1_pin, in2_pin, pwm_pin, pwm_frequency):
        self.gpio_handle = gpio_handle
        self.name = name
        self.in1_pin = in1_pin
        self.in2_pin = in2_pin
        self.pwm_pin = pwm_pin
        self.pwm_frequency = pwm_frequency

        lgpio.gpio_claim_output(self.gpio_handle, self.in1_pin)
        lgpio.gpio_claim_output(self.gpio_handle, self.in2_pin)

        self.stop()

    def apply(self, pwm_value: float):
        pwm_value = clamp(pwm_value, -1.0, 1.0)
        duty_percent = abs(pwm_value) * 100.0

        if pwm_value > 0:
            lgpio.gpio_write(self.gpio_handle, self.in1_pin, 1)
            lgpio.gpio_write(self.gpio_handle, self.in2_pin, 0)
        elif pwm_value < 0:
            lgpio.gpio_write(self.gpio_handle, self.in1_pin, 0)
            lgpio.gpio_write(self.gpio_handle, self.in2_pin, 1)
        else:
            lgpio.gpio_write(self.gpio_handle, self.in1_pin, 0)
            lgpio.gpio_write(self.gpio_handle, self.in2_pin, 0)

        lgpio.tx_pwm(self.gpio_handle, self.pwm_pin, self.pwm_frequency, duty_percent)

    def stop(self):
        lgpio.gpio_write(self.gpio_handle, self.in1_pin, 0)
        lgpio.gpio_write(self.gpio_handle, self.in2_pin, 0)
        lgpio.tx_pwm(self.gpio_handle, self.pwm_pin, self.pwm_frequency, 0.0)


class ServoKitDriver:
    """
    Owns the shared I2C bus and ServoKit object.
    """

    def __init__(self, channels: int, address: int, frequency: int):
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.kit = ServoKit(
            channels=channels,
            i2c=self.i2c,
            address=address,
            frequency=frequency,
        )


class ServoKitServo:
    """
    One standard servo on one ServoKit channel.

    Upstream command is pulse width in microseconds.
    Internally we calibrate pulse range and convert pulse width to angle.
    """

    def __init__(
        self,
        driver: ServoKitDriver,
        channel: int,
        min_us: int,
        center_us: int,
        max_us: int,
        actuation_range: float = 180.0,
    ):
        self.driver = driver
        self.channel = channel
        self.min_us = min_us
        self.center_us = center_us
        self.max_us = max_us
        self.actuation_range = actuation_range

        self.servo = self.driver.kit.servo[self.channel]
        self.servo.actuation_range = self.actuation_range
        self.servo.set_pulse_width_range(self.min_us, self.max_us)

        self.center()

    def _pulse_us_to_angle(self, pulse_width_us: int) -> float:
        pulse_width_us = clamp(pulse_width_us, self.min_us, self.max_us)
        span_us = self.max_us - self.min_us
        if span_us <= 0:
            return self.actuation_range / 2.0

        normalized = (pulse_width_us - self.min_us) / span_us
        return normalized * self.actuation_range

    def apply_pulse_us(self, pulse_width_us: int):
        angle = self._pulse_us_to_angle(pulse_width_us)
        self.servo.angle = angle

    def center(self):
        self.apply_pulse_us(self.center_us)

    def release(self):
        self.servo.angle = None


class HAL:
    def __init__(self):
        self.gpio_handle = lgpio.gpiochip_open(GPIO_CHIP)

        self.motor_pwm_frequency = getattr(config, "MOTOR_PWM_FREQUENCY", 1000)

        self.servo_min_us = getattr(config, "SERVO_MIN_US", 1000)
        self.servo_center_us = getattr(config, "SERVO_CENTER_US", 1500)
        self.servo_max_us = getattr(config, "SERVO_MAX_US", 2000)
        self.servo_actuation_range = getattr(config, "SERVO_ACTUATION_RANGE", 180)

        self._build_motors()
        self._build_servo()

        self.stop_all()

    def _build_motors(self):
        motor_configs = getattr(config, "MOTOR_CONFIGS", None)
        if motor_configs is None:
            motor_configs = [
                {
                    "name": "left_motor",
                    "in1": config.LEFT_MOTOR_IN1,
                    "in2": config.LEFT_MOTOR_IN2,
                    "pwm": config.LEFT_MOTOR_PWM,
                },
                {
                    "name": "right_motor",
                    "in1": config.RIGHT_MOTOR_IN1,
                    "in2": config.RIGHT_MOTOR_IN2,
                    "pwm": config.RIGHT_MOTOR_PWM,
                },
            ]

        self.left_motor = DCMotorL298N(
            gpio_handle=self.gpio_handle,
            name=motor_configs[0]["name"],
            in1_pin=motor_configs[0]["in1"],
            in2_pin=motor_configs[0]["in2"],
            pwm_pin=motor_configs[0]["pwm"],
            pwm_frequency=self.motor_pwm_frequency,
        )

        self.right_motor = DCMotorL298N(
            gpio_handle=self.gpio_handle,
            name=motor_configs[1]["name"],
            in1_pin=motor_configs[1]["in1"],
            in2_pin=motor_configs[1]["in2"],
            pwm_pin=motor_configs[1]["pwm"],
            pwm_frequency=self.motor_pwm_frequency,
        )

    def _build_servo(self):
        channels = getattr(config, "PCA9685_CHANNELS", 16)
        address = getattr(config, "PCA9685_I2C_ADDRESS", 0x40)
        frequency = getattr(config, "PCA9685_PWM_FREQUENCY", 50)
        servo_channel = getattr(config, "SERVO1_CHANNEL", 0)

        self.servo_driver = ServoKitDriver(
            channels=channels,
            address=address,
            frequency=frequency,
        )

        self.steering_servo = ServoKitServo(
            driver=self.servo_driver,
            channel=servo_channel,
            min_us=self.servo_min_us,
            center_us=self.servo_center_us,
            max_us=self.servo_max_us,
            actuation_range=self.servo_actuation_range,
        )

    def apply(self, cmd):
        left_motor_pwm_value = cmd.get("left_motor_pwm_value", 0.0)
        right_motor_pwm_value = cmd.get("right_motor_pwm_value", 0.0)
        steering_pwm_value_us = cmd.get("steering_pwm_value_us", self.servo_center_us)

        self.left_motor.apply(left_motor_pwm_value)
        self.right_motor.apply(right_motor_pwm_value)
        self.steering_servo.apply_pulse_us(steering_pwm_value_us)

    def stop_all(self):
        self.left_motor.stop()
        self.right_motor.stop()
        self.steering_servo.center()

    def cleanup(self):
        self.stop_all()
        self.steering_servo.release()
        lgpio.gpiochip_close(self.gpio_handle)