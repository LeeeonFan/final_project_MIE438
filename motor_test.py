import time
import lgpio

GPIO_CHIP = 4

LEFT_IN1 = 17
LEFT_IN2 = 22
LEFT_EN = 12

h = lgpio.gpiochip_open(GPIO_CHIP)

try:
    lgpio.gpio_claim_output(h, LEFT_IN1)
    lgpio.gpio_claim_output(h, LEFT_IN2)

    print("Left motor forward for 3 seconds")
    lgpio.gpio_write(h, LEFT_IN1, 1)
    lgpio.gpio_write(h, LEFT_IN2, 0)
    lgpio.tx_pwm(h, LEFT_EN, 1000, 100.0)
    time.sleep(3)

    print("Stop")
    lgpio.gpio_write(h, LEFT_IN1, 0)
    lgpio.gpio_write(h, LEFT_IN2, 0)
    lgpio.tx_pwm(h, LEFT_EN, 1000, 0.0)

finally:
    lgpio.gpiochip_close(h)