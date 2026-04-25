#!/bin/bash

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Running script at $DIR"

# enabling sh execution and linking the service to systemd
sudo chmod +x "$DIR"/wpa_supplicant/WiFiDirectAutorun.sh
sudo ln -s "$DIR"/wpa_supplicant/WiFiDirectAutorun.service /etc/systemd/system/WiFiDirectAutorun.service

# disabling NetworkManager service
sudo systemctl stop NetworkManager
sudo systemctl disable NetworkManager

#enabling the WiFi direct autorun service
sudo systemctl enable WiFiDirectAutorun.service
sudo systemctl start WifiDirectAutorun.service
