#!/bin/bash
# Cleanup script - removes all configurations
# Use this before re-running init.sh or to reset the system

echo "=== Bina Camera Cleanup ==="

# Stop services
echo "Stopping services..."
sudo systemctl stop WiFiDirectAutorun.service 2>/dev/null || true
sudo systemctl stop camera-streamer.service 2>/dev/null || true
sudo systemctl disable WiFiDirectAutorun.service 2>/dev/null || true
sudo systemctl disable camera-streamer.service 2>/dev/null || true

# Kill processes
echo "Killing processes..."
sudo killall wpa_supplicant 2>/dev/null || true
sudo killall dnsmasq 2>/dev/null || true

# Remove P2P interface if exists
echo "Removing P2P interface..."
sudo ip link set p2p-wlan0-0 down 2>/dev/null || true

# Remove symlinks
echo "Removing systemd symlinks..."
sudo rm -f /etc/systemd/system/WiFiDirectAutorun.service
sudo rm -f /etc/systemd/system/camera-streamer.service

# Remove dnsmasq config
echo "Removing dnsmasq config..."
sudo rm -f /etc/dnsmasq.d/p2p-wlan0.conf

# Reload systemd
sudo systemctl daemon-reload

echo ""
echo "Cleanup complete!"
echo "Run ./init.sh to set up again"
