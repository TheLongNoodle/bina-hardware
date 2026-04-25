#!/bin/bash

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Running script at $DIR"

sudo wpa_supplicant -B -iwlan0 -Dnl80211 -c"$DIR"/wpa_supplicant.conf
sleep 1
sudo wpa_cli -iwlan0 p2p_group_add
sleep 1
sudo ifconfig p2p-wlan0-0 192.168.1.2
sleep 1
wpa_cli -ip2p-wlan0-0 wps_pbc
sleep 1
sudo wpa_cli -ip2p-wlan0-0 wps_pin any 12345678

