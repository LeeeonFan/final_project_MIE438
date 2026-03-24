from dataclasses import dataclass, field
from typing import Tuple


@dataclass
class HSVRange:
    lower: Tuple[int, int, int]
    upper: Tuple[int, int, int]


@dataclass
class CVConfig:
    """Configuration for the CV-only test pipeline."""

    # Camera
    camera_index: int = 0
    frame_width: int = 1280
    frame_height: int = 720

    # Physical board dimensions in meters.
    # Change these to your actual whiteboard size.
    board_width_m: float = 0.2159
    board_height_m: float = 0.2794

    # Visualization scaling for the rectified board view.
    rectified_pixels_per_meter: int = 2500

    # Marker detection
    min_marker_area_px: int = 120
    max_marker_area_px: int = 100000
    morphology_kernel_size: int = 5

    # Front/head marker: RED circle
    red_ranges: tuple[HSVRange, ...] = field(
        default_factory=lambda: (
            HSVRange((0, 100, 80), (12, 255, 255)),
            HSVRange((170, 100, 80), (179, 255, 255)),
        )
    )

    # Rear/tail marker: BLUE circle
    blue_range: HSVRange = HSVRange((95, 100, 60), (130, 255, 255))

    # State filtering
    point_alpha: float = 0.35
    scalar_alpha: float = 0.25
    max_dt_s: float = 0.30

    # Misc
    show_debug_masks: bool = False
    calibration_json_path: str = "cv_calibration.json"
