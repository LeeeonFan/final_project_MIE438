"""
config.py
"""
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
MAX_SHAFT_SPEED = 100.0      # rad/s
MAX_STEERING_ANGLE = 30.0    # degrees
# Drivetrain
GEAR_RATIO = 1.0        


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

PI_IP = "172.20.10.3"       
COMMAND_PORT = 5006
COMMAND_TIMEOUT_S = 0.5       # seconds
MOTOR_PWM_FREQUENCY = 1000

# =========================================================
# MOTOR and SERVO
# =========================================================

MOTOR_PWM_FREQUENCY = 1000

SERVO_MIN_US = 100
SERVO_CENTER_US = 1500
SERVO_MAX_US = 2900
SERVO_ACTUATION_RANGE = 180

MOTOR_CONFIGS = [
    {"name": "left_motor", "in1": 18, "in2": 19, "pwm": 12},
    {"name": "right_motor", "in1": 20, "in2": 21, "pwm": 13},
]

PCA9685_I2C_ADDRESS = 0x40
PCA9685_PWM_FREQUENCY = 50
PCA9685_CHANNELS = 16

# Existing steering servo
SERVO1_CHANNEL = 0

# New manipulator servos
SERVO2_CHANNEL = 1
SERVO3_CHANNEL = 2

# Steering servo calibration
SERVO1_MIN_US = 100
SERVO1_CENTER_US = 1500
SERVO1_MAX_US = 2900

# Manipulator servo 1 calibration
SERVO2_MIN_US = 100
SERVO2_CENTER_US = 1500
SERVO2_MAX_US = 2900

# Manipulator servo 2 calibration
SERVO3_MIN_US = 100
SERVO3_CENTER_US = 1500
SERVO3_MAX_US = 2900

