import time
import threading
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest

app = Flask(__name__)
CORS(app)

is_trojan_active = False
current_tick = 0

shared_telemetry = {
    "is_secure": True,
    "em_voltage": 1.65,
    "current_ma": 42.0,
    "power_mw": 210.0
}

anomaly_detector = IsolationForest(contamination=0.01, random_state=42)


def sample_virtual_sensors():
    global is_trojan_active
    if not is_trojan_active:
        em_voltage = np.random.normal(1.65, 0.015)
        current_ma = np.random.normal(42.0, 0.4)
    else:
        em_voltage = np.random.normal(2.45, 0.12)
        current_ma = np.random.normal(78.5, 4.2)
    power_mw = current_ma * 5.0
    return [em_voltage, current_ma, power_mw]


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
            "em_voltage": float(metrics[0]),
            "current_ma": float(metrics[1]),
            "power_mw": float(metrics[2])
        }

        if current_tick % 20 == 0:
            status = "SECURE" if is_secure else "⚠️ TROJAN DETECTED ⚠️"
            print(
                f"[Tick {current_tick}] Status: {status} | EM: {metrics[0]:.2f}V | Pwr: {metrics[2]:.1f}mW")

        time.sleep(0.05)


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(shared_telemetry)


@app.route('/trigger', methods=['POST'])
def trigger_attack():
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
    monitor_thread = threading.Thread(
        target=guardian_runtime_loop, daemon=True)
    monitor_thread.start()

    public_url = ngrok.connect(5000).public_url
    print(f"\n🚀 NGROK TUNNEL DISTRIBUTED SUCCESSFULLY!")
    print(f"🔗 COPY THIS PUBLIC SECURE URL FOR FLUTTER: {public_url}\n")

    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
