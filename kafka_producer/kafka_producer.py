from kafka import KafkaProducer
import json
import time
import os

# Fix the path calculation - only go up 2 levels from the script location
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
data_path = os.path.join(project_root, 'data', 'test_data.json')

print(f"Looking for data file at: {data_path}")  # Debug path

broker = os.getenv("KAFKA_BROKER")
producer = KafkaProducer(
    bootstrap_servers=broker,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    request_timeout_ms=10000,
    api_version=(0, 10, 1)
)

TOPIC = os.getenv("KAFKA_TOPIC")

try:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")

    with open(data_path, 'r') as f:
        for line in f:
            try:
                review = json.loads(line)
                producer.send(TOPIC, value=review)
                print(f"✅ Review sent: {review['reviewerID']}")
                time.sleep(1)  # Simulate real-time flow
            except Exception as e:
                print(f"❌ Error: {e}")

    producer.flush()
    print("✅ All messages sent successfully")
except Exception as e:
    print(f"❌ Connection error: {e}")
finally:
    producer.close()
