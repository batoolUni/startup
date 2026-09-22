import os
import time
import threading
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from twilio.rest import Client

# Initialize Flask API Server with Cross-Origin Resource Sharing (CORS) enabled globally
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# ==============================================================================
# 1. SYSTEM PARAMETERS & CREDENTIALS CONFIGURATION
# ==============================================================================
TWILIO_ACCOUNT_SID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN = 'your_auth_token_goes_here'
TWILIO_PHONE_NUM = '+1855XXXXXXX'
CONSUMER_PHONE_NUM = '+1XXXXXXXXXX'

is_trojan_active = False
current_tick = 0

shared_telemetry = {
    "is_secure": True,
    "em_voltage": 1.65,
    "current_ma": 42.0,
    "power_mw": 210.0
}

anomaly_detector = IsolationForest(contamination=0.01, random_state=42)

# ==============================================================================
# 2. DATA EXTRACTION ENGINE (ScienceDB File Parser)
# ==============================================================================


def load_and_format_sciencedb_data(file_path):
    """Reads raw ScienceDB metric logs and formats them for the model."""
    try:
        df = pd.read_csv(file_path, sep=None, engine='python').dropna()
        feature_candidates = [col for col in df.columns if any(kw in col.lower(
        ) for kw in ['power', 'current', 'delay', 'transition', 'activity', 'em_v'])]

        if not feature_candidates:
            numerical_df = df.select_dtypes(include=[np.number])
            feature_columns = numerical_df.columns[:3].tolist()
        else:
            feature_columns = feature_candidates[:3]

        X_raw = df[feature_columns].values
        label_column = [col for col in df.columns if any(
            kw in col.lower() for kw in ['label', 'trojan', 'class', 'infected'])]

        if label_column:
            y_labels = df[label_column].apply(lambda x: 1 if str(x).strip().lower() in [
                                              '0', 'clean', 'benign', 'normal'] else -1).values
        else:
            y_labels = np.ones(X_raw.shape)

        scaler = StandardScaler()
        return scaler.fit_transform(X_raw), y_labels
    except Exception as e:
        print(f"[X] Failed to parse ScienceDB dataset file: {e}")
        return None, None

# ==============================================================================
# 3. VIRTUAL SENSOR SIMULATOR MODULE
# ==============================================================================


def sample_virtual_sensors():
    """Generates synthetic telemetry based on ScienceDB structural profiles."""
    global is_trojan_active
    if not is_trojan_active:
        em_voltage = np.random.normal(1.65, 0.015)
        current_ma = np.random.normal(42.0, 0.4)
    else:
        em_voltage = np.random.normal(2.45, 0.12)
        current_ma = np.random.normal(78.5, 4.2)

    power_mw = current_ma * 5.0  # Safe (~210mW) vs Attack (~392.5mW)
    return [em_voltage, current_ma, power_mw]

# ==============================================================================
# 4. CLOUD COMMUNICATION PIPELINE
# ==============================================================================


def dispatch_sms_threat_alert(em_metric, power_metric):
    """Dispatches a critical cellular SMS security warning message via Twilio."""
    print("[*] Connecting to Twilio Cloud Infrastructure...")
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        alert_body = (
            f"\n⚠️ SECURITY ALERT ⚠️\n"
            f"Your hardware watchdog has detected a potential Hardware Trojan anomaly!\n\n"
            f"Metric Violations:\n"
            f"- EM Signature Spike: {em_metric:.3f}V\n"
            f"- Current Power Draw: {power_metric:.2f}mW\n\n"
            f"Action Recommended: Isolate the target device from the network immediately."
        )
        message = client.messages.create(
            body=alert_body, from_=TWILIO_PHONE_NUM, to=CONSUMER_PHONE_NUM)
        print(
            f"[+] Alert message successfully dispatched. Message SID: {message.sid}")
        return True
    except Exception as error:
        print(f"[X] Cloud notification routing failed: {error}")
        return False

# ==============================================================================
# 5. ML INITIALIZATION & BACKGROUND SYSTEM RUNTIME
# ==============================================================================


def run_virtual_calibration(samples=100):
    print("[*] Learning virtual data 'clean' heartbeat baseline...")
    calibration_pool = []
    while len(calibration_pool) < samples:
        calibration_pool.append(sample_virtual_sensors())
        time.sleep(0.02)
    anomaly_detector.fit(np.array(calibration_pool))
    print("[+] Machine Learning local calibration matrix locked.")


def initialize_and_train_watchdog(dataset_file_path="sciencedb_profile.csv"):
    """Trains model using either ScienceDB database file or falls back to physical capture."""
    if os.path.exists(dataset_file_path):
        print(
            f"\n[+] ScienceDB Dataset discovered at target destination: {dataset_file_path}")
        X_features, y_labels = load_and_format_sciencedb_data(
            dataset_file_path)
        if X_features is not None:
            X_clean_training = X_features[y_labels.flatten() == 1]
            anomaly_detector.fit(X_clean_training)
            print(
                f"[SUCCESS] Guard Engine pre-trained via ScienceDB. Rows: {len(X_clean_training)}")
            return True
    print("\n[!] No dataset file found. Reverting to automated local calibration...")
    run_virtual_calibration()
    return False


def guardian_runtime_loop():
    global shared_telemetry, is_trojan_active, current_tick
    initialize_and_train_watchdog("sciencedb_profile.csv")
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
            if consecutive_hits >= 3:  # 3-strike frame temporal filter
                is_secure = False
                if consecutive_hits == 3:
                    dispatch_sms_threat_alert(
                        em_metric=metrics[0], power_metric=metrics[2])
        else:
            consecutive_hits = 0

        v_em = float(metrics[0])
        i_ma = float(metrics[1])
        p_mw = float(metrics[2])

        shared_telemetry = {
            "is_secure": is_secure,
            "em_voltage": v_em,
            "current_ma": i_ma,
            "power_mw": p_mw
        }

        if current_tick % 20 == 0:
            status = "SECURE" if is_secure else "⚠️ TROJAN DETECTED ⚠️"
            print(
                f"[Tick {current_tick}] Status: {status} | EM: {v_em:.2f}V | Power: {p_mw:.1f}mW")

        time.sleep(0.05)

# ==============================================================================
# 6. REST API NETWORK CONTROLLER ENDPOINTS
# ==============================================================================


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    return jsonify(shared_telemetry)


@app.route('/trigger', methods=['POST', 'OPTIONS'])
def trigger_attack():
    if request.method == 'OPTIONS':
        return '', 200

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
    monitor_thread = threading.Thread(
        target=guardian_runtime_loop, daemon=True)
    monitor_thread.start()

    # Run natively on local port 5000
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
