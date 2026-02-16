import os
import json
import logging
import paho.mqtt.client as mqtt

# Correct host for Docker → Windows communication
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
# MQTT_HOST = "192.168.1.5"   # Your Windows machine IP address
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "ayush123")

logger = logging.getLogger("mqtt_client")

def publish_message(topic: str, message: str, qos: int = 0, retain: bool = False):
    """Publish an MQTT message from Django"""

    client = mqtt.Client()

    # Set credentials
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    extra = {
        "mqtt_topic": topic,
        "mqtt_event": "publish",
        "mqtt_qos": qos,
        "mqtt_retain": retain,
    }

    try:
        payload = json.loads(message)
        if isinstance(payload, dict):
            if payload.get("blog_id") is not None:
                extra["blog_id"] = payload.get("blog_id")
            if payload.get("status") is not None:
                extra["status"] = payload.get("status")
    except Exception:
        pass

    try:
        # Connect to Windows MQTT Explorer
        client.connect(MQTT_HOST, MQTT_PORT, 60)

        # Publish
        client.publish(topic, payload=message, qos=qos, retain=retain)
        logger.info("MQTT published", extra=extra)
    except Exception:
        logger.exception("MQTT publish failed", extra=extra)
        raise
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
