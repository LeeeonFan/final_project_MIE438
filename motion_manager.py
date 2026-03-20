"""
motion_manager.py

Converts normalized command inputs into actuator-space targets.
"""

from config import MAX_SHAFT_SPEED, MAX_STEERING_ANGLE
from utils import clamp


class MotionManager:
    def __init__(self):
        self.max_shaft_speed = MAX_SHAFT_SPEED
        self.max_steering_angle = MAX_STEERING_ANGLE

    def update(self, cmd):
        """
        Parameters
        ----------
        cmd : dict
            {
                "throttle": float in [-1, 1],
                "steering": float in [-1, 1]
            }

        Returns
        -------
        dict
            {
                "left_shaft_speed": float (rad/s),
                "right_shaft_speed": float (rad/s),
                "steering_angle": float (deg)
            }
        """
        # Clamp inputs
        throttle = clamp(cmd.get("throttle", 0.0), -1.0, 1.0)
        steering = clamp(cmd.get("steering", 0.0), -1.0, 1.0)

        # Convert to physical targets
        left_shaft_speed = throttle * self.max_shaft_speed
        right_shaft_speed = throttle * self.max_shaft_speed
        steering_angle = steering * self.max_steering_angle

        return {
            "left_shaft_speed": left_shaft_speed,
            "right_shaft_speed": right_shaft_speed,
            "steering_angle": steering_angle,
        }