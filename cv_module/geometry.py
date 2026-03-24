"""Geometry helpers for the CV module."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np


EPS = 1e-9


def wrap_angle(angle_rad: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return (angle_rad + math.pi) % (2 * math.pi) - math.pi


def angle_lerp(prev: float, curr: float, alpha: float) -> float:
    """Smoothly update an angle while handling wraparound."""
    delta = wrap_angle(curr - prev)
    return wrap_angle(prev + alpha * delta)


def lerp(prev: float, curr: float, alpha: float) -> float:
    return (1.0 - alpha) * prev + alpha * curr



def point_lerp(prev: np.ndarray, curr: np.ndarray, alpha: float) -> np.ndarray:
    return (1.0 - alpha) * prev + alpha * curr



def order_corners(points: Iterable[Iterable[float]]) -> np.ndarray:
    """Return corners ordered as top-left, top-right, bottom-right, bottom-left."""
    pts = np.array(list(points), dtype=np.float32)
    if pts.shape != (4, 2):
        raise ValueError(f"Expected four 2D corners, got shape {pts.shape}")

    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).reshape(-1)

    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(s)]      # top-left
    ordered[2] = pts[np.argmax(s)]      # bottom-right
    ordered[1] = pts[np.argmin(diff)]   # top-right
    ordered[3] = pts[np.argmax(diff)]   # bottom-left
    return ordered



def board_corners_metric(width_m: float, height_m: float) -> np.ndarray:
    """Board frame corners in meters, ordered TL, TR, BR, BL."""
    return np.array(
        [
            [0.0, 0.0],
            [width_m, 0.0],
            [width_m, height_m],
            [0.0, height_m],
        ],
        dtype=np.float32,
    )



def to_homogeneous(points: np.ndarray) -> np.ndarray:
    ones = np.ones((points.shape[0], 1), dtype=points.dtype)
    return np.hstack([points, ones])
