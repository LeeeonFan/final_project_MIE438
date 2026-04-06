# Raspberry Pi–based Mobile Whiteboard Robot
This project is a Raspberry Pi–based mobile whiteboard robot designed to move across a whiteboard surface while carrying a simple manipulator that can hold either an eraser or a pen. In operation, the robot can navigate along the board, position its end effector, and support whiteboard interaction tasks such as writing, marking, or erasing. It is built around a **Raspberry Pi 5**, **L298N motor driver**, and **PCA9685 servo driver**. The project supports multiple command sources over UDP, including

- **Keyboard teleoperation** from a laptop
- **PS5 controller teleoperation**
- **Camera-based CV waypoint control**

The software is organized as a layered pipeline:

```text
Command Source
    ↓
Motion Manager
    ↓
Controllers (Drivers)
  ├── Motor Controller
  └── Servo Controller
    ↓
HAL (Hardware Abstraction Layer)
    ↓
Robot Hardware
```
This repository contains the software for the MIE438 final project. Mechanical and hardware design materials are organized and added here prior to submission.
## Software Framework

This framework receives high-level drive commands such as throttle and steering, converts them into actuator-space targets, and applies them to:

- **2 DC drive motors** through an L298N driver
- **1 steering servo** through a PCA9685
- **2 manipulator servos** through the same PCA9685

It also includes a standalone **computer vision module** that tracks the robot on a board, estimates state, and sends waypoint-following commands to the Pi.

## Main features

- Layered robot-control architecture
- Keyboard teleoperation client
- PS5 controller teleoperation client
- CV-based waypoint navigation module
- PID motor controller interface
- Servo pulse-width control through Adafruit ServoKit
- Watchdog timeout that stops the robot when commands are lost
- Basic motor and servo test scripts

## Repository structure

```text
.
├── assets/
│   └── marker_template.png
├── cv_module/
│   ├── __init__.py
│   ├── __init__.py
│   ├── board_calibrator.py
│   ├── config.py
│   ├── geometry.py
│   ├── marker_detector.py
│   ├── state_estimator.py
│   ├── visualizer.py
│   └── waypoint_controller.py
├── tests/
|   └── controller/
│   ├── motor_test.py
│   ├── servo_test.py
│   └── test_cam_index.py
├── config.py
├── controller_client.py
├── cv_calibration.json
├── hal.py
├── main.py
├── motion_manager.py
├── motor_controller.py
├── run_cv_module.py
├── servo_controller.py
├── teleop_client.py
└── utils.py
```

## Software architecture

### 1. `main.py`
The main robot process running on the Raspberry Pi.

It:
- listens for packets on `COMMAND_PORT`
- applies a watchdog timeout
- converts normalized commands into targets
- runs the controller pipeline
- sends final actuator commands to the HAL

### 2. `motion_manager.py`
Converts normalized high-level commands into physical targets:

- `throttle ∈ [-1, 1]` → left/right shaft speed targets
- `steering ∈ [-1, 1]` → steering angle target

### 3. `motor_controller.py`
Implements simple PID-based left/right motor control.

Inputs:
- target shaft speed
- measured shaft speed

Outputs:
- normalized motor command in `[-1, 1]`

### 4. `servo_controller.py`
Maps steering angle into a servo pulse width in microseconds.

### 5. `hal.py`
Hardware abstraction layer for the real robot.

Current implementation:
- **DC motors**: direct GPIO direction control through `lgpio` and L298N
- **Servos**: PCA9685 + `adafruit_servokit`

### 6. `teleop_client.py`
Keyboard teleoperation client running on a laptop.

Sends packets to the Pi continuously while you adjust commands with the keyboard.

### 7. `controller_client.py`
PS5 controller teleoperation client on laptop.

Uses a controller manager to map sticks/triggers to throttle and steering, then sends the same packet format as the keyboard teleop.

### 8. `run_cv_module.py`
Standalone computer vision process.

It:
- opens a camera
- calibrates the board
- detects robot markers
- estimates robot state
- computes waypoint-following commands
- streams commands to the Pi

## Command packet format

The main.py file expects commands encoded in the following format:
```json
{
  "throttle": 0.4,
  "steering": -0.2,
}
```
Pi 5 expects extended packets from the HAL layer:
```json
{
  "left_motor_pwm_value": 1,
  "right_motor_pwm_value": 1,
  "steering_pwm_value_us": 1500,
  "manipulator_servo1_pwm_value_us":1500,
  "manipulator_servo2_pwm_value_us":1500,
}
```

### Field meanings

- `throttle`: normalized forward/reverse command in `[-1, 1]`
- `steering`: normalized steering command in `[-1, 1]`
- `left_motor_pwm_value`: ENABLE signal for left motor
- `right_motor_pwm_value`: ENABLE signal for right motor
- `steering_pwm_value_us`: pulse width for steering servo
- `manipulator_servo1_pwm_value_us`: pulse width for manipulator servo 1
- `manipulator_servo2_pwm_value_us`: pulse width for manipulator servo 2

## Hardware assumptions

This codebase is written around the following setup:

- Raspberry Pi 5
- L298N motor driver
- PCA9685 servo controller
- 2 DC drive motors
- 1 steering servo
- 2 manipulator servos
- USB camera for CV mode

## Python dependencies

Install the required packages on the Raspberry Pi or development machine as needed.

### Core runtime

```bash
pip install lgpio adafruit-circuitpython-servokit adafruit-blinka
```

### CV module

```bash
pip install opencv-python numpy
```

### Controller client

```bash
pip install pygame
```


## Configuration

Most settings live in `config.py`.

- network settings:
  - `PI_IP`
  - `COMMAND_PORT`
  - `COMMAND_TIMEOUT_S`
- control loop:
  - `CONTROL_FREQUENCY`
  - `DT`
- motion limits:
  - `MAX_SHAFT_SPEED`
  - `MAX_STEERING_ANGLE`
- motor PID gains:
  - `LEFT_MOTOR_KP`, `LEFT_MOTOR_KI`, `LEFT_MOTOR_KD`
  - `RIGHT_MOTOR_KP`, `RIGHT_MOTOR_KI`, `RIGHT_MOTOR_KD`
- servo calibration:
  - `SERVO*_MIN_US`
  - `SERVO*_CENTER_US`
  - `SERVO*_MAX_US`
- PCA9685 settings:
  - `PCA9685_I2C_ADDRESS`
  - `PCA9685_PWM_FREQUENCY`
  - `PCA9685_CHANNELS`
- motor wiring:
  - `MOTOR_CONFIGS`

## Running the project

### 1. Start the robot control loop on the Pi

```bash
python main.py
```

This starts the UDP receiver and hardware control loop.

### 2. Keyboard teleoperation from a laptop

```bash
python teleop_client.py
```

Keyboard controls:

- `W / S`: increase/decrease throttle
- `A / D`: steer left/right
- `I / K`: move manipulator servo 1
- `J / L`: move manipulator servo 2

### 3. PS5 controller teleoperation

```bash
python controller_client.py
```


Default mapping:
- `R2`: forward throttle
- `L2`: reverse throttle
- `Right Stick X`: steering

### 4. Run the CV waypoint module

```bash
python run_cv_module.py
```

Controls inside the CV window:

- `c`: calibrate board corners
- `l`: load saved calibration
- `r`: reset state estimator
- left click: set waypoint
- right click: clear waypoint
- `q` or `ESC`: quit

## Test scripts

### Motor test

```bash
python tests/motor_test.py
```

Use this to verify the motor outputs and wiring.

### Servo test

```bash
python tests/servo_test.py
```

Use this to verify PCA9685 servo motion.

### Camera index test

```bash
python tests/test_cam_index.py
```


## Data flow summary

At each control step, the system roughly does:

1. receive latest UDP command
2. apply watchdog timeout logic
3. convert normalized command into physical targets
4. compute motor PWM commands
5. compute steering servo pulse width
6. forward everything to the HAL
7. apply commands to the motors and servos

