"""
config.py

Minimal configuration file for the robot framework.
Only includes parameters needed by the current architecture.
"""

# =========================================================
# GPIO PINS (BCM numbering)
# =========================================================

# Left motor driver pins
LEFT_MOTOR_IN1 = 17
LEFT_MOTOR_IN2 = 27
LEFT_MOTOR_PWM = 18

# Right motor driver pins
RIGHT_MOTOR_IN1 = 22
RIGHT_MOTOR_IN2 = 23
RIGHT_MOTOR_PWM = 19

# Servo pin
STEERING_SERVO_PIN = 12


# =========================================================
# PWM SETTINGS
# =========================================================

# DC motor PWM
MOTOR_PWM_FREQUENCY = 1000   # Hz
MOTOR_PWM_RANGE = 255        # duty cycle range

# Servo pulse range
SERVO_MIN_US = 1000          # microseconds
SERVO_CENTER_US = 1500       # microseconds
SERVO_MAX_US = 2000          # microseconds


# =========================================================
# ROBOT / ACTUATOR PARAMETERS
# =========================================================

# Motion manager
MAX_SHAFT_SPEED = 100.0      # rad/s, must be measured or estimated
MAX_STEERING_ANGLE = 30.0    # degrees, must be measured or chosen

# Drivetrain
GEAR_RATIO = 1.0             # use actual value if needed in your controller


# =========================================================
# CONTROL LOOP
# =========================================================

CONTROL_FREQUENCY = 60.0     # Hz
DT = 1.0 / CONTROL_FREQUENCY


# =========================================================
# MOTOR PID GAINS
# =========================================================

LEFT_MOTOR_KP = 0.02
LEFT_MOTOR_KI = 0.0
LEFT_MOTOR_KD = 0.0

RIGHT_MOTOR_KP = 0.02
RIGHT_MOTOR_KI = 0.0
RIGHT_MOTOR_KD = 0.0


# =========================================================
# OUTPUT LIMITS
# =========================================================

MOTOR_PWM_MIN = -1.0
MOTOR_PWM_MAX = 1.0


# =========================================================
# WHEEL
# =========================================================

WHEEL_RADIUS_M = 0.015       # 15 mm


# =========================================================
# NETWORK (laptop -> Pi bridge)
# =========================================================

PI_IP = "172.20.10.3"       # set to your Pi's IP address
COMMAND_PORT = 5006
COMMAND_TIMEOUT_S = 0.5       # seconds; Pi stops motors if no command received
MOTOR_PWM_FREQUENCY = 1000

# =========================================================
# MOTOR and SERVO
# =========================================================

MOTOR_PWM_FREQUENCY = 1000

SERVO_MIN_US = 1000
SERVO_CENTER_US = 1500
SERVO_MAX_US = 2000
SERVO_ACTUATION_RANGE = 180

MOTOR_CONFIGS = [
    {"name": "left_motor", "in1": 17, "in2": 22, "pwm": 10},
    {"name": "right_motor", "in1": 23, "in2": 24, "pwm": 9},
]

PCA9685_I2C_ADDRESS = 0x40
PCA9685_PWM_FREQUENCY = 50
PCA9685_CHANNELS = 16

SERVO1_CHANNEL = 0