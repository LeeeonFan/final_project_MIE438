from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .config import CVConfig
from .geometry import board_corners_metric, order_corners


class BoardCalibrator:
    """Manual 4-corner board calibration using a planar homography."""

    def __init__(self, config: CVConfig):
        self.config = config
        self.image_corners_px: Optional[np.ndarray] = None
        self.board_corners_m: np.ndarray = board_corners_metric(
            config.board_width_m, config.board_height_m
        )
        self.h_img_to_board: Optional[np.ndarray] = None
        self.h_board_to_img: Optional[np.ndarray] = None

    @property
    def is_calibrated(self) -> bool:
        return self.h_img_to_board is not None and self.h_board_to_img is not None

    def set_corners(self, image_corners_px: np.ndarray) -> None:
        ordered = order_corners(image_corners_px)
        self.image_corners_px = ordered
        self.h_img_to_board = cv2.getPerspectiveTransform(
            ordered.astype(np.float32), self.board_corners_m.astype(np.float32)
        )
        self.h_board_to_img = cv2.getPerspectiveTransform(
            self.board_corners_m.astype(np.float32), ordered.astype(np.float32)
        )

    def image_to_board(self, points_px: np.ndarray) -> np.ndarray:
        if not self.is_calibrated:
            raise RuntimeError("BoardCalibrator is not calibrated yet.")
        pts = np.array(points_px, dtype=np.float32).reshape(-1, 1, 2)
        out = cv2.perspectiveTransform(pts, self.h_img_to_board)
        return out.reshape(-1, 2)

    def board_to_image(self, points_m: np.ndarray) -> np.ndarray:
        if not self.is_calibrated:
            raise RuntimeError("BoardCalibrator is not calibrated yet.")
        pts = np.array(points_m, dtype=np.float32).reshape(-1, 1, 2)
        out = cv2.perspectiveTransform(pts, self.h_board_to_img)
        return out.reshape(-1, 2)

    def warp_to_board_view(self, frame: np.ndarray) -> np.ndarray:
        if not self.is_calibrated:
            raise RuntimeError("BoardCalibrator is not calibrated yet.")
        ppm = self.config.rectified_pixels_per_meter
        width_px = max(1, int(round(self.config.board_width_m * ppm)))
        height_px = max(1, int(round(self.config.board_height_m * ppm)))

        target_rect = np.array(
            [[0, 0], [width_px - 1, 0], [width_px - 1, height_px - 1], [0, height_px - 1]],
            dtype=np.float32,
        )
        h = cv2.getPerspectiveTransform(self.image_corners_px.astype(np.float32), target_rect)
        warped = cv2.warpPerspective(frame, h, (width_px, height_px))
        return warped

    def save(self, path: Optional[str] = None) -> None:
        if not self.is_calibrated:
            raise RuntimeError("Cannot save calibration before calibration is complete.")
        save_path = Path(path or self.config.calibration_json_path)
        payload = {
            "board_width_m": self.config.board_width_m,
            "board_height_m": self.config.board_height_m,
            "image_corners_px": self.image_corners_px.tolist(),
            "board_corners_m": self.board_corners_m.tolist(),
        }
        save_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self, path: Optional[str] = None) -> bool:
        load_path = Path(path or self.config.calibration_json_path)
        if not load_path.exists():
            return False
        payload = json.loads(load_path.read_text(encoding="utf-8"))
        self.set_corners(np.array(payload["image_corners_px"], dtype=np.float32))
        return True

    def interactive_calibrate(self, frame: np.ndarray, window_name: str = "Calibration") -> bool:
        """Let the user click the four board corners in image space.

        Order expected: top-left, top-right, bottom-right, bottom-left.
        Press r to reset, s to save, q/esc to cancel.
        """
        display = frame.copy()
        clicked_points: list[tuple[int, int]] = []

        def on_mouse(event, x, y, _flags, _userdata):
            if event == cv2.EVENT_LBUTTONDOWN and len(clicked_points) < 4:
                clicked_points.append((x, y))

        cv2.namedWindow(window_name)
        cv2.setMouseCallback(window_name, on_mouse)

        while True:
            canvas = display.copy()
            for idx, pt in enumerate(clicked_points):
                cv2.circle(canvas, pt, 6, (0, 255, 0), -1)
                cv2.putText(
                    canvas,
                    str(idx + 1),
                    (pt[0] + 8, pt[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                )
            cv2.putText(
                canvas,
                "Click corners: TL, TR, BR, BL | r=reset s=save q=quit",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
            )
            cv2.imshow(window_name, canvas)
            key = cv2.waitKey(20) & 0xFF

            if key in (27, ord('q')):
                cv2.destroyWindow(window_name)
                return False
            if key == ord('r'):
                clicked_points.clear()
            if key == ord('s') and len(clicked_points) == 4:
                self.set_corners(np.array(clicked_points, dtype=np.float32))
                self.save()
                cv2.destroyWindow(window_name)
                return True
