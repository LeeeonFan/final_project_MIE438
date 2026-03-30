import time
import lgpio

GPIO_CHIP = 4

LEFT_IN1 = 18
LEFT_IN2 = 19
LEFT_EN  = 12

h = lgpio.gpiochip_open(GPIO_CHIP)

try:
    lgpio.gpio_claim_output(h, LEFT_IN1)
    lgpio.gpio_claim_output(h, LEFT_IN2)
    lgpio.gpio_claim_output(h, LEFT_EN)

    print("Left motor forward for 3 seconds")
    lgpio.gpio_write(h, LEFT_IN1, 1)
    lgpio.gpio_write(h, LEFT_IN2, 0)
    lgpio.gpio_write(h, LEFT_EN, 1)
    time.sleep(3)

    print("Stop for 2 seconds")
    lgpio.gpio_write(h, LEFT_EN, 0)
    lgpio.gpio_write(h, LEFT_IN1, 0)
    lgpio.gpio_write(h, LEFT_IN2, 0)
    time.sleep(2)

    print("Left motor reverse for 3 seconds")
    lgpio.gpio_write(h, LEFT_IN1, 0)
    lgpio.gpio_write(h, LEFT_IN2, 1)
    lgpio.gpio_write(h, LEFT_EN, 1)
    time.sleep(3)

    print("Final stop")
    lgpio.gpio_write(h, LEFT_EN, 0)
    lgpio.gpio_write(h, LEFT_IN1, 0)
    lgpio.gpio_write(h, LEFT_IN2, 0)

finally:
    lgpio.gpiochip_close(h)