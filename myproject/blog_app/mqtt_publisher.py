import os                # ← THIS WAS MISSING
import json
import paho.mqtt.client as mqtt

# MQTT host options:
# - host.docker.internal (preferred for Docker → Windows)
# - OR your Windows IP (example: 192.168.1.5)
# - OR override with environment variable

MQTT_HOST = os.getenv("MQTT_HOST", "host.docker.internal")
MQTT_PORT = 1883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "ayush123"


def mqtt_publish(topic, payload):
    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

        print(f"🔌 Connecting to MQTT at {MQTT_HOST}:{MQTT_PORT} ...")

        client.connect(MQTT_HOST, MQTT_PORT, 60)

        client.publish(topic, json.dumps(payload))
        client.disconnect()

        print(f"📤 MQTT SENT → {topic} | {payload}")

    except Exception as e:
        print("❌ MQTT publish error:", e)
