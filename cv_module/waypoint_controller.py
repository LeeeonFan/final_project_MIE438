from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from .geometry import wrap_angle
from .state_estimator import RobotState


def clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class Waypoint:
    x: float
    y: float


@dataclass
class ControlCommand:
    throttle: float
    steering: float
    distance: float
    goal_heading: float
    heading_error: float
    reached: bool


class WaypointController:
    def __init__(
        self,
        k_v: float = 1.8,
        k_theta: float = 1.5,
        goal_radius_m: float = 0.03,
        max_throttle: float = 1.0,
        max_steering: float = 1.0,
    ):
        self.k_v = k_v
        self.k_theta = k_theta
        self.goal_radius_m = goal_radius_m
        self.max_throttle = max_throttle
        self.max_steering = max_steering

        self.waypoint: Optional[Waypoint] = None

    def set_waypoint(self, x: float, y: float) -> None:
        self.waypoint = Waypoint(x=x, y=y)

    def clear_waypoint(self) -> None:
        self.waypoint = None

    def has_waypoint(self) -> bool:
        return self.waypoint is not None

    def compute(self, state: RobotState) -> Optional[ControlCommand]:
        if not state.valid or self.waypoint is None:
            return None

        dx = self.waypoint.x - state.x
        dy = self.waypoint.y - state.y
        distance = math.hypot(dx, dy)
        goal_heading = math.atan2(dy, dx)
        heading_error = wrap_angle(goal_heading - state.theta)

        if distance <= self.goal_radius_m:
            return ControlCommand(
                throttle=0.0,
                steering=0.0,
                distance=distance,
                goal_heading=goal_heading,
                heading_error=heading_error,
                reached=True,
            )

        steering = clip(self.k_theta * heading_error, -self.max_steering, self.max_steering)

        # Slow down when facing far away from the target direction
        heading_scale = max(0.0, math.cos(heading_error))
        throttle = clip(self.k_v * distance * heading_scale, -self.max_throttle, self.max_throttle)

        return ControlCommand(
            throttle=throttle,
            steering=steering,
            distance=distance,
            goal_heading=goal_heading,
            heading_error=heading_error,
            reached=False,
        )