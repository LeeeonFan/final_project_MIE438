"""
motor_controller.py

Closed-loop motor speed controller for left and right motors.

Input:
    cmd = {
        "left_shaft_speed": float,   # rad/s
        "right_shaft_speed": float   # rad/s
    }

    feedback = {
        "left_shaft_speed": float,   # rad/s
        "right_shaft_speed": float   # rad/s
    }

Output:
    target = {
        "left_motor_pwm_value": float,   # normalized PWM in [-1, 1]
        "right_motor_pwm_value": float   # normalized PWM in [-1, 1]
    }
"""

from config import (
    LEFT_MOTOR_KP,
    LEFT_MOTOR_KI,
    LEFT_MOTOR_KD,
    RIGHT_MOTOR_KP,
    RIGHT_MOTOR_KI,
    RIGHT_MOTOR_KD,
    MOTOR_PWM_MIN,
    MOTOR_PWM_MAX,
)
from utils import clamp


class PID:
    def __init__(self, kp, ki, kd, output_min=-1.0, output_max=1.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.output_min = output_min
        self.output_max = output_max

        self.integral = 0.0
        self.prev_error = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_error = 0.0

    def update(self, error, dt):
        if dt <= 0:
            raise ValueError("dt must be > 0")

        self.integral += error * dt
        derivative = (error - self.prev_error) / dt

        output = (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )

        output = clamp(output, self.output_min, self.output_max)
        self.prev_error = error
        return output


class MotorController:
    def __init__(self):
        self.left_pid = PID(
            kp=LEFT_MOTOR_KP,
            ki=LEFT_MOTOR_KI,
            kd=LEFT_MOTOR_KD,
            output_min=MOTOR_PWM_MIN,
            output_max=MOTOR_PWM_MAX,
        )

        self.right_pid = PID(
            kp=RIGHT_MOTOR_KP,
            ki=RIGHT_MOTOR_KI,
            kd=RIGHT_MOTOR_KD,
            output_min=MOTOR_PWM_MIN,
            output_max=MOTOR_PWM_MAX,
        )

    def reset(self):
        self.left_pid.reset()
        self.right_pid.reset()

    def update(self, cmd, feedback, dt):
        """
        Parameters
        ----------
        cmd : dict
            {
                "left_shaft_speed": float,
                "right_shaft_speed": float
            }

        feedback : dict
            {
                "left_shaft_speed": float,
                "right_shaft_speed": float
            }

        dt : float
            Control timestep in seconds

        Returns
        -------
        dict
            {
                "left_motor_pwm_value": float,
                "right_motor_pwm_value": float
            }
        """
        target_left_speed = cmd.get("left_shaft_speed", 0.0)
        target_right_speed = cmd.get("right_shaft_speed", 0.0)

        measured_left_speed = feedback.get("left_shaft_speed", 0.0)
        measured_right_speed = feedback.get("right_shaft_speed", 0.0)

        left_error = target_left_speed - measured_left_speed
        right_error = target_right_speed - measured_right_speed

        left_motor_pwm_value = self.left_pid.update(left_error, dt)
        right_motor_pwm_value = self.right_pid.update(right_error, dt)

        return {
            "left_motor_pwm_value": left_motor_pwm_value,
            "right_motor_pwm_value": right_motor_pwm_value,
        }