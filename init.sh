#!/bin/bash
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Bina Camera Setup ==="
echo "Project directory: $DIR"

# Install required packages
echo "[1/8] Installing required packages..."
sudo apt-get update
sudo apt-get install -y dnsmasq wpasupplicant python3-picamera2 python3-simplejpeg

# Configure dnsmasq for DHCP on P2P interface
echo "[2/8] Configuring dnsmasq for WiFi Direct..."
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
echo "[3/8] Setting up scripts..."
sudo chmod +x "$DIR"/wpa_supplicant/WiFiDirectAutorun.sh
sudo chmod +x "$DIR"/scripts/*.py 2>/dev/null || true
sudo chmod +x "$DIR"/test_connection.py 2>/dev/null || true

# Update service files with correct paths
echo "[4/8] Configuring systemd services..."
sed -i "s|ExecStart=.*|ExecStart=$DIR/wpa_supplicant/WiFiDirectAutorun.sh|" "$DIR/wpa_supplicant/WiFiDirectAutorun.service"
sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $DIR/scripts/libcamera-streamer.py|" "$DIR/scripts/camera-streamer.service"

# Remove old symlinks if exist, then create new ones
sudo rm -f /etc/systemd/system/WiFiDirectAutorun.service
sudo rm -f /etc/systemd/system/camera-streamer.service
sudo ln -s "$DIR"/wpa_supplicant/WiFiDirectAutorun.service /etc/systemd/system/WiFiDirectAutorun.service
sudo ln -s "$DIR"/scripts/camera-streamer.service /etc/systemd/system/camera-streamer.service

# Disable NetworkManager if it exists (conflicts with wpa_supplicant)
echo "[5/8] Disabling NetworkManager..."
if systemctl is-active --quiet NetworkManager; then
    sudo systemctl stop NetworkManager
    sudo systemctl disable NetworkManager
fi

# Enable WiFi Direct service
echo "[6/8] Enabling WiFi Direct service..."
sudo systemctl daemon-reload
sudo systemctl enable WiFiDirectAutorun.service
sudo systemctl start WiFiDirectAutorun.service

# Enable camera streamer service
echo "[7/8] Enabling camera streamer service..."
sudo systemctl enable camera-streamer.service
sudo systemctl start camera-streamer.service

echo ""
echo "[8/8] Verifying services..."
sleep 2
systemctl is-active --quiet WiFiDirectAutorun.service && echo "  WiFi Direct: Running" || echo "  WiFi Direct: FAILED"
systemctl is-active --quiet camera-streamer.service && echo "  Camera Streamer: Running" || echo "  Camera Streamer: FAILED"

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
echo ""
echo "Commands:"
echo "  Check WiFi:  sudo systemctl status WiFiDirectAutorun.service"
echo "  Check Camera: sudo systemctl status camera-streamer.service"
echo "  View logs:   journalctl -u camera-streamer.service -f"
