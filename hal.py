"""
hal.py

Hardware Abstraction Layer with explicit actuator abstractions:

- DCMotorL298N
- PCA9685Driver
- PCA9685Servo

Design:
- The I2C bus (SDA/SCL) is initialized once inside PCA9685Driver.
- The PCA9685 chip is initialized once.
- Each servo instance is attached to one PCA9685 channel.

This keeps the upstream interface compatible with the current robot pipeline.

Expected cmd dictionary:
    {
        "left_motor_pwm_value": float in [-1, 1],
        "right_motor_pwm_value": float in [-1, 1],

        # backward-compatible old key
        "steering_pwm_value_us": int,

        # expanded servo keys
        "servo1_pwm_value_us": int,
        "servo2_pwm_value_us": int,
        "servo3_pwm_value_us": int,
    }
"""

import lgpio
import board
import busio
from adafruit_pca9685 import PCA9685

import config
from utils import clamp

# Pi 5 style from your existing project
GPIO_CHIP = 4


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


class PCA9685Driver:
    """
    Owns the shared I2C bus and the PCA9685 chip.

    This is where SDA/SCL are actually used.
    All servo instances share this single driver.
    """

    def __init__(self, i2c_address, pwm_frequency):
        self.i2c_address = i2c_address
        self.pwm_frequency = pwm_frequency

        # Explicit shared I2C initialization using Pi SDA/SCL pins
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.pca = PCA9685(self.i2c, address=self.i2c_address)
        self.pca.frequency = self.pwm_frequency

    def pulse_us_to_duty_cycle(self, pulse_width_us, min_us, max_us):
        pulse_width_us = clamp(pulse_width_us, min_us, max_us)
        period_us = 1_000_000.0 / float(self.pwm_frequency)
        duty_cycle = int((pulse_width_us / period_us) * 65535.0)
        return max(0, min(65535, duty_cycle))

    def set_channel_pulse_us(self, channel, pulse_width_us, min_us, max_us):
        duty_cycle = self.pulse_us_to_duty_cycle(pulse_width_us, min_us, max_us)
        self.pca.channels[channel].duty_cycle = duty_cycle

    def release_channel(self, channel):
        self.pca.channels[channel].duty_cycle = 0

    def deinit(self):
        self.pca.deinit()


class PCA9685Servo:
    """
    One servo on one PCA9685 channel.
    Uses the shared PCA9685Driver.
    """

    def __init__(self, driver, name, channel, min_us, center_us, max_us):
        self.driver = driver
        self.name = name
        self.channel = channel
        self.min_us = min_us
        self.center_us = center_us
        self.max_us = max_us

        self.center()

    def apply_pulse_us(self, pulse_width_us):
        self.driver.set_channel_pulse_us(
            channel=self.channel,
            pulse_width_us=pulse_width_us,
            min_us=self.min_us,
            max_us=self.max_us,
        )

    def center(self):
        self.apply_pulse_us(self.center_us)

    def release(self):
        self.driver.release_channel(self.channel)


class HAL:
    def __init__(self):
        self.gpio_handle = lgpio.gpiochip_open(GPIO_CHIP)

        self.motor_pwm_frequency = getattr(config, "MOTOR_PWM_FREQUENCY", 1000)
        self.servo_min_us = getattr(config, "SERVO_MIN_US", 1000)
        self.servo_center_us = getattr(config, "SERVO_CENTER_US", 1500)
        self.servo_max_us = getattr(config, "SERVO_MAX_US", 2000)

        self.motors = {}
        self.servos = {}

        self._build_motors()
        self._build_servos()

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

        for mc in motor_configs:
            self.motors[mc["name"]] = DCMotorL298N(
                gpio_handle=self.gpio_handle,
                name=mc["name"],
                in1_pin=mc["in1"],
                in2_pin=mc["in2"],
                pwm_pin=mc["pwm"],
                pwm_frequency=self.motor_pwm_frequency,
            )

    def _build_servos(self):
        pca_i2c_address = getattr(config, "PCA9685_I2C_ADDRESS", 0x40)
        pca_pwm_frequency = getattr(config, "PCA9685_PWM_FREQUENCY", 50)

        # Shared I2C + shared PCA9685 device
        self.servo_driver = PCA9685Driver(
            i2c_address=pca_i2c_address,
            pwm_frequency=pca_pwm_frequency,
        )

        servo_configs = getattr(config, "SERVO_CONFIGS", None)
        if servo_configs is None:
            servo_configs = [
                {"name": "servo1", "channel": 0},
                {"name": "servo2", "channel": 1},
                {"name": "servo3", "channel": 2},
            ]

        for sc in servo_configs:
            self.servos[sc["name"]] = PCA9685Servo(
                driver=self.servo_driver,
                name=sc["name"],
                channel=sc["channel"],
                min_us=sc.get("min_us", self.servo_min_us),
                center_us=sc.get("center_us", self.servo_center_us),
                max_us=sc.get("max_us", self.servo_max_us),
            )

    def apply(self, cmd):
        left_motor_pwm_value = cmd.get("left_motor_pwm_value", 0.0)
        right_motor_pwm_value = cmd.get("right_motor_pwm_value", 0.0)

        if "left_motor" in self.motors:
            self.motors["left_motor"].apply(left_motor_pwm_value)

        if "right_motor" in self.motors:
            self.motors["right_motor"].apply(right_motor_pwm_value)

        servo1_pwm_value_us = cmd.get(
            "servo1_pwm_value_us",
            cmd.get("steering_pwm_value_us", self.servo_center_us),
        )
        servo2_pwm_value_us = cmd.get("servo2_pwm_value_us", self.servo_center_us)
        servo3_pwm_value_us = cmd.get("servo3_pwm_value_us", self.servo_center_us)

        if "servo1" in self.servos:
            self.servos["servo1"].apply_pulse_us(servo1_pwm_value_us)

        if "servo2" in self.servos:
            self.servos["servo2"].apply_pulse_us(servo2_pwm_value_us)

        if "servo3" in self.servos:
            self.servos["servo3"].apply_pulse_us(servo3_pwm_value_us)

    def stop_all(self):
        for motor in self.motors.values():
            motor.stop()

        for servo in self.servos.values():
            servo.center()

    def cleanup(self):
        self.stop_all()

        for servo in self.servos.values():
            servo.release()

        if hasattr(self, "servo_driver"):
            self.servo_driver.deinit()

        lgpio.gpiochip_close(self.gpio_handle)