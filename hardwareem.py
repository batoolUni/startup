import numpy as np
import pandas as pd
import time
import socket

# Configuration for local software loopback communication
HOST = '127.0.0.1'
PORT = 65432


def generate_virtual_telemetry(is_attack_active=False):
    """Simulates raw physical sensor outputs based on ScienceDB profiles."""
    if not is_attack_active:
        # Standard baseline running cryptographic math loops safely
        # Micro-volt EM ambient waves
        em_voltage = np.random.normal(1.65, 0.015)
        current_ma = np.random.normal(42.0, 0.4)         # Steady current draw
    else:
        # Trojan payload triggered! Parasitic capacitance spikes parameters
        # High frequency radio burst
        em_voltage = np.random.normal(2.35, 0.12)
        # Massive transistor switching load
        current_ma = np.random.normal(78.5, 4.2)

    power_mw = current_ma * 5.0  # Derived power metric
    return f"{em_voltage:.4f},{current_ma:.2f},{power_mw:.2f}"


def start_virtual_hardware_server():
    print("[*] Virtual Hardware Simulator Active. Waiting for Watchdog to connect...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    conn, addr = server.accept()
    print(f"[+] Watchdog connected from local pipeline node: {addr}")

    tick = 0
    try:
        while True:
            # Simulate a timeline: Trigger Trojan automatically after 100 ticks
            is_attacked = True if tick > 100 else False

            if tick == 101:
                print(
                    "\n[⚠️ SYSTEM CRITICAL] Hacker deployed trigger '0xAA'. Trojan Active!")

            payload = generate_virtual_telemetry(is_attack_active=is_attacked)
            conn.sendall(f"{payload}\n".encode('utf-8'))

            tick += 1
            time.sleep(0.05)  # Emulate a 20Hz sensor polling speed
    except ConnectionResetError:
        print("[*] Watchdog disconnected.")
    finally:
        conn.close()
        server.close()


if __name__ == "__main__":
    start_virtual_hardware_server()
