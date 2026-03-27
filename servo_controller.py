"""
servo_controller.py

Converts desired steering angle into servo pulse width.
"""

from config import (
    MAX_STEERING_ANGLE,
    SERVO_MIN_US,
    SERVO_CENTER_US,
    SERVO_MAX_US,
)
from utils import clamp


class ServoController:
    def __init__(self):
        self.max_steering_angle = MAX_STEERING_ANGLE
        self.servo_min_us = SERVO_MIN_US
        self.servo_center_us = SERVO_CENTER_US
        self.servo_max_us = SERVO_MAX_US

    def steering_angle_to_pwm(self, steering_angle):
        steering_angle = clamp(
            steering_angle,
            -self.max_steering_angle,
            self.max_steering_angle,
        )

        if self.max_steering_angle == 0:
            return self.servo_center_us

        if steering_angle >= 0:
            pulse_width_us = self.servo_center_us + (
                steering_angle / self.max_steering_angle
            ) * (self.servo_max_us - self.servo_center_us)
        else:
            pulse_width_us = self.servo_center_us + (
                steering_angle / self.max_steering_angle
            ) * (self.servo_center_us - self.servo_min_us)

        pulse_width_us = clamp(
            pulse_width_us,
            self.servo_min_us,
            self.servo_max_us,
        )

        return int(pulse_width_us)

    def update(self, cmd):
        """
        Parameters
        ----------
        cmd : dict
            {
                "steering_angle": float   # degrees
            }

        Returns
        -------
        dict
            {
                "steering_pwm_value_us": int   # microseconds
            }
        """
        steering_angle = cmd.get("steering_angle", 0.0)
        steering_pwm_value_us = self.steering_angle_to_pwm(steering_angle)

        return {
            "steering_pwm_value_us": steering_pwm_value_us
        }