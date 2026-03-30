"""
test_servo_direct.py

Direct one-servo test using Adafruit ServoKit on Raspberry Pi + PCA9685.

Requirements:
    pip3 install adafruit-circuitpython-servokit

Wiring:
    - Servo signal -> PCA9685 channel 0
    - PCA9685 SDA/SCL -> Pi I2C
    - External 5V supply for servo power recommended
    - Common ground between Pi, PCA9685, and servo supply
"""

import time
from adafruit_servokit import ServoKit

# PCA9685 / servo settings
I2C_ADDRESS = 0x40
CHANNELS = 16
SERVO_CHANNEL = 0

# Servo calibration
SERVO_MIN_US = 1000
SERVO_MAX_US = 2000
SERVO_CENTER_ANGLE = 90
SERVO_LEFT_ANGLE = 30
SERVO_RIGHT_ANGLE = 150
ACTUATION_RANGE = 180

MOVE_DELAY_S = 1.5

# Create ServoKit for PCA9685
kit = ServoKit(channels=CHANNELS, address=I2C_ADDRESS)

# Configure the servo on the selected channel
servo = kit.servo[SERVO_CHANNEL]
servo.actuation_range = ACTUATION_RANGE
servo.set_pulse_width_range(SERVO_MIN_US, SERVO_MAX_US)

try:
    print("Center")
    servo.angle = SERVO_CENTER_ANGLE
    time.sleep(MOVE_DELAY_S)

    print("Left")
    servo.angle = SERVO_LEFT_ANGLE
    time.sleep(MOVE_DELAY_S)

    print("Right")
    servo.angle = SERVO_RIGHT_ANGLE
    time.sleep(MOVE_DELAY_S)

    print("Center")
    servo.angle = SERVO_CENTER_ANGLE
    time.sleep(MOVE_DELAY_S)

finally:
    # Release the servo signal
    servo.angle = None
    print("Done")