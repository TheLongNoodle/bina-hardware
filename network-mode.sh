#!/bin/bash
# Switch between WiFi Direct mode and regular networking mode

usage() {
    echo "Usage: $0 [wifi|p2p|status]"
    echo ""
    echo "  wifi   - Enable regular WiFi (for SSH/SCP access)"
    echo "  p2p    - Enable WiFi Direct (for phone connection)"
    echo "  status - Show current mode"
    echo ""
}

status() {
    echo "=== Network Status ==="

    if systemctl is-active --quiet NetworkManager; then
        echo "Mode: Regular WiFi (NetworkManager active)"
    elif systemctl is-active --quiet wpa_supplicant; then
        echo "Mode: WiFi Direct (wpa_supplicant active)"
    else
        echo "Mode: Unknown"
    fi

    echo ""
    echo "Interfaces:"
    ip -br addr show | grep -E "wlan|p2p|eth"
}

wifi_mode() {
    echo "Switching to regular WiFi mode..."

    # Stop WiFi Direct services
    sudo systemctl stop WiFiDirectAutorun.service 2>/dev/null || true
    sudo systemctl stop camera-streamer.service 2>/dev/null || true
    sudo killall wpa_supplicant 2>/dev/null || true
    sudo killall dnsmasq 2>/dev/null || true
    sudo ip link set p2p-wlan0-0 down 2>/dev/null || true

    # Enable NetworkManager
    sudo systemctl enable NetworkManager 2>/dev/null || true
    sudo systemctl start NetworkManager

    echo ""
    echo "Regular WiFi enabled."
    echo "Waiting for connection..."
    sleep 3

    # Show IP
    echo ""
    ip -br addr show wlan0 2>/dev/null || echo "wlan0 not ready yet"
    echo ""
    echo "You can now SSH/SCP to this device."
    echo "Run '$0 p2p' to switch back to WiFi Direct mode."
}

p2p_mode() {
    echo "Switching to WiFi Direct mode..."

    # Stop NetworkManager
    sudo systemctl stop NetworkManager 2>/dev/null || true
    sudo systemctl disable NetworkManager 2>/dev/null || true

    # Start WiFi Direct
    sudo systemctl start WiFiDirectAutorun.service
    sudo systemctl start camera-streamer.service 2>/dev/null || true

    echo ""
    echo "WiFi Direct enabled."
    echo "Device name: Bina-Camera"
    echo "WPS PIN: 12345678"
    echo "Pi IP: 192.168.1.2"
    echo ""
    echo "Run '$0 wifi' to switch back to regular WiFi."
}

case "$1" in
    wifi)
        wifi_mode
        ;;
    p2p|direct)
        p2p_mode
        ;;
    status|"")
        status
        ;;
    *)
        usage
        ;;
esac
