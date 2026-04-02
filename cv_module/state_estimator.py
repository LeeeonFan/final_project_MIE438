from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .config import CVConfig
from .geometry import angle_lerp, lerp, point_lerp, wrap_angle


@dataclass
class RobotState:
    timestamp: float
    x: float
    y: float
    theta: float
    v: float
    omega: float
    vx: float
    vy: float
    head_x: float
    head_y: float
    tail_x: float
    tail_y: float
    pen_x: float
    pen_y: float
    valid: bool

    def as_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "x": self.x,
            "y": self.y,
            "theta": self.theta,
            "v": self.v,
            "omega": self.omega,
            "vx": self.vx,
            "vy": self.vy,
            "head_x": self.head_x,
            "head_y": self.head_y,
            "tail_x": self.tail_x,
            "tail_y": self.tail_y,
            "pen_x": self.pen_x,
            "pen_y": self.pen_y,
            "valid": self.valid,
        }


class StateEstimator:
    """Estimate board-frame pose and velocity from head/tail marker points."""

    def __init__(self, config: CVConfig):
        self.config = config
        self.prev_timestamp: Optional[float] = None
        self.prev_center: Optional[np.ndarray] = None
        self.prev_theta: Optional[float] = None
        self.prev_v: float = 0.0
        self.prev_omega: float = 0.0
        self.filtered_head: Optional[np.ndarray] = None
        self.filtered_tail: Optional[np.ndarray] = None

    def reset(self) -> None:
        self.prev_timestamp = None
        self.prev_center = None
        self.prev_theta = None
        self.prev_v = 0.0
        self.prev_omega = 0.0
        self.filtered_head = None
        self.filtered_tail = None

    def update(
        self,
        head_m: np.ndarray,
        tail_m: np.ndarray,
        timestamp: Optional[float] = None,
    ) -> RobotState:
        t = time.perf_counter() if timestamp is None else timestamp
        head_m = np.array(head_m, dtype=np.float32)
        tail_m = np.array(tail_m, dtype=np.float32)

        if self.filtered_head is None:
            self.filtered_head = head_m.copy()
            self.filtered_tail = tail_m.copy()
        else:
            alpha = self.config.point_alpha
            self.filtered_head = point_lerp(self.filtered_head, head_m, alpha)
            self.filtered_tail = point_lerp(self.filtered_tail, tail_m, alpha)

        center = 0.5 * (self.filtered_head + self.filtered_tail)
        vec = self.filtered_head - self.filtered_tail
        theta = math.atan2(float(vec[1]), float(vec[0]))

        v = 0.0
        omega = 0.0
        vx = 0.0
        vy = 0.0

        if self.prev_timestamp is not None and self.prev_center is not None and self.prev_theta is not None:
            dt = t - self.prev_timestamp
            if 1e-6 < dt <= self.config.max_dt_s:
                center_vel = (center - self.prev_center) / dt
                heading_dir = np.array([math.cos(theta), math.sin(theta)], dtype=np.float32)

                raw_v = float(center_vel @ heading_dir)
                raw_omega = wrap_angle(theta - self.prev_theta) / dt

                v = lerp(self.prev_v, raw_v, self.config.scalar_alpha)
                omega = lerp(self.prev_omega, raw_omega, self.config.scalar_alpha)

                vx = float(center_vel[0])
                vy = float(center_vel[1])
            else:
                v = 0.0
                omega = 0.0
                vx = 0.0
                vy = 0.0

        if self.prev_theta is not None:
            theta = angle_lerp(self.prev_theta, theta, self.config.scalar_alpha)

        self.prev_timestamp = t
        self.prev_center = center.copy()
        self.prev_theta = theta
        self.prev_v = v
        self.prev_omega = omega

        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        fwd = self.config.pen_offset_forward_m
        rgt = self.config.pen_offset_right_m
        pen_x = float(center[0]) + fwd * cos_t - rgt * sin_t
        pen_y = float(center[1]) + fwd * sin_t + rgt * cos_t

        return RobotState(
            timestamp=t,
            x=float(center[0]),
            y=float(center[1]),
            theta=float(theta),
            v=float(v),
            omega=float(omega),
            vx=float(vx),
            vy=float(vy),
            head_x=float(self.filtered_head[0]),
            head_y=float(self.filtered_head[1]),
            tail_x=float(self.filtered_tail[0]),
            tail_y=float(self.filtered_tail[1]),
            pen_x=pen_x,
            pen_y=pen_y,
            valid=True,
        )