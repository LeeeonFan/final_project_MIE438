"""Run the standalone CV module.

Usage:
    python run_cv_module.py

Controls:
    c = calibrate by clicking the 4 whiteboard corners
    l = load saved calibration from cv_calibration.json
    r = reset state estimator
    left click on rectified board view = set waypoint
    right click on rectified board view = clear waypoint
    q or ESC = quit
"""

from __future__ import annotations

import json
import math
import socket
import time

import cv2
import numpy as np

from config import PI_IP, COMMAND_PORT
from cv_module import BoardCalibrator, CVConfig, MarkerDetector, StateEstimator
from cv_module.visualizer import Visualizer
from cv_module.waypoint_controller import WaypointController


PRINT_PERIOD_S = 0.10
WINDOW_CAMERA = "CV Camera View"
WINDOW_BOARD = "CV Rectified Board View"


def configure_camera(cap: cv2.VideoCapture, config: CVConfig) -> None:
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)


def make_board_mouse_callback(config: CVConfig, waypoint_controller: WaypointController):
    # Must match the scaling logic in Visualizer.draw_board_overlay.
    # Board is stretched to (frame_width, frame_height), so x and y scale differently.
    fw = config.frame_width
    fh = config.frame_height
    bw_m = config.board_width_m
    bh_m = config.board_height_m

    def on_mouse(event, x, y, flags, param):
        if x >= fw:
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            wx = x * bw_m / fw
            wy = y * bh_m / fh
            waypoint_controller.set_waypoint(wx, wy)
            print(f"[waypoint] set to x={wx:.3f} m, y={wy:.3f} m")
        elif event == cv2.EVENT_RBUTTONDOWN:
            waypoint_controller.clear_waypoint()
            print("[waypoint] cleared")

    return on_mouse


def main() -> None:
    config = CVConfig()
    calibrator = BoardCalibrator(config)
    detector = MarkerDetector(config)
    estimator = StateEstimator(config)
    visualizer = Visualizer()
    waypoint_controller = WaypointController()

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pi_addr = (PI_IP, COMMAND_PORT)

    cap = cv2.VideoCapture(config.camera_index)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera index {config.camera_index}")
    configure_camera(cap, config)

    cv2.namedWindow(WINDOW_CAMERA, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_BOARD, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(
        WINDOW_BOARD,
        make_board_mouse_callback(config, waypoint_controller),
    )

    last_print_time = 0.0
    calibrator.load()
    if calibrator.is_calibrated:
        detector.set_board_roi(calibrator.image_corners_px)

    print("CV module started.")
    print("Markers: RED circle = head/front, BLUE circle = tail/rear")
    print("Keys: c=calibrate, l=load calibration, r=reset estimator, q=quit")
    print("Mouse on board view: left click=set waypoint, right click=clear waypoint")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Failed to grab frame from camera.")
                break

            detection = detector.detect(frame)
            state = None
            control_cmd = None

            if calibrator.is_calibrated and detection.valid:
                board_points = calibrator.image_to_board(
                    [detection.head_px, detection.tail_px]
                )
                timestamp = time.perf_counter()
                state = estimator.update(
                    head_m=board_points[0],
                    tail_m=board_points[1],
                    timestamp=timestamp,
                )

                control_cmd = waypoint_controller.compute(state)

                if timestamp - last_print_time >= PRINT_PERIOD_S:
                    last_print_time = timestamp
                    if control_cmd is not None:
                        print(
                            f"x={state.x:.3f} m, y={state.y:.3f} m, "
                            f"theta={state.theta:.3f} rad, v={state.v:.3f} m/s, "
                            f"omega={state.omega:.3f} rad/s, "
                            f"vx={state.vx:.3f} m/s, vy={state.vy:.3f} m/s | "
                            f"dist={control_cmd.distance:.3f} m, "
                            f"heading_err={math.degrees(control_cmd.heading_error):.1f} deg, "
                            f"throttle={control_cmd.throttle:.3f}, "
                            f"steering={control_cmd.steering:.3f}, "
                            f"reached={control_cmd.reached}"
                        )
                    else:
                        print(
                            f"x={state.x:.3f} m, y={state.y:.3f} m, "
                            f"theta={state.theta:.3f} rad, v={state.v:.3f} m/s, "
                            f"omega={state.omega:.3f} rad/s, "
                            f"vx={state.vx:.3f} m/s, vy={state.vy:.3f} m/s"
                        )

            cam_vis = visualizer.draw_camera_overlay(
                frame=frame,
                calibrator=calibrator,
                detection=detection,
                state=state,
            )
            cv2.imshow(WINDOW_CAMERA, cam_vis)

            if calibrator.is_calibrated:
                board_vis = visualizer.draw_board_overlay(
                    calibrator=calibrator,
                    frame=frame,
                    state=state,
                    waypoint_controller=waypoint_controller,
                    control_cmd=control_cmd,
                )
                cv2.imshow(WINDOW_BOARD, board_vis)
            else:
                board_vis = np.full((config.frame_height, config.frame_width, 3), 255, dtype=np.uint8)
                cv2.putText(
                    board_vis,
                    "Board calibration not ready",
                    (40, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 0, 180),
                    2,
                )
                cv2.putText(
                    board_vis,
                    "Press 'c' to calibrate, 'l' to load calibration",
                    (40, 130),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 0, 0),
                    2,
                )
                cv2.imshow(WINDOW_BOARD, board_vis)

            # Send command + measured velocity to Pi over UDP
            if control_cmd is not None and not control_cmd.reached:
                packet = {
                    "throttle": control_cmd.throttle,
                    "steering": control_cmd.steering,
                    "measured_v": state.v,
                }
            else:
                packet = {"throttle": 0.0, "steering": 0.0, "measured_v": 0.0}
            udp_sock.sendto(json.dumps(packet).encode(), pi_addr)

            if config.show_debug_masks and detection.red_mask is not None and detection.blue_mask is not None:
                cv2.imshow("Mask Red", detection.red_mask)
                cv2.imshow("Mask Blue", detection.blue_mask)

            key = cv2.waitKey(1) & 0xFF
            if key in (27, ord('q')):
                break
            if key == ord('c'):
                print("Calibration mode: click TL, TR, BR, BL then press s.")
                calibrator.interactive_calibrate(frame)
                if calibrator.is_calibrated:
                    detector.set_board_roi(calibrator.image_corners_px)
            elif key == ord('l'):
                loaded = calibrator.load()
                print(f"Calibration loaded: {loaded}")
                if calibrator.is_calibrated:
                    detector.set_board_roi(calibrator.image_corners_px)
            elif key == ord('r'):
                estimator.reset()
                print("State estimator reset.")

    finally:
        udp_sock.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()