from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from .config import CVConfig, HSVRange


@dataclass
class MarkerDetection:
    head_px: Optional[np.ndarray]
    tail_px: Optional[np.ndarray]
    head_area_px: float
    tail_area_px: float
    head_found: bool
    tail_found: bool
    red_mask: Optional[np.ndarray] = None
    blue_mask: Optional[np.ndarray] = None

    @property
    def valid(self) -> bool:
        return self.head_found and self.tail_found


class MarkerDetector:
    """Detect a red head marker and a blue tail marker."""

    def __init__(self, config: CVConfig):
        self.config = config
        k = config.morphology_kernel_size
        self.kernel = np.ones((k, k), dtype=np.uint8)

    def _make_mask(self, hsv: np.ndarray, ranges: list[HSVRange] | tuple[HSVRange, ...]) -> np.ndarray:
        mask = None
        for hsv_range in ranges:
            part = cv2.inRange(
                hsv,
                np.array(hsv_range.lower, dtype=np.uint8),
                np.array(hsv_range.upper, dtype=np.uint8),
            )
            mask = part if mask is None else cv2.bitwise_or(mask, part)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        return mask

    def _largest_centroid(self, mask: np.ndarray) -> tuple[Optional[np.ndarray], float, bool]:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best_area = 0.0
        best_centroid = None

        for contour in contours:
            area = float(cv2.contourArea(contour))
            if area < self.config.min_marker_area_px or area > self.config.max_marker_area_px:
                continue
            moments = cv2.moments(contour)
            if abs(moments["m00"]) < 1e-6:
                continue
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]
            if area > best_area:
                best_area = area
                best_centroid = np.array([cx, cy], dtype=np.float32)

        return best_centroid, best_area, best_centroid is not None

    def detect(self, frame_bgr: np.ndarray) -> MarkerDetection:
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        red_mask = self._make_mask(hsv, self.config.red_ranges)
        blue_mask = self._make_mask(hsv, (self.config.blue_range,))

        head_px, head_area, head_found = self._largest_centroid(red_mask)
        tail_px, tail_area, tail_found = self._largest_centroid(blue_mask)

        return MarkerDetection(
            head_px=head_px,
            tail_px=tail_px,
            head_area_px=head_area,
            tail_area_px=tail_area,
            head_found=head_found,
            tail_found=tail_found,
            red_mask=red_mask if self.config.show_debug_masks else None,
            blue_mask=blue_mask if self.config.show_debug_masks else None,
        )
