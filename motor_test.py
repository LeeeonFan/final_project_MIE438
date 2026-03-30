from hal import HAL
import time

hal = HAL()

def apply_outputs(
    left_motor=0.0,
    right_motor=0.0,
    steering_us=1500,
    servo2_us=1500,
    servo3_us=1500,
):
    hal.apply({
        "left_motor_pwm_value": left_motor,
        "right_motor_pwm_value": right_motor,
        "steering_pwm_value_us": steering_us,
        "servo2_pwm_value_us": servo2_us,
        "servo3_pwm_value_us": servo3_us,
    })

try:
    print("Centering all outputs...")
    apply_outputs()
    time.sleep(1.5)

    print("Testing steering channel...")
    for pwm in [1500, 1400, 1600, 1300, 1700, 1500]:
        print(f"steering_pwm_value_us = {pwm}")
        apply_outputs(steering_us=pwm)
        time.sleep(1.0)

    print("Testing servo2 channel...")
    for pwm in [1500, 1400, 1600, 1300, 1700, 1500]:
        print(f"servo2_pwm_value_us = {pwm}")
        apply_outputs(servo2_us=pwm)
        time.sleep(1.0)

    print("Testing servo3 channel...")
    for pwm in [1500, 1400, 1600, 1300, 1700, 1500]:
        print(f"servo3_pwm_value_us = {pwm}")
        apply_outputs(servo3_us=pwm)
        time.sleep(1.0)

    print("Testing motors gently...")
    apply_outputs(left_motor=0.15, right_motor=0.15)
    time.sleep(1.0)

    print("Stopping motors...")
    apply_outputs()
    time.sleep(1.0)

finally:
    print("Cleaning up...")
    hal.cleanup()