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
STEPS_PER_REV = 190

MAX_SPEED = 2000   # steps/sec
MIN_SPEED = 200
ACCEL = 5

# ---------------- STEP FUNCTION ----------------
def step_pulse(delay):
    lgpio.gpio_write(h, STEP, 1)
    time.sleep(delay)
    lgpio.gpio_write(h, STEP, 0)
    time.sleep(delay)

# ---------------- MOVE FUNCTION ----------------
def move(steps, direction=1):
    lgpio.gpio_write(h, DIR, direction)

    speed = MIN_SPEED

    for _ in range(steps):
        # accelerate smoothly
        if speed < MAX_SPEED:
            speed += ACCEL

        delay = 1 / (2 * speed)  # half-period
        step_pulse(delay)

# ---------------- HIGH LEVEL ----------------
def rotate(revolutions, direction=1):
    steps = int(revolutions * STEPS_PER_REV)
    move(steps, direction)

# ---------------- RUN TEST ----------------
try:
    print("Running motor...")

    rotate(50, 1)
    time.sleep(1)
    rotate(50, 0)

finally:
    lgpio.gpio_write(h, EN, 1)  # disable motor
    lgpio.gpiochip_close(h)
