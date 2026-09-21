import os
import time
import threading
import board
import busio
import numpy as np
import pandas as pd
from flask import Flask, jsonify
from gpiozero import Buzzer
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ina219 import INA219
import adafruit_ssd1306
from PIL import Image, ImageDraw, ImageFont
from twilio.rest import Client

# Initialize Flask API Server
app = Flask(__name__)

# ==========================================
# 1. APPLICATION PARAMS & GLOBAL STATE
# ==========================================
TWILIO_ACCOUNT_SID = 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
TWILIO_AUTH_TOKEN = 'your_auth_token_goes_here'
TWILIO_PHONE_NUM = '+1855XXXXXXX'
CONSUMER_PHONE_NUM = '+1XXXXXXXXXX'

# Global shared dictionary to bridge the background ML loop with the network API
shared_telemetry = {
    "is_secure": True,
    "em_voltage": 1.65,
    "current_ma": 42.0,
    "power_mw": 210.0,
    "timestamp": time.time()
}

# ==========================================
# 2. PHYSICAL HARDWARE PIN INITIALIZATION
# ==========================================
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
em_channel = AnalogIn(ads, ADS.P0)
ina219 = INA219(i2c)
buzzer = Buzzer(17)

oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)
image = Image.new("1", (oled.width, oled.height))
draw = ImageDraw.Draw(image)
font = ImageFont.load_default()

anomaly_detector = IsolationForest(contamination=0.01, random_state=42)

# ==========================================
# 3. INTERFACE HELPER FUNCTIONS
# ==========================================


def update_display(status_text, sub_text=""):
    draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
    draw.text((0, 0), "SIDE-CHANNEL WATCHDOG", font=font, fill=255)
    draw.text((0, 20), f"STATUS: {status_text}", font=font, fill=255)
    draw.text((0, 45), sub_text, font=font, fill=255)
    oled.image(image)
    oled.show()


def sample_metrics():
    try:
        em_field_v = em_channel.voltage
        current_ma = ina219.current
        bus_voltage = ina219.bus_voltage
        power_mw = current_ma * bus_voltage
        return [em_field_v, current_ma, power_mw]
    except Exception:
        return None


def dispatch_sms_threat_alert(em_metric, power_metric):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        alert_body = (
            f"\n⚠️ ALERT ⚠️\nHardware Trojan detected!\n\n"
            f"Metrics:\n- EM Spike: {em_metric:.3f}V\n- Power Draw: {power_metric:.2f}mW"
        )
        client.messages.create(
            body=alert_body, from_=TWILIO_PHONE_NUM, to=CONSUMER_PHONE_NUM)
    except Exception as error:
        print(f"[X] Twilio failed: {error}")


def run_physical_calibration(duration=15):
    update_display("CALIBRATING...", "Keep target clean")
    calibration_pool = []
    timeout = time.time() + duration
    while time.time() < timeout:
        metrics = sample_metrics()
        if metrics:
            calibration_pool.append(metrics)
        time.sleep(0.02)
    anomaly_detector.fit(np.array(calibration_pool))

# ==========================================
# 4. BACKGROUND PROCESSOR LOOP
# ==========================================


def background_guardian_thread():
    """Continuously reads sensors and runs inference independently from network requests."""
    global shared_telemetry
    run_physical_calibration(duration=10)
    update_display("GUARDIAN ACTIVE", "Monitoring...")

    consecutive_anomalies = 0
    while True:
        metrics = sample_metrics()
        if not metrics:
            continue

        feature_vector = np.array(metrics).reshape(1, -1)
        prediction = anomaly_detector.predict(feature_vector)

        # Safe updating of the global state dictionary
        is_secure = True
        if prediction == -1:
            consecutive_anomalies += 1
            if consecutive_anomalies >= 3:
                is_secure = False
                update_display("TROJAN THREAT!!", f"EM: {metrics[0]:.2f}V")
                buzzer.on()
                dispatch_sms_threat_alert(metrics[0], metrics[2])
                time.sleep(1.0)
                buzzer.off()
                consecutive_anomalies = 0
        else:
            consecutive_anomalies = 0

        shared_telemetry = {
            "is_secure": is_secure,
            "em_voltage": metrics[0],
            "current_ma": metrics[1],
            "power_mw": metrics[2],
            "timestamp": time.time()
        }
        time.sleep(0.05)

# ==========================================
# 5. REST API ROUTING
# ==========================================


@app.route('/telemetry', methods=['GET'])
def get_telemetry():
    """API endpoint providing clean JSON data payloads to the Flutter mobile application."""
    # Allow cross-origin testing requests from web debuggers
    response = jsonify(shared_telemetry)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response


if __name__ == "__main__":
    # Start the hardware background monitoring loop thread
    hardware_thread = threading.Thread(
        target=background_guardian_thread, daemon=True)
    hardware_thread.start()

    # Start the network API Server (accessible to anything on your Wi-Fi network)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
