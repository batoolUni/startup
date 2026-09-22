import time
import threading
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest

# Initialize Flask API Server with Cross-Origin Resource Sharing (CORS) enabled
app = Flask(__name__)
CORS(app)

# ==============================================================================
# 1. GLOBAL STATE & ATTACK SIMULATOR PARAMETERS
# ==============================================================================
is_trojan_active = False
current_tick = 0

# Baseline safe initialization defaults
shared_telemetry = {
    "is_secure": True,
    "em_voltage": 1.65,
    "current_ma": 42.0,
    "power_mw": 210.0
}

anomaly_detector = IsolationForest(contamination=0.01, random_state=42)

# ==============================================================================
# 2. VIRTUAL SENSOR GENERATOR (ScienceDB Structural Footprints)
# ==============================================================================


def sample_virtual_sensors():
    """Generates synthetic telemetry based on ScienceDB structural profiles."""
    global is_trojan_active

    if not is_trojan_active:
        # Standard benign electrical heartbeat (Safe state)
        em_voltage = np.random.normal(1.65, 0.015)
        current_ma = np.random.normal(42.0, 0.4)
    else:
        # Hardware Trojan triggered parameter spikes (Active attack state)
        em_voltage = np.random.normal(2.45, 0.12)
        current_ma = np.random.normal(78.5, 4.2)  # Generates ~78.5mA draw

    # Derived total electrical power matrix calculation (P = I * V) using 5.0V rail
    power_mw = current_ma * 5.0  # Safe (~210mW) vs Attack (~392.5mW)
    return [em_voltage, current_ma, power_mw]

# ==============================================================================
# 3. BACKGROUND MACHINE LEARNING TIMELINE ENGINE
# ==============================================================================


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
            if consecutive_hits >= 3:  # 3-strike frame temporal filter
                is_secure = False
        else:
            consecutive_hits = 0

        # FIXED: Assigned explicit array indexing mapping definitions to clear scaling errors
        v_em = float(metrics[0])
        i_ma = float(metrics[1])
        p_mw = float(metrics[2])

        shared_telemetry = {
            "is_secure": is_secure,
            "em_voltage": v_em,
            "current_ma": i_ma,
            "power_mw": p_mw  # Will now scale correctly to 380+ mW during attacks!
        }

        # Output real-time execution parameters directly to your terminal window
        if current_tick % 20 == 0:
            status = "SECURE" if is_secure else "⚠️ TROJAN DETECTED ⚠️"
            print(
                f"[Tick {current_tick}] Status: {status} | EM: {v_em:.2f}V | Current: {i_ma:.1f}mA | Power: {p_mw:.1f}mW")

        time.sleep(0.05)

# ==============================================================================
# 4. REST NETWORK API CONFIGURATION ROUTES
# ==============================================================================


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    """Provides real-time parsed data packets to the Flutter app interface."""
    return jsonify(shared_telemetry)


@app.route('/trigger', methods=['POST'])
def trigger_attack():
    """Acts as the virtual trigger system payload channel."""
    global is_trojan_active
    data = request.get_json() or {}
    command = data.get("command", "")

    if command == "0xAA":
        is_trojan_active = True
        print("\n[🚨 ALERT] RECEIVED ATTACK COMMAND VIA API: 0xAA. TROJAN TRIGGERED!")
        return jsonify({"status": "Trojan Activated Successfully"}), 200
    elif command == "RESET":
        is_trojan_active = False
        print("\n[🔄 RESET] RECEIVED RECOVERY COMMAND VIA API. BASELINE RESTORED.")
        return jsonify({"status": "System Disarmed"}), 200
    return jsonify({"error": "Invalid Payload Command"}), 400


if __name__ == "__main__":
    from pyngrok import ngrok

    # Start the hardware background monitoring loop thread
    monitor_thread = threading.Thread(
        target=guardian_runtime_loop, daemon=True)
    monitor_thread.start()

    # Open a public HTTP tunnel routing to local port 5000 to bypass firewalls
    public_url = ngrok.connect(5000).public_url
    print(f"\n🚀 NGROK TUNNEL DISTRIBUTED SUCCESSFULLY!")
    print(f"🔗 COPY THIS PUBLIC SECURE URL FOR FLUTTER: {public_url}\n")

    # Run the server node
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
