from __future__ import annotations

import math
from typing import Optional

import cv2
import numpy as np

from .board_calibrator import BoardCalibrator
from .marker_detector import MarkerDetection
from .state_estimator import RobotState
from .waypoint_controller import ControlCommand, WaypointController


class Visualizer:
    """Overlay detections, state, waypoint, and mock control on camera frames."""

    def draw_camera_overlay(
        self,
        frame: np.ndarray,
        calibrator: BoardCalibrator,
        detection: Optional[MarkerDetection] = None,
        state: Optional[RobotState] = None,
    ) -> np.ndarray:
        vis = frame.copy()

        if calibrator.image_corners_px is not None:
            corners = calibrator.image_corners_px.astype(int)
            cv2.polylines(vis, [corners], True, (0, 255, 255), 2)
            for idx, pt in enumerate(corners):
                cv2.circle(vis, tuple(pt), 5, (0, 255, 255), -1)
                cv2.putText(
                    vis,
                    f"C{idx+1}",
                    tuple(pt + np.array([8, -8])),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 255),
                    2,
                )

        if detection is not None:
            if detection.head_found and detection.head_px is not None:
                hp = tuple(np.round(detection.head_px).astype(int))
                cv2.circle(vis, hp, 10, (0, 0, 255), -1)
                cv2.putText(
                    vis,
                    "HEAD",
                    (hp[0] + 10, hp[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2,
                )
            if detection.tail_found and detection.tail_px is not None:
                tp = tuple(np.round(detection.tail_px).astype(int))
                cv2.circle(vis, tp, 10, (255, 0, 0), -1)
                cv2.putText(
                    vis,
                    "TAIL",
                    (tp[0] + 10, tp[1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2,
                )
            if detection.valid and detection.head_px is not None and detection.tail_px is not None:
                hp = tuple(np.round(detection.head_px).astype(int))
                tp = tuple(np.round(detection.tail_px).astype(int))
                cv2.line(vis, tp, hp, (0, 255, 0), 2)

        if state is not None:
            text_lines = [
                f"x={state.x:.3f} m  y={state.y:.3f} m",
                f"theta={math.degrees(state.theta):.1f} deg",
                f"v={state.v:.3f} m/s  omega={math.degrees(state.omega):.1f} deg/s",
                f"vx={state.vx:.3f} m/s  vy={state.vy:.3f} m/s",
            ]
            y0 = 30
            for idx, line in enumerate(text_lines):
                cv2.putText(
                    vis,
                    line,
                    (20, y0 + idx * 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (50, 255, 50),
                    2,
                )

        return vis

    def draw_board_overlay(
        self,
        calibrator: BoardCalibrator,
        frame: np.ndarray,
        state: Optional[RobotState] = None,
        waypoint_controller: Optional[WaypointController] = None,
        control_cmd: Optional[ControlCommand] = None,
    ) -> np.ndarray:
        board = calibrator.warp_to_board_view(frame)
        ppm = calibrator.config.rectified_pixels_per_meter

        h, w = board.shape[:2]
        for xm in np.arange(0.0, calibrator.config.board_width_m + 1e-6, 0.1):
            xpx = int(round(xm * ppm))
            cv2.line(board, (xpx, 0), (xpx, h - 1), (235, 235, 235), 1)
        for ym in np.arange(0.0, calibrator.config.board_height_m + 1e-6, 0.1):
            ypx = int(round(ym * ppm))
            cv2.line(board, (0, ypx), (w - 1, ypx), (235, 235, 235), 1)

        cv2.putText(
            board,
            "Board frame (meters)",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 120, 0),
            2,
        )

        cx = cy = None
        if state is not None and state.valid:
            hx, hy = int(round(state.head_x * ppm)), int(round(state.head_y * ppm))
            tx, ty = int(round(state.tail_x * ppm)), int(round(state.tail_y * ppm))
            cx, cy = int(round(state.x * ppm)), int(round(state.y * ppm))

            cv2.circle(board, (hx, hy), 10, (0, 0, 255), -1)
            cv2.circle(board, (tx, ty), 10, (255, 0, 0), -1)
            cv2.circle(board, (cx, cy), 8, (0, 255, 0), -1)
            cv2.line(board, (tx, ty), (hx, hy), (0, 255, 0), 3)

            heading_len_px = 0.10 * ppm
            heading_tip = (
                int(round(cx + heading_len_px * math.cos(state.theta))),
                int(round(cy + heading_len_px * math.sin(state.theta))),
            )
            cv2.arrowedLine(board, (cx, cy), heading_tip, (50, 50, 255), 3, tipLength=0.25)
            cv2.putText(
                board,
                "Heading",
                (heading_tip[0] + 8, heading_tip[1] - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (50, 50, 255),
                2,
            )

            vel_scale_px_per_mps = 0.35 * ppm
            vel_tip = (
                int(round(cx + vel_scale_px_per_mps * state.vx)),
                int(round(cy + vel_scale_px_per_mps * state.vy)),
            )
            cv2.arrowedLine(board, (cx, cy), vel_tip, (0, 140, 255), 3, tipLength=0.25)
            cv2.putText(
                board,
                "Velocity",
                (vel_tip[0] + 8, vel_tip[1] + 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 140, 255),
                2,
            )

        # Pen location
        px_pen = py_pen = None
        if state is not None and state.valid:
            px_pen = int(round(state.pen_x * ppm))
            py_pen = int(round(state.pen_y * ppm))
            cv2.circle(board, (px_pen, py_pen), 7, (0, 200, 200), -1)
            cv2.circle(board, (px_pen, py_pen), 9, (0, 140, 140), 2)
            cv2.putText(
                board,
                "Pen",
                (px_pen + 10, py_pen - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 180, 180),
                2,
            )

        if waypoint_controller is not None and waypoint_controller.has_waypoint():
            wp = waypoint_controller.waypoint
            wx, wy = int(round(wp.x * ppm)), int(round(wp.y * ppm))
            cv2.drawMarker(
                board,
                (wx, wy),
                (180, 0, 180),
                markerType=cv2.MARKER_CROSS,
                markerSize=22,
                thickness=3,
            )
            cv2.circle(board, (wx, wy), 10, (180, 0, 180), 2)
            cv2.putText(
                board,
                "Waypoint",
                (wx + 10, wy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 0, 180),
                2,
            )

            # Line from pen to waypoint (pen is the controlled point)
            if px_pen is not None and py_pen is not None:
                cv2.line(board, (px_pen, py_pen), (wx, wy), (120, 0, 200), 2)

        # Stretch board to exactly camera resolution, then append the panel.
        disp_w = calibrator.config.frame_width
        disp_h = calibrator.config.frame_height
        board_scaled = cv2.resize(board, (disp_w, disp_h), interpolation=cv2.INTER_LINEAR)

        # Append info panel to the right.
        PANEL_W = 300
        canvas = np.hstack([
            board_scaled,
            np.full((disp_h, PANEL_W, 3), 245, dtype=np.uint8),
        ])

        # Separator between board area and panel.
        cv2.line(canvas, (disp_w, 0), (disp_w, disp_h - 1), (180, 180, 180), 1)

        # Control info in the panel area.
        px = disp_w + 14
        if control_cmd is not None:
            cv2.putText(
                canvas, "[ Control ]", (px, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 40, 180), 2,
            )
            lines = [
                f"dist:          {control_cmd.distance:.3f} m",
                f"goal heading:  {math.degrees(control_cmd.goal_heading):.1f} deg",
                f"heading error: {math.degrees(control_cmd.heading_error):.1f} deg",
                f"throttle:      {control_cmd.throttle:.3f}",
                f"steering:      {control_cmd.steering:.3f}",
                f"reached:       {control_cmd.reached}",
            ]
            for idx, line in enumerate(lines):
                cv2.putText(
                    canvas, line, (px, 62 + idx * 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 30, 150), 1,
                )

        return canvas