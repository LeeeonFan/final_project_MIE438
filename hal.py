"""
hal.py

Hardware Abstraction Layer for:
- 2 DC motors driven by L298N
- 1 steering servo

Uses lgpio (compatible with Raspberry Pi 5).

Inputs:
    cmd = {
        "left_motor_pwm_value": float in [-1, 1],
        "right_motor_pwm_value": float in [-1, 1],
        "steering_pwm_value_us": int
    }

This module converts controller outputs into GPIO signals.
"""

import lgpio

from config import (
    LEFT_MOTOR_IN1,
    LEFT_MOTOR_IN2,
    LEFT_MOTOR_PWM,
    RIGHT_MOTOR_IN1,
    RIGHT_MOTOR_IN2,
    RIGHT_MOTOR_PWM,
    STEERING_SERVO_PIN,
    MOTOR_PWM_FREQUENCY,
    SERVO_MIN_US,
    SERVO_MAX_US,
)
from utils import clamp

# GPIO chip number: 4 for Pi 5, 0 for Pi 4 and earlier
GPIO_CHIP = 4


class HAL:
    def __init__(self):
        self.h = lgpio.gpiochip_open(GPIO_CHIP)

        # Store pins
        self.left_motor_in1 = LEFT_MOTOR_IN1
        self.left_motor_in2 = LEFT_MOTOR_IN2
        self.left_motor_pwm = LEFT_MOTOR_PWM

        self.right_motor_in1 = RIGHT_MOTOR_IN1
        self.right_motor_in2 = RIGHT_MOTOR_IN2
        self.right_motor_pwm = RIGHT_MOTOR_PWM

        self.steering_servo_pin = STEERING_SERVO_PIN

        # Claim direction pins as outputs
        lgpio.gpio_claim_output(self.h, self.left_motor_in1)
        lgpio.gpio_claim_output(self.h, self.left_motor_in2)
        lgpio.gpio_claim_output(self.h, self.right_motor_in1)
        lgpio.gpio_claim_output(self.h, self.right_motor_in2)

        # Initialize outputs to safe state
        self.stop_all()

    def _set_dc_motor(self, pwm_value, in1_pin, in2_pin, pwm_pin):
        """
        Set one DC motor using L298N.

        Parameters
        ----------
        pwm_value : float
            Normalized motor command in [-1, 1]
        in1_pin : int
            Direction pin 1
        in2_pin : int
            Direction pin 2
        pwm_pin : int
            PWM enable pin
        """
        pwm_value = clamp(pwm_value, -1.0, 1.0)
        duty_percent = abs(pwm_value) * 100.0

        if pwm_value > 0:
            # Forward
            lgpio.gpio_write(self.h, in1_pin, 1)
            lgpio.gpio_write(self.h, in2_pin, 0)
        elif pwm_value < 0:
            # Reverse
            lgpio.gpio_write(self.h, in1_pin, 0)
            lgpio.gpio_write(self.h, in2_pin, 1)
        else:
            # Stop
            lgpio.gpio_write(self.h, in1_pin, 0)
            lgpio.gpio_write(self.h, in2_pin, 0)

        lgpio.tx_pwm(self.h, pwm_pin, MOTOR_PWM_FREQUENCY, duty_percent)

    def _set_servo(self, pulse_width_us):
        """
        Set steering servo pulse width.

        Parameters
        ----------
        pulse_width_us : int or float
            Servo pulse width in microseconds
        """
        pulse_width_us = int(clamp(pulse_width_us, SERVO_MIN_US, SERVO_MAX_US))
        lgpio.tx_servo(self.h, self.steering_servo_pin, pulse_width_us)

    def apply(self, cmd):
        """
        Apply full hardware command.

        Parameters
        ----------
        cmd : dict
            {
                "left_motor_pwm_value": float in [-1, 1],
                "right_motor_pwm_value": float in [-1, 1],
                "steering_pwm_value_us": int
            }
        """
        left_motor_pwm_value = cmd.get("left_motor_pwm_value", 0.0)
        right_motor_pwm_value = cmd.get("right_motor_pwm_value", 0.0)
        steering_pwm_value_us = cmd.get("steering_pwm_value_us", 1500)

        self._set_dc_motor(
            left_motor_pwm_value,
            self.left_motor_in1,
            self.left_motor_in2,
            self.left_motor_pwm,
        )

        self._set_dc_motor(
            right_motor_pwm_value,
            self.right_motor_in1,
            self.right_motor_in2,
            self.right_motor_pwm,
        )

        self._set_servo(steering_pwm_value_us)

    def stop_all(self):
        """
        Stop both motors and center/hold servo safely.
        """
        lgpio.gpio_write(self.h, self.left_motor_in1, 0)
        lgpio.gpio_write(self.h, self.left_motor_in2, 0)
        lgpio.gpio_write(self.h, self.right_motor_in1, 0)
        lgpio.gpio_write(self.h, self.right_motor_in2, 0)

        lgpio.tx_pwm(self.h, self.left_motor_pwm, MOTOR_PWM_FREQUENCY, 0)
        lgpio.tx_pwm(self.h, self.right_motor_pwm, MOTOR_PWM_FREQUENCY, 0)

    def cleanup(self):
        """
        Stop outputs and release GPIO handle.
        """
        self.stop_all()
        lgpio.tx_servo(self.h, self.steering_servo_pin, 0)
        lgpio.gpiochip_close(self.h)