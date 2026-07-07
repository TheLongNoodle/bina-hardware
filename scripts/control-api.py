from gpiozero import LED
from http.server import BaseHTTPRequestHandler, HTTPServer
import lgpio
import smbus2
import time
import json
import math

PORT = 8071

# =============================================================================
# LIS3DH Accelerometer Sensor (I2C)
# =============================================================================
LIS3DH_ADDR = 0x18  # or 0x19 if SA0 is HIGH

# LIS3DH Registers
LIS3DH_WHO_AM_I = 0x0F
LIS3DH_CTRL_REG1 = 0x20
LIS3DH_CTRL_REG4 = 0x23
LIS3DH_OUT_X_L = 0x28

class LIS3DH:
    def __init__(self, bus_num=1):
        self.bus = None
        self.initialized = False
        self.addr = LIS3DH_ADDR
        self.accel_scale = 2.0 / 32768.0  # ±2g default (16-bit)

        try:
            self.bus = smbus2.SMBus(bus_num)
            # Try default address first, then alternate
            if not self._try_init(0x18):
                if not self._try_init(0x19):
                    print("LIS3DH not found at 0x18 or 0x19")
        except Exception as e:
            print(f"LIS3DH init failed: {e}")
            self.initialized = False

    def _try_init(self, addr):
        try:
            self.addr = addr
            device_id = self.bus.read_byte_data(addr, LIS3DH_WHO_AM_I)
            if device_id == 0x33:  # LIS3DH ID
                self._init_sensor()
                self.initialized = True
                print(f"LIS3DH found at {hex(addr)}")
                return True
        except:
            pass
        return False

    def _init_sensor(self):
        # CTRL_REG1: 100Hz, all axes enabled
        self.bus.write_byte_data(self.addr, LIS3DH_CTRL_REG1, 0x57)
        time.sleep(0.01)

        # CTRL_REG4: ±2g, high resolution mode
        self.bus.write_byte_data(self.addr, LIS3DH_CTRL_REG4, 0x08)
        time.sleep(0.01)

    def _read_axis(self, reg_low):
        # Read with auto-increment (set MSB of register address)
        low = self.bus.read_byte_data(self.addr, reg_low | 0x80)
        high = self.bus.read_byte_data(self.addr, (reg_low + 1) | 0x80)
        val = (high << 8) | low
        if val >= 0x8000:
            val = val - 0x10000
        return val

    def get_device_id(self):
        if not self.initialized:
            return None
        try:
            return self.bus.read_byte_data(self.addr, LIS3DH_WHO_AM_I)
        except:
            return None

    def read_accel(self):
        if not self.initialized:
            return None
        try:
            ax = self._read_axis(LIS3DH_OUT_X_L) * self.accel_scale
            ay = self._read_axis(LIS3DH_OUT_X_L + 2) * self.accel_scale
            az = self._read_axis(LIS3DH_OUT_X_L + 4) * self.accel_scale
            return {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4), "unit": "g"}
        except Exception as e:
            return {"error": str(e)}

    def read_gyro(self):
        # LIS3DH has no gyroscope
        return {"error": "LIS3DH is accelerometer only - no gyroscope"}

    def read_mag(self):
        # LIS3DH has no magnetometer
        return {"error": "LIS3DH is accelerometer only - no magnetometer"}

    def read_temp(self):
        # LIS3DH has a temperature sensor but it's relative, not absolute
        return {"error": "LIS3DH temperature sensor not implemented"}

    def read_all(self):
        if not self.initialized:
            return {"error": "LIS3DH not initialized"}
        return {
            "accelerometer": self.read_accel(),
            "gyroscope": {"note": "Not available on LIS3DH"},
            "magnetometer": {"note": "Not available on LIS3DH"},
            "timestamp": time.time()
        }

    def get_orientation(self):
        """Calculate pitch and roll from accelerometer data"""
        if not self.initialized:
            return None
        accel = self.read_accel()
        if accel is None or "error" in accel:
            return accel

        ax, ay, az = accel["x"], accel["y"], accel["z"]

        # Calculate pitch and roll
        pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2)) * 180 / math.pi
        roll = math.atan2(ay, az) * 180 / math.pi

        return {
            "pitch": round(pitch, 2),
            "roll": round(roll, 2),
            "unit": "degrees"
        }

    def get_status(self):
        return {
            "initialized": self.initialized,
            "device_id": hex(self.get_device_id()) if self.get_device_id() else None,
            "expected_id": "0x33 (LIS3DH)",
            "sensor_type": "Accelerometer only (no gyro/mag)",
            "accel_range": "±2g",
            "i2c_address": hex(self.addr)
        }

# Initialize LIS3DH
mpu = LIS3DH()  # Keep variable name for API compatibility
led = LED(21)
led_state = False
is_moving = False
STEP = 18
DIR = 23
EN = 24

h = lgpio.gpiochip_open(0)

lgpio.gpio_claim_output(h, STEP)
lgpio.gpio_claim_output(h, DIR)
lgpio.gpio_claim_output(h, EN)

# Disable driver at startup to save power (EN is active LOW)
lgpio.gpio_write(h, EN, 1)

STEPS_PER_REV = 190

MAX_SPEED = 2000   # steps/sec
MIN_SPEED = 200
ACCEL = 5

# The lowest function to move the motor in the direction set in the DIR pin
def step_pulse(delay):
    lgpio.gpio_write(h, STEP, 1)
    time.sleep(delay)
    lgpio.gpio_write(h, STEP, 0)
    time.sleep(delay)

# Abstraction in the step_pulse allowing setting the direction and number of steps
def move(steps, direction=1):
    global is_moving
    is_moving = True

    # Enable motor before movement
    lgpio.gpio_write(h, EN, 0)
    time.sleep(0.01)  # Small delay for driver to stabilize

    lgpio.gpio_write(h, DIR, direction)

    speed = MIN_SPEED

    for _ in range(steps):
        if not is_moving:
            break
        # accelerate smoothly
        if speed < MAX_SPEED:
            speed += ACCEL

        delay = 1 / (2 * speed)  # half-period
        step_pulse(delay)

    # Disable motor after movement to save power
    lgpio.gpio_write(h, EN, 1)
    is_moving = False

# Another abstraction allowing us to use revolutions instead
def rotate(revolutions, direction=1):
    steps = int(revolutions * STEPS_PER_REV)
    move(steps, direction)

def stop_motor():
    global is_moving
    is_moving = False
    lgpio.gpio_write(h, EN, 1)  # Disable motor on stop

def disable_motor():
    stop_motor()
    lgpio.gpio_write(h, EN, 1)  # EN is active LOW, so 1 disables

def enable_motor():
    lgpio.gpio_write(h, EN, 0)  # EN is active LOW, so 0 enables

class MotorHandler(BaseHTTPRequestHandler):
    def send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        body = self.rfile.read(content_length)
        return json.loads(body.decode())

    def do_GET(self):
        if self.path == "/status":
            self.send_json(200, {
                "is_moving": is_moving,
                "steps_per_rev": STEPS_PER_REV,
                "max_speed": MAX_SPEED
            })
        elif self.path == "/":
            self.send_json(200, {"message": "Motor Control API", "endpoints": [
                "GET  /status        - Motor status",
                "GET  /led           - Toggle LED on/off",
                "GET  /gyro          - All IMU sensor data",
                "GET  /gyro/accel    - Accelerometer (g)",
                "GET  /gyro/orientation - Pitch/Roll",
                "GET  /gyro/status   - Sensor status",
                "POST /move {steps, direction}",
                "POST /rotate {revolutions, direction}",
                "POST /stop",
                "POST /enable",
                "POST /disable",
                "POST /led {count}   - Blink LED"
            ]})
        # MPU9250 IMU endpoints
        elif self.path == "/gyro":
            self.send_json(200, mpu.read_all())
        elif self.path == "/gyro/accel":
            data = mpu.read_accel()
            self.send_json(200 if data else 500, data or {"error": "Sensor not available"})
        elif self.path == "/gyro/rotation":
            data = mpu.read_gyro()
            self.send_json(200 if data else 500, data or {"error": "Sensor not available"})
        elif self.path == "/gyro/mag":
            data = mpu.read_mag()
            self.send_json(200 if data else 500, data or {"error": "Sensor not available"})
        elif self.path == "/gyro/temp":
            data = mpu.read_temp()
            self.send_json(200 if data else 500, data or {"error": "Sensor not available"})
        elif self.path == "/gyro/orientation":
            data = mpu.get_orientation()
            self.send_json(200 if data else 500, data or {"error": "Sensor not available"})
        elif self.path == "/gyro/status":
            self.send_json(200, mpu.get_status())
        elif self.path == "/led":
            global led_state
            led_state = not led_state
            if led_state:
                led.on()
            else:
                led.off()
            self.send_json(200, {"led": "on" if led_state else "off"})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        try:
            body = self.read_json_body()

            if self.path == "/move":
                steps = body.get("steps", 100)
                direction = body.get("direction", 1)
                move(steps, direction)
                self.send_json(200, {"success": True, "steps": steps, "direction": direction})

            elif self.path == "/rotate":
                revolutions = body.get("revolutions", 1)
                direction = body.get("direction", 1)
                rotate(revolutions, direction)
                self.send_json(200, {"success": True, "revolutions": revolutions, "direction": direction})

            elif self.path == "/stop":
                stop_motor()
                self.send_json(200, {"success": True, "message": "Motor stopped"})

            elif self.path == "/enable":
                enable_motor()
                self.send_json(200, {"success": True, "message": "Motor enabled"})

            elif self.path == "/disable":
                disable_motor()
                self.send_json(200, {"success": True, "message": "Motor disabled"})

            elif self.path == "/led":
                # Blink LED for testing
                count = body.get("count", 3)
                for _ in range(count):
                    led.on()
                    time.sleep(0.5)
                    led.off()
                    time.sleep(0.5)
                self.send_json(200, {"success": True, "blinks": count})

            else:
                self.send_json(404, {"error": "Endpoint not found"})

        except json.JSONDecodeError:
            self.send_json(400, {"error": "Invalid JSON"})
        except Exception as e:
            self.send_json(500, {"error": str(e)})

if __name__ == "__main__":
    print(f"Motor Control API starting on port {PORT}...")
    print("Motor Endpoints:")
    print("  GET  /              - API info")
    print("  GET  /status        - Motor status")
    print("  GET  /led           - Toggle LED on/off")
    print("  POST /move          - Move steps {steps, direction}")
    print("  POST /rotate        - Rotate {revolutions, direction}")
    print("  POST /stop          - Stop motor")
    print("  POST /enable        - Enable motor driver")
    print("  POST /disable       - Disable motor driver")
    print("  POST /led           - Blink LED {count}")
    print("LIS3DH Accelerometer Endpoints:")
    print("  GET  /gyro          - All sensor data")
    print("  GET  /gyro/accel    - Accelerometer X/Y/Z (g)")
    print("  GET  /gyro/orientation - Pitch/Roll angles")
    print("  GET  /gyro/status   - Sensor status")
    print(f"LIS3DH Status: {'Initialized' if mpu.initialized else 'Not connected'}")
    server = HTTPServer(("0.0.0.0", PORT), MotorHandler)
    server.serve_forever()

