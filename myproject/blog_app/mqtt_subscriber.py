import os
import json
import logging
import django
import paho.mqtt.client as mqtt

from django.core.exceptions import ObjectDoesNotExist
from django.db import ProgrammingError, OperationalError

try:
    import logstash
except Exception:
    logstash = None


# ------------------------------------------------------------------
# DJANGO SETUP (MANDATORY FOR STANDALONE SCRIPTS)
# ------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from blog_app.models import Blog  # noqa: E402
from django.utils import timezone  # noqa: E402


# ------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------
logger = logging.getLogger("mqtt_subscriber")
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

LOGSTASH_HOST = os.getenv("LOGSTASH_HOST", "logstash")
LOGSTASH_PORT = int(os.getenv("LOGSTASH_PORT", 5044))

if logstash is not None:
    try:
        logstash_handler = logstash.TCPLogstashHandler(
            LOGSTASH_HOST, LOGSTASH_PORT, version=1
        )
        logger.addHandler(logstash_handler)
    except Exception:
        logger.exception("Logstash handler setup failed")


# ------------------------------------------------------------------
# MQTT CONFIG (FROM ENV - DOCKER SAFE)
# ------------------------------------------------------------------
MQTT_HOST = os.getenv("MQTT_HOST", "mqtt")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "admin")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "ayush123")

MQTT_TOPIC = "blog/#"


# ------------------------------------------------------------------
# MQTT CALLBACKS
# ------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(
            "MQTT connected successfully",
            extra={"mqtt_event": "connect"}
        )
        client.subscribe(MQTT_TOPIC)
        logger.info(
            "Subscribed to topic",
            extra={"mqtt_topic": MQTT_TOPIC, "mqtt_event": "subscribe"},
        )
    else:
        logger.error(
            "MQTT connection failed",
            extra={"mqtt_event": "connect", "mqtt_rc": rc},
        )


def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode()
        payload = json.loads(payload_str)
    except Exception:
        logger.warning(
            "Invalid JSON payload",
            extra={
                "mqtt_topic": msg.topic,
                "mqtt_event": "receive",
                "raw_payload": msg.payload.decode(errors="ignore"),
            },
        )
        return

    blog_id = payload.get("blog_id")
    status = payload.get("status")

    # 🔥 FULL STRUCTURED LOG
    logger.info(
        "MQTT message received",
        extra={
            "mqtt_topic": msg.topic,
            "mqtt_event": "receive",
            "blog_id": blog_id,
            "status": status,
            "payload": payload,
        },
    )

    try:
        blog = Blog.objects.get(id=blog_id)

        if status == "published":
            blog.is_published = True
            blog.published_at = timezone.now()
            blog.save(update_fields=["is_published", "published_at"])

            logger.info(
                "Blog published successfully",
                extra={
                    "mqtt_topic": msg.topic,
                    "blog_id": blog_id,
                    "status": status,
                },
            )

        elif status == "scheduled":
            blog.is_published = False
            blog.save(update_fields=["is_published"])

            logger.info(
                "Blog scheduled successfully",
                extra={
                    "mqtt_topic": msg.topic,
                    "blog_id": blog_id,
                    "status": status,
                },
            )

        else:
            logger.warning(
                "Invalid status received",
                extra={
                    "mqtt_topic": msg.topic,
                    "blog_id": blog_id,
                    "invalid_status": status,
                },
            )

    except Blog.DoesNotExist:
        logger.warning(
            "Blog not found",
            extra={
                "mqtt_topic": msg.topic,
                "blog_id": blog_id,
            },
        )

def on_disconnect(client, userdata, rc):
    logger.warning(
        "MQTT disconnected",
        extra={"mqtt_event": "disconnect", "mqtt_rc": rc},
    )


# ------------------------------------------------------------------
# MQTT CLIENT SETUP
# ------------------------------------------------------------------
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect


# ------------------------------------------------------------------
# START
# ------------------------------------------------------------------
logger.info("MQTT subscriber running", extra={"mqtt_event": "start"})
logger.info(
    "Listening for topic",
    extra={"mqtt_topic": MQTT_TOPIC, "mqtt_event": "listen"},
)

try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()
except Exception:
    logger.exception("MQTT subscriber crashed")
