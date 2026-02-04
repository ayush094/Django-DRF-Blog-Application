import paho.mqtt.client as mqtt

# MQTT Credentials
MQTT_HOST = "localhost"   # Your Windows machine to Docker container
MQTT_PORT = 1883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "ayush123"

# When a message is received
def on_message(client, userdata, msg):
    try:
        decoded_message = msg.payload.decode("utf-8")
    except:
        decoded_message = "<UNDECODABLE>"
    
    print(f"📥 Topic: {msg.topic} | Message: {decoded_message}")

# Create MQTT client
client = mqtt.Client()

# Set username/password
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Connect to MQTT broker
try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    print("🟢 Subscriber connected to MQTT broker")
except Exception as e:
    print("❌ Subscriber connection failed:", str(e))
    exit()

# Subscribe to ALL blog topics
client.subscribe("blog/#")   # blog/created , blog/new, blog/scheduled, blog/published

print("👂 Listening on topic: blog/# ...")

client.on_message = on_message

# Keep subscriber running forever
client.loop_forever()
