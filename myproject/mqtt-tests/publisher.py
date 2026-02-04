import paho.mqtt.client as mqtt

# MQTT Credentials
MQTT_HOST = "localhost"   # Because you're running from Windows to Docker
MQTT_PORT = 1883
MQTT_USERNAME = "admin"
MQTT_PASSWORD = "ayush123"

# Create client
client = mqtt.Client()

# Set username/password for authentication
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Connect to MQTT broker
try:
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    print("🟢 Connected to MQTT broker")
except Exception as e:
    print("❌ Connection failed:", str(e))
    exit()

# Publish a test message
topic = "blog/new"
message = "Hello from MQTT publisher!"

client.publish(topic, message)
print(f"📤 Sent → Topic: {topic} | Message: {message}")

client.disconnect()
print("🔌 Disconnected")
