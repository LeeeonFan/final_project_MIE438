"""
hal.py

Hardware Abstraction Layer for:
- 2 DC motors driven by L298N
- 1 steering servo

Inputs:
    cmd = {
        "left_motor_pwm_value": float in [-1, 1],
        "right_motor_pwm_value": float in [-1, 1],
        "steering_pwm_value_us": int
    }

This module converts controller outputs into GPIO signals.
"""

import pigpio

from config import (
    LEFT_MOTOR_IN1,
    LEFT_MOTOR_IN2,
    LEFT_MOTOR_PWM,
    RIGHT_MOTOR_IN1,
    RIGHT_MOTOR_IN2,
    RIGHT_MOTOR_PWM,
    STEERING_SERVO_PIN,
    MOTOR_PWM_FREQUENCY,
    MOTOR_PWM_RANGE,
    SERVO_MIN_US,
    SERVO_MAX_US,
)
from utils import clamp


class HAL:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Failed to connect to pigpio daemon.")

        # Store pins
        self.left_motor_in1 = LEFT_MOTOR_IN1
        self.left_motor_in2 = LEFT_MOTOR_IN2
        self.left_motor_pwm = LEFT_MOTOR_PWM

        self.right_motor_in1 = RIGHT_MOTOR_IN1
        self.right_motor_in2 = RIGHT_MOTOR_IN2
        self.right_motor_pwm = RIGHT_MOTOR_PWM

        self.steering_servo_pin = STEERING_SERVO_PIN

        # Configure GPIO modes
        self.pi.set_mode(self.left_motor_in1, pigpio.OUTPUT)
        self.pi.set_mode(self.left_motor_in2, pigpio.OUTPUT)
        self.pi.set_mode(self.left_motor_pwm, pigpio.OUTPUT)

        self.pi.set_mode(self.right_motor_in1, pigpio.OUTPUT)
        self.pi.set_mode(self.right_motor_in2, pigpio.OUTPUT)
        self.pi.set_mode(self.right_motor_pwm, pigpio.OUTPUT)

        self.pi.set_mode(self.steering_servo_pin, pigpio.OUTPUT)

        # Configure motor PWM
        self.pi.set_PWM_frequency(self.left_motor_pwm, MOTOR_PWM_FREQUENCY)
        self.pi.set_PWM_frequency(self.right_motor_pwm, MOTOR_PWM_FREQUENCY)

        self.pi.set_PWM_range(self.left_motor_pwm, MOTOR_PWM_RANGE)
        self.pi.set_PWM_range(self.right_motor_pwm, MOTOR_PWM_RANGE)

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
        duty = int(abs(pwm_value) * MOTOR_PWM_RANGE)

        if pwm_value > 0:
            # Forward
            self.pi.write(in1_pin, 1)
            self.pi.write(in2_pin, 0)
        elif pwm_value < 0:
            # Reverse
            self.pi.write(in1_pin, 0)
            self.pi.write(in2_pin, 1)
        else:
            # Stop
            self.pi.write(in1_pin, 0)
            self.pi.write(in2_pin, 0)

        self.pi.set_PWM_dutycycle(pwm_pin, duty)

    def _set_servo(self, pulse_width_us):
        """
        Set steering servo pulse width.

        Parameters
        ----------
        pulse_width_us : int or float
            Servo pulse width in microseconds
        """
        pulse_width_us = int(clamp(pulse_width_us, SERVO_MIN_US, SERVO_MAX_US))
        self.pi.set_servo_pulsewidth(self.steering_servo_pin, pulse_width_us)

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
        self.pi.write(self.left_motor_in1, 0)
        self.pi.write(self.left_motor_in2, 0)
        self.pi.write(self.right_motor_in1, 0)
        self.pi.write(self.right_motor_in2, 0)

        self.pi.set_PWM_dutycycle(self.left_motor_pwm, 0)
        self.pi.set_PWM_dutycycle(self.right_motor_pwm, 0)

    def cleanup(self):
        """
        Stop outputs and release pigpio connection.
        """
        self.stop_all()
        self.pi.set_servo_pulsewidth(self.steering_servo_pin, 0)
        self.pi.stop()