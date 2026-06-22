from gpiozero import LED
from http.server import BaseHTTPRequestHandler, HTTPServer
import lgpio
import smbus2
import time
import json
import math

PORT = 8071

# =============================================================================
# MPU9250 IMU Sensor (I2C)
# =============================================================================
MPU9250_ADDR = 0x68
AK8963_ADDR = 0x0C  # Magnetometer

# MPU9250 Registers
PWR_MGMT_1 = 0x6B
PWR_MGMT_2 = 0x6C
GYRO_CONFIG = 0x1B
ACCEL_CONFIG = 0x1C
ACCEL_CONFIG2 = 0x1D
INT_PIN_CFG = 0x37
ACCEL_XOUT_H = 0x3B
GYRO_XOUT_H = 0x43
TEMP_OUT_H = 0x41
WHO_AM_I = 0x75

# AK8963 Magnetometer Registers
AK8963_WHO_AM_I = 0x00
AK8963_CNTL1 = 0x0A
AK8963_ST1 = 0x02
AK8963_HXL = 0x03

class MPU9250:
    def __init__(self, bus_num=1):
        self.bus = None
        self.initialized = False
        self.gyro_scale = 250.0 / 32768.0  # ±250°/s default
        self.accel_scale = 2.0 / 32768.0   # ±2g default
        self.mag_scale = 4912.0 / 32760.0  # μT
        self.mag_calibration = [1.0, 1.0, 1.0]

        try:
            self.bus = smbus2.SMBus(bus_num)
            self._init_sensor()
            self.initialized = True
        except Exception as e:
            print(f"MPU9250 init failed: {e}")
            self.initialized = False

    def _init_sensor(self):
        # Wake up MPU9250
        self.bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x00)
        time.sleep(0.1)

        # Auto select best clock source
        self.bus.write_byte_data(MPU9250_ADDR, PWR_MGMT_1, 0x01)
        time.sleep(0.1)

        # Configure gyro: ±250°/s
        self.bus.write_byte_data(MPU9250_ADDR, GYRO_CONFIG, 0x00)

        # Configure accelerometer: ±2g
        self.bus.write_byte_data(MPU9250_ADDR, ACCEL_CONFIG, 0x00)

        # Enable bypass mode to access magnetometer directly
        self.bus.write_byte_data(MPU9250_ADDR, INT_PIN_CFG, 0x02)
        time.sleep(0.1)

        # Initialize magnetometer (continuous measurement mode, 16-bit)
        try:
            self.bus.write_byte_data(AK8963_ADDR, AK8963_CNTL1, 0x00)
            time.sleep(0.01)
            self.bus.write_byte_data(AK8963_ADDR, AK8963_CNTL1, 0x16)  # 16-bit, 100Hz
            time.sleep(0.1)
        except:
            print("Magnetometer init failed (may not be present)")

    def _read_word(self, addr, reg):
        high = self.bus.read_byte_data(addr, reg)
        low = self.bus.read_byte_data(addr, reg + 1)
        val = (high << 8) | low
        if val >= 0x8000:
            val = val - 0x10000
        return val

    def _read_word_le(self, addr, reg):
        low = self.bus.read_byte_data(addr, reg)
        high = self.bus.read_byte_data(addr, reg + 1)
        val = (high << 8) | low
        if val >= 0x8000:
            val = val - 0x10000
        return val

    def get_device_id(self):
        if not self.initialized:
            return None
        try:
            return self.bus.read_byte_data(MPU9250_ADDR, WHO_AM_I)
        except:
            return None

    def read_accel(self):
        if not self.initialized:
            return None
        try:
            ax = self._read_word(MPU9250_ADDR, ACCEL_XOUT_H) * self.accel_scale
            ay = self._read_word(MPU9250_ADDR, ACCEL_XOUT_H + 2) * self.accel_scale
            az = self._read_word(MPU9250_ADDR, ACCEL_XOUT_H + 4) * self.accel_scale
            return {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4), "unit": "g"}
        except Exception as e:
            return {"error": str(e)}

    def read_gyro(self):
        if not self.initialized:
            return None
        try:
            gx = self._read_word(MPU9250_ADDR, GYRO_XOUT_H) * self.gyro_scale
            gy = self._read_word(MPU9250_ADDR, GYRO_XOUT_H + 2) * self.gyro_scale
            gz = self._read_word(MPU9250_ADDR, GYRO_XOUT_H + 4) * self.gyro_scale
            return {"x": round(gx, 4), "y": round(gy, 4), "z": round(gz, 4), "unit": "deg/s"}
        except Exception as e:
            return {"error": str(e)}

    def read_mag(self):
        if not self.initialized:
            return None
        try:
            # Check data ready
            st1 = self.bus.read_byte_data(AK8963_ADDR, AK8963_ST1)
            if not (st1 & 0x01):
                return {"x": 0, "y": 0, "z": 0, "unit": "uT", "ready": False}

            mx = self._read_word_le(AK8963_ADDR, AK8963_HXL) * self.mag_scale
            my = self._read_word_le(AK8963_ADDR, AK8963_HXL + 2) * self.mag_scale
            mz = self._read_word_le(AK8963_ADDR, AK8963_HXL + 4) * self.mag_scale

            # Read ST2 to signal data read complete
            self.bus.read_byte_data(AK8963_ADDR, 0x09)

            return {"x": round(mx, 2), "y": round(my, 2), "z": round(mz, 2), "unit": "uT", "ready": True}
        except Exception as e:
            return {"error": str(e)}

    def read_temp(self):
        if not self.initialized:
            return None
        try:
            raw = self._read_word(MPU9250_ADDR, TEMP_OUT_H)
            temp_c = (raw / 333.87) + 21.0
            return {"celsius": round(temp_c, 2)}
        except Exception as e:
            return {"error": str(e)}

    def read_all(self):
        if not self.initialized:
            return {"error": "MPU9250 not initialized"}
        return {
            "accelerometer": self.read_accel(),
            "gyroscope": self.read_gyro(),
            "magnetometer": self.read_mag(),
            "temperature": self.read_temp(),
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
            "expected_id": "0x71 (MPU9250) or 0x73 (MPU9255)",
            "gyro_range": "±250 deg/s",
            "accel_range": "±2g",
            "i2c_address": hex(MPU9250_ADDR)
        }

# Initialize MPU9250
mpu = MPU9250()
led = LED(21)
is_moving = False
STEP = 18
DIR = 23
EN = 24

h = lgpio.gpiochip_open(0)

lgpio.gpio_claim_output(h, STEP)
lgpio.gpio_claim_output(h, DIR)
lgpio.gpio_claim_output(h, EN)

# Enable driver (EN is active LOW)
lgpio.gpio_write(h, EN, 0)

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

    is_moving = False

# Another abstraction allowing us to use revolutions instead
def rotate(revolutions, direction=1):
    steps = int(revolutions * STEPS_PER_REV)
    move(steps, direction)

def stop_motor():
    global is_moving
    is_moving = False

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
                "GET  /gyro          - All IMU sensor data",
                "GET  /gyro/accel    - Accelerometer (g)",
                "GET  /gyro/rotation - Gyroscope (deg/s)",
                "GET  /gyro/mag      - Magnetometer (uT)",
                "GET  /gyro/temp     - Temperature (C)",
                "GET  /gyro/orientation - Pitch/Roll",
                "GET  /gyro/status   - Sensor status",
                "POST /move {steps, direction}",
                "POST /rotate {revolutions, direction}",
                "POST /stop",
                "POST /enable",
                "POST /disable",
                "POST /led {count}"
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
    print("  POST /move          - Move steps {steps, direction}")
    print("  POST /rotate        - Rotate {revolutions, direction}")
    print("  POST /stop          - Stop motor")
    print("  POST /enable        - Enable motor driver")
    print("  POST /disable       - Disable motor driver")
    print("  POST /led           - Blink LED {count}")
    print("MPU9250 IMU Endpoints:")
    print("  GET  /gyro          - All sensor data (accel, gyro, mag, temp)")
    print("  GET  /gyro/accel    - Accelerometer X/Y/Z (g)")
    print("  GET  /gyro/rotation - Gyroscope X/Y/Z (deg/s)")
    print("  GET  /gyro/mag      - Magnetometer X/Y/Z (uT)")
    print("  GET  /gyro/temp     - Temperature (Celsius)")
    print("  GET  /gyro/orientation - Pitch/Roll angles")
    print("  GET  /gyro/status   - Sensor status")
    print(f"MPU9250 Status: {'Initialized' if mpu.initialized else 'Not connected'}")
    server = HTTPServer(("0.0.0.0", PORT), MotorHandler)
    server.serve_forever()

