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
    """PID waypoint controller using CV state as feedback.

    Heading channel:  PID on heading_error, uses state.omega as derivative feedback.
    Speed channel:    PID on distance (scaled by cos(heading_error)),
                      uses closing speed as derivative feedback.

    Default I and D gains are 0, preserving the original P-only behaviour.
    """

    def __init__(
        self,
        # --- Heading PID gains ---
        k_theta_p: float = 1.5,
        k_theta_i: float = 0.0,
        k_theta_d: float = 0.0,
        # --- Speed PID gains ---
        k_v_p: float = 1.8,
        k_v_i: float = 0.0,
        k_v_d: float = 0.0,
        # --- Limits ---
        goal_radius_m: float = 0.03,
        max_throttle: float = 1.0,
        max_steering: float = 1.0,
        # --- Anti-windup: cap integral magnitude ---
        max_heading_integral: float = 2.0,
        max_speed_integral: float = 2.0,
    ):
        # Heading PID
        self.k_theta_p = k_theta_p
        self.k_theta_i = k_theta_i
        self.k_theta_d = k_theta_d

        # Speed PID
        self.k_v_p = k_v_p
        self.k_v_i = k_v_i
        self.k_v_d = k_v_d

        # Limits
        self.goal_radius_m = goal_radius_m
        self.max_throttle = max_throttle
        self.max_steering = max_steering
        self.max_heading_integral = max_heading_integral
        self.max_speed_integral = max_speed_integral

        # Internal state
        self.waypoint: Optional[Waypoint] = None
        self._heading_integral: float = 0.0
        self._speed_integral: float = 0.0
        self._prev_heading_error: Optional[float] = None
        self._prev_distance: Optional[float] = None
        self._prev_timestamp: Optional[float] = None

    def _reset_pid_state(self) -> None:
        self._heading_integral = 0.0
        self._speed_integral = 0.0
        self._prev_heading_error = None
        self._prev_distance = None
        self._prev_timestamp = None

    def set_waypoint(self, x: float, y: float) -> None:
        self.waypoint = Waypoint(x=x, y=y)
        self._reset_pid_state()

    def clear_waypoint(self) -> None:
        self.waypoint = None
        self._reset_pid_state()

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
            self._reset_pid_state()
            return ControlCommand(
                throttle=0.0,
                steering=0.0,
                distance=distance,
                goal_heading=goal_heading,
                heading_error=heading_error,
                reached=True,
            )

        # --- Compute dt ---
        dt = None
        if self._prev_timestamp is not None:
            dt = state.timestamp - self._prev_timestamp
            if dt <= 1e-6 or dt > 0.5:
                dt = None
        self._prev_timestamp = state.timestamp

        # =============================================================
        # Heading PID
        # =============================================================
        # P
        heading_p = self.k_theta_p * heading_error

        # I
        heading_i_term = 0.0
        if dt is not None and self.k_theta_i != 0.0:
            self._heading_integral += heading_error * dt
            self._heading_integral = clip(
                self._heading_integral,
                -self.max_heading_integral,
                self.max_heading_integral,
            )
            heading_i_term = self.k_theta_i * self._heading_integral

        # D — use state.omega (measured angular velocity) as derivative feedback
        # omega > 0 means rotating CCW (heading increasing), so it opposes positive heading_error
        heading_d_term = 0.0
        if self.k_theta_d != 0.0:
            heading_d_term = -self.k_theta_d * state.omega

        steering = clip(
            heading_p + heading_i_term + heading_d_term,
            -self.max_steering,
            self.max_steering,
        )

        # =============================================================
        # Speed PID
        # =============================================================
        # Slow down when facing away from the target
        heading_scale = max(0.0, math.cos(heading_error))
        speed_error = distance * heading_scale

        # P
        speed_p = self.k_v_p * speed_error

        # I
        speed_i_term = 0.0
        if dt is not None and self.k_v_i != 0.0:
            self._speed_integral += speed_error * dt
            self._speed_integral = clip(
                self._speed_integral,
                -self.max_speed_integral,
                self.max_speed_integral,
            )
            speed_i_term = self.k_v_i * self._speed_integral

        # D — use closing speed (rate of distance decrease) as derivative feedback
        speed_d_term = 0.0
        if dt is not None and self.k_v_d != 0.0 and self._prev_distance is not None:
            closing_speed = -(distance - self._prev_distance) / dt
            speed_d_term = -self.k_v_d * closing_speed

        self._prev_distance = distance
        self._prev_heading_error = heading_error

        throttle = clip(
            speed_p + speed_i_term + speed_d_term,
            -self.max_throttle,
            self.max_throttle,
        )

        return ControlCommand(
            throttle=throttle,
            steering=steering,
            distance=distance,
            goal_heading=goal_heading,
            heading_error=heading_error,
            reached=False,
        )