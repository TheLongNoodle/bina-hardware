#!/bin/bash
# Note: Not using set -e because the monitoring loop should continue even if commands fail

DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_TAG="WiFiDirect"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    logger -t "$LOG_TAG" "$1"
}

log "Starting WiFi Direct setup from $DIR"

# Kill any existing wpa_supplicant instances
log "Stopping any existing wpa_supplicant..."
sudo killall wpa_supplicant 2>/dev/null || true
sleep 1

# Bring up wlan0 interface
log "Bringing up wlan0 interface..."
sudo ip link set wlan0 up
sleep 1

# Start wpa_supplicant
log "Starting wpa_supplicant..."
sudo wpa_supplicant -B -iwlan0 -Dnl80211 -c"$DIR"/wpa_supplicant.conf
sleep 2

# Create P2P group (this creates the p2p-wlan0-0 interface)
log "Creating P2P group..."
sudo wpa_cli -iwlan0 p2p_group_add
sleep 2

# Wait for p2p interface to appear
log "Waiting for P2P interface..."
for i in {1..10}; do
    if ip link show p2p-wlan0-0 &>/dev/null; then
        log "P2P interface p2p-wlan0-0 is up"
        break
    fi
    sleep 1
done

# Assign IP address to the P2P interface
log "Assigning IP 192.168.1.2 to P2P interface..."
sudo ip addr flush dev p2p-wlan0-0 2>/dev/null || true
sudo ip addr add 192.168.1.2/24 dev p2p-wlan0-0
sudo ip link set p2p-wlan0-0 up

# Start dnsmasq for DHCP on the P2P interface
log "Starting DHCP server (dnsmasq)..."
sudo killall dnsmasq 2>/dev/null || true
sleep 1
sudo dnsmasq --conf-file=/etc/dnsmasq.d/p2p-wlan0.conf --pid-file=/var/run/dnsmasq-p2p.pid

# Enable WPS for easy pairing
log "Enabling WPS..."
sudo wpa_cli -ip2p-wlan0-0 wps_pbc
sleep 1
sudo wpa_cli -ip2p-wlan0-0 wps_pin any 12345678

log "WiFi Direct setup complete!"
log "Device name: Bina-Camera"
log "WPS PIN: 12345678"
log "IP address: 192.168.1.2"

# Show connection info
echo ""
echo "============================================"
echo "  WiFi Direct is ready!"
echo "  Network name: Bina-Camera"
echo "  WPS PIN: 12345678"
echo "  Pi IP: 192.168.1.2"
echo "============================================"

# Monitor for client disconnections and re-enable WPS
# This runs in foreground to keep the service alive
log "Starting WPS monitor loop..."
while true; do
    # Re-enable WPS every 30 seconds to ensure new clients can connect
    sleep 30
    if ip link show p2p-wlan0-0 &>/dev/null; then
        wpa_cli -ip2p-wlan0-0 wps_pin any 12345678 >/dev/null 2>&1 || true
    else
        log "P2P interface lost, attempting to recreate..."
        sudo wpa_cli -iwlan0 p2p_group_add
        sleep 2
        if ip link show p2p-wlan0-0 &>/dev/null; then
            sudo ip addr flush dev p2p-wlan0-0 2>/dev/null || true
            sudo ip addr add 192.168.1.2/24 dev p2p-wlan0-0
            sudo ip link set p2p-wlan0-0 up
            sudo killall dnsmasq 2>/dev/null || true
            sudo dnsmasq --conf-file=/etc/dnsmasq.d/p2p-wlan0.conf --pid-file=/var/run/dnsmasq-p2p.pid
            wpa_cli -ip2p-wlan0-0 wps_pin any 12345678 >/dev/null 2>&1 || true
            log "P2P interface restored"
        fi
    fi
done

