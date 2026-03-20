# Data Flow

[ Command Input ] 

        ↓
[ Supervisor / Safety ] 

        ↓
[ Motion Manager ]

        ↓
[ Controllers ] 

   ├── Motor Controller (left/right)

   └── Servo Controller (steering)
        ↓
[ Hardware Abstraction Layer (HAL) ]

        ↓
[ Physical Robot ]


# At 60/120Hz
1. Read command
2. Check safety / update state
3. Compute desired motion
4. Convert to actuator targets
5. Convert to PWM / signals
6. Send to hardware

cmd = {
    "throttle": 0.6,          # forward/backward [-1, 1]
    "steering": 0.2,          # left/right [-1, 1]
    "mode": "MANUAL",         # or AUTONOMOUS
    "timestamp": 123456789.0
}

throttle: normalized effort of the motors
+1.0 → full forward
0.0 → stop
-1.0 → full reverse

steering: normalized absolute position of the steering wheel
+1.0 → turn right (or max steering angle right)
0.0 → straight
-1.0 → turn left

# Motion Manager
## Input:
cmd = {
    "throttle": t,
    "steering": s
}
## Output
target = {
    "left_shaft_speed": t * MAX_SHAFT_SPEED,
    "right_shaft_speed": t * MAX_SHAFT_SPEED,
    "steering_angle" = s * MAX_STEERING_ANGLE
}

# Motor Controller
Convert to robot space speed and do PID
## Input
cmd = {
    left_shaft_speed, right_shaft_speed
}
## Output
target ={
    target_robot_speed = GEAR_RATIO * cmd 
    error = target_speed - measured_speed (robot)
    motor_pwm_value = PID(error), normalized PWM output in [-1,1]
}

# Servo Controller
Servo has built in PID controller
## Input
cmd = {
    steering_angle
}

## Output
target = {
    servo_pwm_valu_us_ = steering_angle_to_pwm(servo_pwm_value), time of voltage = HIGH at every cycle
}

# Hardware Abstraction Layer
## Input
cmd = {
    left_motor_pwm_value,
    right_motor_pwm_value,
    steering_pwm_value_us
}
## Output
target = {
    left_direction = sign(left_motor_pwm)
    left_duty = abs(left_motor_pwm)
    right_direction = sign(right_motor_pwm)
    right_duty = abs(right_motor_pwm)
    steering_pwm_value_us = steering_pwm_value_us
}



