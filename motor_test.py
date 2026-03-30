import RPi.GPIO as GPIO
import time

# Pin assignments
IN1, IN2, IN3, IN4 = 18, 19, 20, 21
ENA, ENB = 12, 13

GPIO.setmode(GPIO.BCM)
GPIO.setup([IN1, IN2, IN3, IN4, ENA, ENB], GPIO.OUT)

# Create PWM instances
pwm_a = GPIO.PWM(ENA, 1000)
pwm_b = GPIO.PWM(ENB, 1000)
pwm_a.start(0)
pwm_b.start(0)

def motor_control(motor, direction, speed):
    """Control motor A or B with direction and speed (0-100)."""
    if motor == 'A':
        if direction == 'forward':
            GPIO.output(IN1, GPIO.HIGH)
            GPIO.output(IN2, GPIO.LOW)
        else:
            GPIO.output(IN1, GPIO.LOW)
            GPIO.output(IN2, GPIO.HIGH)
        pwm_a.ChangeDutyCycle(speed)

    elif motor == 'B':
        if direction == 'forward':
            GPIO.output(IN3, GPIO.HIGH)
            GPIO.output(IN4, GPIO.LOW)
        else:
            GPIO.output(IN3, GPIO.LOW)
            GPIO.output(IN4, GPIO.HIGH)
        pwm_b.ChangeDutyCycle(speed)

try:
    # Example usage
    motor_control('A', 'forward', 75)   # Motor A forward at 75% speed
    time.sleep(2)

    motor_control('A', 'backward', 50)  # Motor A backward at 50% speed
    time.sleep(2)

    motor_control('B', 'forward', 75)   # Motor B forward at 75% speed
    time.sleep(2)

    motor_control('B', 'backward', 50)  # Motor B backward at 50% speed
    time.sleep(2)

finally:
    pwm_a.stop()
    pwm_b.stop()
    GPIO.cleanup()