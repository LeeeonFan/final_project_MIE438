from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

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
    """Turn-then-drive waypoint controller.

    Three zones based on heading error:
      1. REVERSE: |heading_error| > 90° → waypoint is behind, drive backward.
      2. TURN:    |heading_error| > threshold → steer toward waypoint with
         a small forward throttle so the Ackermann chassis actually arcs.
         The servo responds faster than the motors, so it physically
         "steers first, then moves."
      3. DRIVE:   |heading_error| <= threshold → drive straight (steering
         centered).
    """

    def __init__(
        self,
        goal_radius_m: float = 0.03,
        heading_threshold_rad: float = math.radians(30),
        turn_throttle: float = 0.3,
        drive_throttle: float = 1.0,
        k_steering: float = 0.8,
        max_steering: float = 1.0,
    ):
        self.goal_radius_m = goal_radius_m
        self.heading_threshold_rad = heading_threshold_rad
        self.turn_throttle = turn_throttle
        self.drive_throttle = drive_throttle
        self.k_steering = k_steering
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

        dx = self.waypoint.x - state.pen_x
        dy = self.waypoint.y - state.pen_y
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

        if abs(heading_error) > math.pi / 2:
            # REVERSE: waypoint is behind — drive backward, no steering
            steering = 0.0
            throttle = -self.drive_throttle
        elif abs(heading_error) > self.heading_threshold_rad:
            # TURN: steer toward waypoint + small throttle to arc
            steering = clip(
                self.k_steering * heading_error,
                -self.max_steering,
                self.max_steering,
            )
            throttle = self.turn_throttle
        else:
            # DRIVE: aligned — go straight
            steering = 0.0
            throttle = self.drive_throttle

        return ControlCommand(
            throttle=throttle,
            steering=steering,
            distance=distance,
            goal_heading=goal_heading,
            heading_error=heading_error,
            reached=False,
        )