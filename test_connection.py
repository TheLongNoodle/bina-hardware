#!/usr/bin/env python3
"""
WiFi Direct Connection Test Script

Run on the Raspberry Pi to test bidirectional communication with a connected phone.

Usage:
    python3 test_connection.py          # Start server mode (default)
    python3 test_connection.py server   # Start server mode
    python3 test_connection.py client <ip>  # Connect to server at <ip>
"""

import socket
import threading
import sys
import time
from datetime import datetime

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5000       # Port for test communication

def log(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}")

def handle_client(conn, addr):
    """Handle a connected client - echo messages back with acknowledgment"""
    log(f"Client connected from {addr}")
    conn.settimeout(60)

    try:
        # Send welcome message
        welcome = f"Connected to Bina-Camera at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        conn.send(welcome.encode())

        while True:
            try:
                data = conn.recv(1024)
                if not data:
                    break

                message = data.decode().strip()
                log(f"Received from {addr}: {message}")

                # Echo back with confirmation
                response = f"[Pi received]: {message}\n"
                conn.send(response.encode())
                log(f"Sent response to {addr}")

            except socket.timeout:
                # Send keepalive
                try:
                    conn.send(b"keepalive\n")
                except:
                    break

    except Exception as e:
        log(f"Error with client {addr}: {e}")
    finally:
        conn.close()
        log(f"Client {addr} disconnected")

def server_mode():
    """Run as TCP server - waits for phone to connect"""
    log("Starting test server...")
    log(f"Listening on {HOST}:{PORT}")
    log("Waiting for connections...")
    print()
    print("=" * 50)
    print("  To test from your phone, use a TCP client app")
    print(f"  Connect to: 192.168.1.2:{PORT}")
    print("  Or use netcat: nc 192.168.1.2 5000")
    print("=" * 50)
    print()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
    except KeyboardInterrupt:
        log("Server shutting down...")
    finally:
        server.close()

def client_mode(target_ip):
    """Run as TCP client - connect to another device"""
    log(f"Connecting to {target_ip}:{PORT}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((target_ip, PORT))
        log("Connected!")

        # Receive welcome message
        data = sock.recv(1024)
        print(f"Server: {data.decode().strip()}")

        print("\nType messages to send (Ctrl+C to quit):")

        # Start receive thread
        def receive():
            while True:
                try:
                    data = sock.recv(1024)
                    if data:
                        msg = data.decode().strip()
                        if msg != "keepalive":
                            print(f"\n{msg}")
                except:
                    break

        recv_thread = threading.Thread(target=receive, daemon=True)
        recv_thread.start()

        # Send loop
        while True:
            try:
                msg = input("> ")
                if msg:
                    sock.send((msg + "\n").encode())
            except KeyboardInterrupt:
                break

    except socket.timeout:
        log(f"Connection to {target_ip} timed out")
    except ConnectionRefusedError:
        log(f"Connection refused by {target_ip}")
    except Exception as e:
        log(f"Error: {e}")
    finally:
        sock.close()
        log("Disconnected")

def show_network_info():
    """Show current network interfaces and IPs"""
    import subprocess
    log("Current network interfaces:")
    try:
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'inet ' in line or ': ' in line and 'link' not in line:
                print(f"  {line.strip()}")
    except:
        pass

if __name__ == "__main__":
    print()
    print("=" * 50)
    print("  Bina Camera - WiFi Direct Connection Test")
    print("=" * 50)
    print()

    show_network_info()
    print()

    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "server":
            server_mode()
        elif mode == "client" and len(sys.argv) > 2:
            client_mode(sys.argv[2])
        else:
            print("Usage:")
            print("  python3 test_connection.py          # Server mode")
            print("  python3 test_connection.py server   # Server mode")
            print("  python3 test_connection.py client <ip>  # Client mode")
    else:
        server_mode()
