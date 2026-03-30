from hal import HAL
import time

hal = HAL()

try:
    # center everything
    hal.apply({
        "left_motor_pwm_value": 0.0,
        "right_motor_pwm_value": 0.0,
        "steering_pwm_value_us": 1500,
        "servo2_pwm_value_us": 1500,
        "servo3_pwm_value_us": 1500,
    })
    time.sleep(1)

    # move servo1
    hal.apply({
        "left_motor_pwm_value": 0.0,
        "right_motor_pwm_value": 0.0,
        "steering_pwm_value_us": 1200,
        "servo2_pwm_value_us": 1500,
        "servo3_pwm_value_us": 1500,
    })
    time.sleep(1)

    hal.apply({
        "left_motor_pwm_value": 0.0,
        "right_motor_pwm_value": 0.0,
        "steering_pwm_value_us": 1800,
        "servo2_pwm_value_us": 1500,
        "servo3_pwm_value_us": 1500,
    })
    time.sleep(1)

    # test motors gently
    hal.apply({
        "left_motor_pwm_value": 0.2,
        "right_motor_pwm_value": 0.2,
        "steering_pwm_value_us": 1500,
        "servo2_pwm_value_us": 1500,
        "servo3_pwm_value_us": 1500,
    })
    time.sleep(1)

finally:
    hal.cleanup()