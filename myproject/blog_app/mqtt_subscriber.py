import os
import sys
import json
import django
import paho.mqtt.client as mqtt
from django.utils import timezone

# Add project root to PYTHONPATH
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Load Django settings for Docker environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")
django.setup()

from blog_app.models import Blog
from blog_app.mqtt_publisher import mqtt_publish


# MQTT SETTINGS — Docker Mosquitto
MQTT_HOST = "mqtt"     # hostname of mosquitto service inside docker
MQTT_PORT = 1883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "ayush123"


# MQTT MESSAGE HANDLER
def on_message(client, userdata, msg):
    print(f"\n📥 MQTT RECEIVED → Topic: {msg.topic} | Payload: {msg.payload.decode()}")

    try:
        data = json.loads(msg.payload.decode())
    except Exception:
        print("❌ Invalid JSON format")
        return

    # FORCE PUBLISH LOGIC
    if msg.topic == "blog/force_publish":
        blog_id = data.get("blog_id")
        status = data.get("status")

        if not blog_id or status != "published":
            print("❌ Wrong or missing status/blog_id")
            return

        try:
            blog = Blog.objects.get(id=blog_id)
        except Blog.DoesNotExist:
            print(f"❌ Blog {blog_id} not found")
            return

        blog.is_published = True
        blog.published_at = timezone.now()
        blog.scheduled_publish_at = None
        blog.save()

        print(f"✅ FORCE PUBLISHED — Blog {blog_id}")

        mqtt_publish("blog/published", {
            "blog_id": blog.id,
            "status": "force_published",
            "published_at": str(blog.published_at)
        })


# START SUBSCRIBER
client = mqtt.Client()
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.on_message = on_message

client.connect(MQTT_HOST, MQTT_PORT)
client.subscribe("blog/force_publish")

print("\n🔵 Docker MQTT Subscriber Running...")
print("👂 Listening for topic: blog/force_publish ...\n")

client.loop_forever()
