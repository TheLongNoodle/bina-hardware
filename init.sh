#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Bina Camera Setup ==="
echo "Project directory: $DIR"

# Install required packages
echo "[1/10] Installing required packages..."
sudo apt-get update
sudo apt-get install -y dnsmasq wpasupplicant python3-picamera2 python3-simplejpeg python3-smbus i2c-tools

# Enable I2C interface for LIS3DH accelerometer
echo "[2/10] Enabling I2C interface..."
sudo raspi-config nonint do_i2c 0

# Configure dnsmasq for DHCP on P2P interface
echo "[3/10] Configuring dnsmasq for WiFi Direct..."
sudo tee /etc/dnsmasq.d/p2p-wlan0.conf > /dev/null << 'EOF'
interface=p2p-wlan0-0
bind-interfaces
dhcp-range=192.168.1.10,192.168.1.50,255.255.255.0,24h
dhcp-option=option:router,192.168.1.2
dhcp-option=option:dns-server,8.8.8.8
EOF

# Stop dnsmasq for now (will be started by WiFiDirectAutorun.sh)
sudo systemctl stop dnsmasq 2>/dev/null || true
sudo systemctl disable dnsmasq 2>/dev/null || true

# Enable script execution
echo "[4/10] Setting up scripts..."
sudo chmod +x "$DIR"/wpa_supplicant/WiFiDirectAutorun.sh
sudo chmod +x "$DIR"/scripts/*.py 2>/dev/null || true
sudo chmod +x "$DIR"/test_connection.py 2>/dev/null || true

# Update service files with correct paths
echo "[5/10] Configuring systemd services..."
sed -i "s|ExecStart=.*|ExecStart=$DIR/wpa_supplicant/WiFiDirectAutorun.sh|" "$DIR/wpa_supplicant/WiFiDirectAutorun.service"
sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $DIR/scripts/libcamera-streamer.py|" "$DIR/scripts/camera-streamer.service"
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$DIR/scripts|" "$DIR/scripts/control-api.service"
sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $DIR/scripts/control-api.py|" "$DIR/scripts/control-api.service"

# Remove old symlinks if exist, then create new ones
sudo rm -f /etc/systemd/system/WiFiDirectAutorun.service
sudo rm -f /etc/systemd/system/camera-streamer.service
sudo rm -f /etc/systemd/system/control-api.service
sudo ln -s "$DIR"/wpa_supplicant/WiFiDirectAutorun.service /etc/systemd/system/WiFiDirectAutorun.service
sudo ln -s "$DIR"/scripts/camera-streamer.service /etc/systemd/system/camera-streamer.service
sudo ln -s "$DIR"/scripts/control-api.service /etc/systemd/system/control-api.service

# Disable NetworkManager if it exists (conflicts with wpa_supplicant)
echo "[6/10] Disabling NetworkManager..."
if systemctl is-active --quiet NetworkManager; then
    sudo systemctl stop NetworkManager
    sudo systemctl disable NetworkManager
fi

# Enable WiFi Direct service
echo "[7/10] Enabling WiFi Direct service..."
sudo systemctl daemon-reload
sudo systemctl enable WiFiDirectAutorun.service
sudo systemctl start WiFiDirectAutorun.service

# Enable camera streamer service
echo "[8/10] Enabling camera streamer service..."
sudo systemctl enable camera-streamer.service
sudo systemctl start camera-streamer.service

# Enable control API service
echo "[9/10] Enabling control API service..."
sudo systemctl enable control-api.service
sudo systemctl start control-api.service

echo ""
echo "[10/10] Verifying services..."
sleep 2
systemctl is-active --quiet WiFiDirectAutorun.service && echo "  WiFi Direct: Running" || echo "  WiFi Direct: FAILED"
systemctl is-active --quiet camera-streamer.service && echo "  Camera Streamer: Running" || echo "  Camera Streamer: FAILED"
systemctl is-active --quiet control-api.service && echo "  Control API: Running" || echo "  Control API: FAILED"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "WiFi Direct:"
echo "  Network name: Bina-Camera"
echo "  WPS PIN: 12345678"
echo "  Pi IP: 192.168.1.2"
echo ""
echo "Camera Stream:"
echo "  URL: http://192.168.1.2:8070/"
echo "  Stream: http://192.168.1.2:8070/stream.mjpg"
echo "  Snapshot: http://192.168.1.2:8070/snapshot.jpg"
echo "Control API (Motor + LIS3DH):"
echo "  URL: http://192.168.1.2:8071/"
echo "  Gyro: http://192.168.1.2:8071/gyro"
echo ""
echo "Commands:"
echo "  Check WiFi:    sudo systemctl status WiFiDirectAutorun.service"
echo "  Check Camera:  sudo systemctl status camera-streamer.service"
echo "  Check Control: sudo systemctl status control-api.service"
echo "  View logs:     journalctl -u control-api.service -f"
echo "  Check I2C:     i2cdetect -y 1  (LIS3DH should show at 0x18 or 0x19)"
