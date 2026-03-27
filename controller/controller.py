import math
import sys
import pygame

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


def main():
    joystick = get_controller()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.JOYDEVICEADDED:
                joystick = get_controller()
            elif event.type == pygame.JOYDEVICEREMOVED:
                joystick = get_controller()

        screen.fill(BG)
        draw_text("PS5 Controller Visualizer", 30, 20, PURPLE)
        draw_text("Connect a DualSense controller and press buttons/move sticks.", 30, 55, GRAY)

        if joystick is None:
            draw_text("No controller detected.", 30, 120, RED)
            pygame.display.flip()
            clock.tick(60)
            continue

        draw_text(f"Controller: {joystick.get_name()}", 30, 100, WHITE)

        left_x = safe_axis(joystick, 0)
        left_y = safe_axis(joystick, 1)
        right_x = safe_axis(joystick, 2)
        right_y = safe_axis(joystick, 3)

        raw_l2 = safe_axis(joystick, 4) if joystick.get_numaxes() > 4 else 0.0
        raw_r2 = safe_axis(joystick, 5) if joystick.get_numaxes() > 5 else 0.0

        l2 = normalize_trigger(raw_l2)
        r2 = normalize_trigger(raw_r2)

        l3 = safe_button(joystick, 7)
        r3 = safe_button(joystick, 8)

        draw_stick(220, 300, 90, left_x, left_y, "Left Stick", pressed=bool(l3))
        draw_stick(460, 300, 90, right_x, right_y, "Right Stick", pressed=bool(r3))

        draw_button(180, 170, 28, "L1", safe_button(joystick, 9))
        draw_button(500, 170, 28, "R1", safe_button(joystick, 10))
        draw_trigger(120, 470, 50, 140, l2, "L2")
        draw_trigger(490, 470, 50, 140, r2, "R2")

        draw_button(760, 270, 24, "\u25b3", safe_button(joystick, 3))
        draw_button(810, 320, 24, "\u25cb", safe_button(joystick, 1))
        draw_button(710, 320, 24, "\u25a1", safe_button(joystick, 2))
        draw_button(760, 370, 24, "\u00d7", safe_button(joystick, 0))

        draw_button(120, 270, 22, "\u2191", safe_button(joystick, 11))
        draw_button(120, 370, 22, "\u2193", safe_button(joystick, 12))
        draw_button(70, 320, 22, "\u2190", safe_button(joystick, 13))
        draw_button(170, 320, 22, "\u2192", safe_button(joystick, 14))

        draw_button(330, 250, 20, "Cr", safe_button(joystick, 4))
        draw_button(350, 320, 20, "PS", safe_button(joystick, 5))
        draw_button(370, 250, 20, "Op", safe_button(joystick, 6))
        draw_button(350, 200, 24, "TP", safe_button(joystick, 15))

        panel_x = 620
        panel_y = 120
        draw_text("Buttons", panel_x, panel_y, PURPLE)

        y = panel_y + 35
        for idx, name in BUTTON_NAMES.items():
            state = safe_button(joystick, idx)
            color = GREEN if state else GRAY
            draw_text(f"{idx:>2}: {name:<10} = {state}", panel_x, y, color, SMALL_FONT)
            y += 24

        y += 10
        draw_text("Axes", panel_x, y, PURPLE)
        y += 35

        for idx, name in AXIS_NAMES.items():
            val = safe_axis(joystick, idx)
            draw_text(f"{idx:>2}: {name:<13} = {val:+.3f}", panel_x, y, WHITE, SMALL_FONT)
            y += 24

        draw_text(f"4: L2 = {raw_l2:+.3f} -> {l2:.3f}", panel_x, y, WHITE, SMALL_FONT)
        y += 24
        draw_text(f"5: R2 = {raw_r2:+.3f} -> {r2:.3f}", panel_x, y, WHITE, SMALL_FONT)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
