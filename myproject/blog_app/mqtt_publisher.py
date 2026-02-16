import os
import json
import logging
import paho.mqtt.client as mqtt

# MQTT host options:
# - host.docker.internal (preferred for Docker to Windows)
# - OR your Windows IP (example: 192.168.1.5)
# - OR override with environment variable
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")

MQTT_PORT = 1883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "ayush123"

logger = logging.getLogger("mqtt_publisher")


def mqtt_publish(topic, payload):
    extra = {
        "mqtt_topic": topic,
        "mqtt_event": "publish",
    }
    if isinstance(payload, dict):
        if payload.get("blog_id") is not None:
            extra["blog_id"] = payload.get("blog_id")
        if payload.get("status") is not None:
            extra["status"] = payload.get("status")

    try:
        client = mqtt.Client()
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.connect(MQTT_HOST, MQTT_PORT, 60)

        client.publish(topic, json.dumps(payload))  
        client.disconnect()
        logger.info(
                "MQTT published",
                extra={
                    **extra,
                    "payload": payload
                    }
                )

    except Exception:
        logger.exception("MQTT publish error", extra=extra)
