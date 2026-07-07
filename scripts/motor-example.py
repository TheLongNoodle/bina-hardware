import lgpio
import time

# ---------------- PINS ----------------
STEP = 18
DIR = 23
EN = 24

h = lgpio.gpiochip_open(0)

lgpio.gpio_claim_output(h, STEP)
lgpio.gpio_claim_output(h, DIR)
lgpio.gpio_claim_output(h, EN)

# Enable driver (EN is active LOW)
lgpio.gpio_write(h, EN, 0)

# ---------------- CONFIG ----------------
STEPS_PER_REV = 1600
DELAY = 0.002

# ---------------- ROTATE ----------------
def rotate(revolutions, direction=1):
    lgpio.gpio_write(h, DIR, direction)
    for _ in int(revolutions * STEPS_PER_REV):
        lgpio.gpio_write(h, STEP, 1)
        time.sleep(DELAY)
        lgpio.gpio_write(h, STEP, 0)
        time.sleep(DELAY)

# ---------------- RUN TEST ----------------
try:
    print("Running motor...")
    rotate(1, 1)
    print("Done!")

finally:
    lgpio.gpio_write(h, EN, 1)  # disable motor
    lgpio.gpiochip_close(h)
    print("Task finished!")
