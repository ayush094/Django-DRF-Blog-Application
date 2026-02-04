import os
import paho.mqtt.client as mqtt

# Correct host for Docker → Windows communication
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
# MQTT_HOST = "192.168.1.5"   # Your Windows machine IP address
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "ayush123")

def publish_message(topic: str, message: str, qos: int = 0, retain: bool = False):
    """Publish an MQTT message from Django"""

    client = mqtt.Client()

    # Set credentials
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Connect to Windows MQTT Explorer
    client.connect(MQTT_HOST, MQTT_PORT, 60)

    # Publish
    client.publish(topic, payload=message, qos=qos, retain=retain)

    client.disconnect()
