from sklearn.ensemble import IsolationForest
import time
import threading
import numpy as np
from flask import Flask, jsonify, request

app = Flask(__name__)

# ==========================================
# 1. GLOBAL STATE & ATTACK SIMULATOR STATE
# ==========================================
# The virtual target state. True = Benign Cryptographic loops, False = Trojan Triggered
is_trojan_active = False
current_tick = 0

shared_telemetry = {
    "is_secure": True,
    "em_voltage": 1.65,
    "current_ma": 42.0,
    "power_mw": 210.0
}

anomaly_detector = IsolationForest(contamination=0.01, random_state=42)

# ==========================================
# 2. VIRTUAL SENSOR GENERATOR
# ==========================================


def sample_virtual_sensors():
    """Generates synthetic telemetry based on the ScienceDB profiles."""
    global is_trojan_active

    if not is_trojan_active:
        # Standard benign electrical heartbeat
        em_voltage = np.random.normal(1.65, 0.015)
        current_ma = np.random.normal(42.0, 0.4)
    else:
        # Malicious circuit activity spike
        em_voltage = np.random.normal(2.45, 0.12)
        current_ma = np.random.normal(78.5, 4.2)

    power_mw = current_ma * 5.0
    return [em_voltage, current_ma, power_mw]

# ==========================================
# 3. BACKGROUND ML ENGINE THREAD
# ==========================================


def run_virtual_calibration(samples=100):
    print("[*] Learning virtual data 'clean' heartbeat baseline...")
    calibration_pool = []
    while len(calibration_pool) < samples:
        calibration_pool.append(sample_virtual_sensors())
        time.sleep(0.02)
    anomaly_detector.fit(np.array(calibration_pool))
    print("[+] Machine Learning calibration matrix locked.")


def guardian_runtime_loop():
    global shared_telemetry, is_trojan_active, current_tick
    run_virtual_calibration()
    print("[!] Guardian active. Monitoring virtual data stream...")

    consecutive_hits = 0
    while True:
        current_tick += 1
        metrics = sample_virtual_sensors()

        # Unsupervised machine learning classification
        feature_vector = np.array(metrics).reshape(1, -1)
        prediction = anomaly_detector.predict(feature_vector)

        is_secure = True
        if prediction == -1:
            consecutive_hits += 1
            if consecutive_hits >= 3:
                is_secure = False
        else:
            consecutive_hits = 0

        shared_telemetry = {
            "is_secure": is_secure,
            "em_voltage": metrics[0],
            "current_ma": metrics[1],
            "power_mw": metrics[2]
        }

        # Print logs to the server terminal window
        if current_tick % 20 == 0:
            status = "SECURE" if is_secure else "⚠️ TROJAN DETECTED ⚠️"
            print(
                f"[Tick {current_tick}] Status: {status} | EM: {metrics[0]:.2f}V | Pwr: {metrics[2]:.1f}mW")

        time.sleep(0.05)

# ==========================================
# 4. REST NETWORK API ENDPOINTS
# ==========================================


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    """Provides data packets to the Flutter app."""
    response = jsonify(shared_telemetry)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


@app.route('/trigger', methods=['POST'])
def trigger_attack():
    """Acts as the virtual trigger. Replaces the laptop serial cable code."""
    global is_trojan_active
    data = request.get_json() or {}
    command = data.get("command", "")

    if command == "0xAA":
        is_trojan_active = True
        return jsonify({"status": "Trojan Activated Successfully"}), 200
    elif command == "RESET":
        is_trojan_active = False
        return jsonify({"status": "System Disarmed"}), 200
    return jsonify({"error": "Invalid Payload Command"}), 400


if __name__ == "__main__":
    # Start ML Engine thread
    monitor_thread = threading.Thread(
        target=guardian_runtime_loop, daemon=True)
    monitor_thread.start()
    # Deploy API Server
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
