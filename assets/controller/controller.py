import math
import sys
import os
import pygame

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from servo_controller import ServoController

pygame.init()
pygame.joystick.init()

WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("PS5 Controller Visualizer")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 22)
SMALL_FONT = pygame.font.SysFont("arial", 16)

BG = (18, 18, 24)
WHITE = (240, 240, 240)
GRAY = (120, 120, 120)
DARK_GRAY = (60, 60, 60)
GREEN = (80, 220, 120)
RED = (220, 90, 90)
BLUE = (90, 160, 255)
YELLOW = (255, 210, 90)
PURPLE = (180, 120, 255)

BUTTON_NAMES = {
    0: "Cross",
    1: "Circle",
    2: "Square",
    3: "Triangle",
    4: "Create",
    5: "PS",
    6: "Options",
    7: "L3",
    8: "R3",
    9: "L1",
    10: "R1",
    11: "DPad Up",
    12: "DPad Down",
    13: "DPad Left",
    14: "DPad Right",
    15: "Touchpad",
    16: "Mic",
}

AXIS_NAMES = {
    0: "Left Stick X",
    1: "Left Stick Y",
    2: "Right Stick X",
    3: "Right Stick Y",
}


def draw_text(text, x, y, color=WHITE, font=FONT):
    surf = font.render(text, True, color)
    screen.blit(surf, (x, y))


def draw_button(x, y, radius, label, pressed):
    color = GREEN if pressed else DARK_GRAY
    pygame.draw.circle(screen, color, (x, y), radius)
    pygame.draw.circle(screen, WHITE, (x, y), radius, 2)
    txt = SMALL_FONT.render(label, True, WHITE)
    rect = txt.get_rect(center=(x, y))
    screen.blit(txt, rect)


def draw_trigger(x, y, w, h, value, label):
    pygame.draw.rect(screen, DARK_GRAY, (x, y, w, h), border_radius=8)
    fill_h = int(h * max(0.0, min(1.0, value)))
    pygame.draw.rect(screen, BLUE, (x, y + h - fill_h, w, fill_h), border_radius=8)
    pygame.draw.rect(screen, WHITE, (x, y, w, h), 2, border_radius=8)
    draw_text(f"{label}: {value:.2f}", x, y - 30)


def draw_stick(cx, cy, size, xval, yval, label, pressed=False):
    pygame.draw.circle(screen, DARK_GRAY, (cx, cy), size, 0)
    pygame.draw.circle(screen, WHITE, (cx, cy), size, 2)

    knob_x = int(cx + xval * (size - 12))
    knob_y = int(cy + yval * (size - 12))
    knob_color = RED if pressed else YELLOW

    pygame.draw.circle(screen, knob_color, (knob_x, knob_y), 12)
    pygame.draw.circle(screen, WHITE, (knob_x, knob_y), 12, 2)

    pygame.draw.line(screen, GRAY, (cx - size, cy), (cx + size, cy), 1)
    pygame.draw.line(screen, GRAY, (cx, cy - size), (cx, cy + size), 1)

    draw_text(f"{label}: ({xval:+.2f}, {yval:+.2f})", cx - size, cy + size + 15)


def get_controller():
    if pygame.joystick.get_count() == 0:
        return None
    joystick = pygame.joystick.Joystick(0)
    joystick.init()
    return joystick


def safe_button(js, index):
    return js.get_button(index) if index < js.get_numbuttons() else 0


def safe_axis(js, index):
    return js.get_axis(index) if index < js.get_numaxes() else 0.0


def normalize_trigger(v):
    if v < 0:
        return (v + 1) / 2
    return v


def apply_deadzone(value, deadzone):
    """Zero out values within the deadzone, rescale the rest to [0, 1] range."""
    if abs(value) < deadzone:
        return 0.0
    sign = 1.0 if value > 0 else -1.0
    return sign * (abs(value) - deadzone) / (1.0 - deadzone)


class EMAFilter:
    """Exponential moving average filter for smoothing noisy analog input."""

    def __init__(self, alpha=0.3):
        self._alpha = alpha
        self._value = 0.0
        self._initialized = False

    def update(self, raw):
        if not self._initialized:
            self._value = raw
            self._initialized = True
        else:
            self._value = self._alpha * raw + (1.0 - self._alpha) * self._value
        return self._value

    def reset(self):
        self._value = 0.0
        self._initialized = False


class ControllerManager:
    """
    Manages PS5 controller input and converts to robot commands (throttle, steering).

    Default mapping:
    - R2 → forward throttle, L2 → reverse throttle
    - Right Stick X → steering angle
    - Deadzone + EMA low-pass filter on all analog axes
    """

    THROTTLE_MODE_TRIGGERS = "triggers"
    THROTTLE_MODE_R2 = "r2"
    THROTTLE_MODE_LEFT_STICK = "left_stick"

    def __init__(self, throttle_mode="triggers", stick_deadzone=0.08,
                 trigger_deadzone=0.05, smoothing_alpha=0.35):
        self.joystick = None
        self.servo_controller = ServoController()
        self.throttle_mode = throttle_mode
        self.stick_deadzone = stick_deadzone
        self.trigger_deadzone = trigger_deadzone

        self._throttle_filter = EMAFilter(alpha=smoothing_alpha)
        self._steering_filter = EMAFilter(alpha=smoothing_alpha)

        self._init_joystick()

    def _init_joystick(self):
        """Initialize the joystick connection."""
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()

    def reconnect(self):
        """Attempt to reconnect joystick."""
        self._init_joystick()

    def is_connected(self):
        """Check if controller is connected."""
        return self.joystick is not None and pygame.joystick.get_count() > 0

    def get_raw_input(self):
        """
        Get raw controller input values.

        Returns
        -------
        dict
            Raw input state from controller with keys like:
            - left_x, left_y: Left stick position
            - right_x, right_y: Right stick position
            - l2, r2: Trigger values (0.0-1.0)
            - buttons: dict of button states
        """
        if not self.is_connected():
            return None

        js = self.joystick

        left_x = safe_axis(js, 0)
        left_y = safe_axis(js, 1)
        right_x = safe_axis(js, 2)
        right_y = safe_axis(js, 3)

        raw_l2 = safe_axis(js, 4) if js.get_numaxes() > 4 else 0.0
        raw_r2 = safe_axis(js, 5) if js.get_numaxes() > 5 else 0.0

        l2 = normalize_trigger(raw_l2)
        r2 = normalize_trigger(raw_r2)

        buttons = {
            "cross": safe_button(js, 0),
            "circle": safe_button(js, 1),
            "square": safe_button(js, 2),
            "triangle": safe_button(js, 3),
            "create": safe_button(js, 4),
            "ps": safe_button(js, 5),
            "options": safe_button(js, 6),
            "l3": safe_button(js, 7),
            "r3": safe_button(js, 8),
            "l1": safe_button(js, 9),
            "r1": safe_button(js, 10),
            "dpad_up": safe_button(js, 11),
            "dpad_down": safe_button(js, 12),
            "dpad_left": safe_button(js, 13),
            "dpad_right": safe_button(js, 14),
            "touchpad": safe_button(js, 15),
        }

        return {
            "left_x": left_x,
            "left_y": left_y,
            "right_x": right_x,
            "right_y": right_y,
            "l2": l2,
            "r2": r2,
            "raw_l2": raw_l2,
            "raw_r2": raw_r2,
            "buttons": buttons,
        }

    def get_command_payload(self):
        """
        Get robot command payload (throttle, steering) from controller.

        Throttle source depends on throttle_mode:
        - "triggers" (default): R2 forward, L2 backward  (-1.0 to 1.0)
        - "r2": R2 only (0.0 to 1.0)
        - "left_stick": Left stick Y (-1.0 to 1.0)

        Steering comes from right stick X (-1.0 to 1.0).

        All analog values pass through a deadzone and EMA low-pass filter.

        Returns
        -------
        dict or None
        """
        raw_input = self.get_raw_input()

        if raw_input is None:
            return None

        raw_steering = apply_deadzone(raw_input["right_x"], self.stick_deadzone)

        if self.throttle_mode == self.THROTTLE_MODE_TRIGGERS:
            r2 = apply_deadzone(raw_input["r2"], self.trigger_deadzone)
            l2 = apply_deadzone(raw_input["l2"], self.trigger_deadzone)
            raw_throttle = r2 - l2
        elif self.throttle_mode == self.THROTTLE_MODE_R2:
            raw_throttle = apply_deadzone(raw_input["r2"], self.trigger_deadzone)
        else:
            raw_throttle = apply_deadzone(-raw_input["left_y"], self.stick_deadzone)

        throttle = self._throttle_filter.update(raw_throttle)
        steering = self._steering_filter.update(raw_steering)

        max_angle = self.servo_controller.max_steering_angle
        steering_angle = steering * max_angle
        servo_cmd = {"steering_angle": steering_angle}
        servo_output = self.servo_controller.update(servo_cmd)

        return {
            "throttle": throttle,
            "steering": steering,
            "steering_pwm_us": servo_output["steering_pwm_value_us"],
            "steering_angle": steering_angle,
            "raw_input": raw_input,
        }


def main():
    controller_manager = ControllerManager()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.JOYDEVICEADDED:
                controller_manager.reconnect()
            elif event.type == pygame.JOYDEVICEREMOVED:
                controller_manager.reconnect()

        screen.fill(BG)
        draw_text("PS5 Controller → Robot Commands", 30, 20, PURPLE)
        draw_text("R2: forward  |  L2: backward  |  Right Stick X: steering", 30, 55, GRAY)

        if not controller_manager.is_connected():
            draw_text("No controller detected.", 30, 120, RED)
            pygame.display.flip()
            clock.tick(60)
            continue

        raw_input = controller_manager.get_raw_input()
        payload = controller_manager.get_command_payload()

        draw_text(f"Controller: {controller_manager.joystick.get_name()}", 30, 100, WHITE)

        left_x = raw_input["left_x"]
        left_y = raw_input["left_y"]
        right_x = raw_input["right_x"]
        right_y = raw_input["right_y"]

        l2 = raw_input["l2"]
        r2 = raw_input["r2"]

        l3 = raw_input["buttons"]["l3"]
        r3 = raw_input["buttons"]["r3"]

        draw_stick(220, 300, 90, left_x, left_y, "Left Stick", pressed=bool(l3))
        draw_stick(460, 300, 90, right_x, right_y, "Right Stick (Steering)", pressed=bool(r3))

        draw_button(180, 170, 28, "L1", raw_input["buttons"]["l1"])
        draw_button(500, 170, 28, "R1", raw_input["buttons"]["r1"])
        draw_trigger(120, 470, 50, 140, l2, "L2 (Back)")
        draw_trigger(490, 470, 50, 140, r2, "R2 (Fwd)")

        draw_button(760, 270, 24, "\u25b3", raw_input["buttons"]["triangle"])
        draw_button(810, 320, 24, "\u25cb", raw_input["buttons"]["circle"])
        draw_button(710, 320, 24, "\u25a1", raw_input["buttons"]["square"])
        draw_button(760, 370, 24, "\u00d7", raw_input["buttons"]["cross"])

        draw_button(120, 270, 22, "\u2191", raw_input["buttons"]["dpad_up"])
        draw_button(120, 370, 22, "\u2193", raw_input["buttons"]["dpad_down"])
        draw_button(70, 320, 22, "\u2190", raw_input["buttons"]["dpad_left"])
        draw_button(170, 320, 22, "\u2192", raw_input["buttons"]["dpad_right"])

        draw_button(330, 250, 20, "Cr", raw_input["buttons"]["create"])
        draw_button(350, 320, 20, "PS", raw_input["buttons"]["ps"])
        draw_button(370, 250, 20, "Op", raw_input["buttons"]["options"])
        draw_button(350, 200, 24, "TP", raw_input["buttons"]["touchpad"])

        panel_x = 620
        panel_y = 120
        draw_text("Command Payload", panel_x, panel_y, PURPLE)

        y = panel_y + 35
        draw_text(f"throttle:  {payload['throttle']:+.2f}", panel_x, y, YELLOW, SMALL_FONT)
        y += 24
        draw_text(f"steering:  {payload['steering']:+.2f}", panel_x, y, YELLOW, SMALL_FONT)
        y += 24
        draw_text(f"(steering angle: {payload['steering_angle']:+.1f}°)", panel_x, y, GRAY, SMALL_FONT)
        y += 24
        draw_text(f"PWM: {payload['steering_pwm_us']} µs", panel_x, y, GREEN, SMALL_FONT)

        y += 48
        draw_text("Raw Input", panel_x, y, PURPLE)
        y += 35

        axis_info = [
            ("L: X", f"{left_x:+.2f}"),
            ("L: Y", f"{left_y:+.2f}"),
            ("R: X", f"{right_x:+.2f}"),
            ("R: Y", f"{right_y:+.2f}"),
            ("L2", f"{l2:.2f}"),
            ("R2", f"{r2:.2f}"),
        ]

        for label, value in axis_info:
            draw_text(f"{label}  {value}", panel_x, y, WHITE, SMALL_FONT)
            y += 22

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
