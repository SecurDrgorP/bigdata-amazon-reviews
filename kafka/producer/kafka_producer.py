from kafka import KafkaProducer
import json
import time
import os

# Fix the path calculation - only go up 2 levels from the script location
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # Remove one dirname call
data_path = os.path.join(project_root, 'data', 'reviews.json')

print(f"Looking for data file at: {data_path}")  # Debug path

# Connection to Kafka broker with proper configuration
producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    request_timeout_ms=10000,
    api_version=(0, 10, 1)
)

# Topic name
TOPIC = 'reviews'

try:
    # Verify the file exists before trying to open it
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")
        
    # Load and send data
    with open(data_path, 'r') as f:
        for line in f:
            try:
                review = json.loads(line)
                producer.send(TOPIC, value=review)
                print(f"✅ Avis envoyé : {review['reviewerID']}")
                time.sleep(1)  # Simulate real-time flow
            except Exception as e:
                print(f"❌ Erreur : {e}")
    
    producer.flush()
    print("✅ All messages sent successfully")
except Exception as e:
    print(f"❌ Connection error: {e}")
finally:
    producer.close()
