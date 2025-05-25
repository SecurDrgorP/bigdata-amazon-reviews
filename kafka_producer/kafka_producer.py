from kafka import KafkaProducer
import json
import time
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Use the mounted data directory path in Docker container
data_path = '/app/data/test_data.json'

logger.info("🚀 Starting Kafka Producer for Amazon Reviews")
logger.info(f"📁 Looking for data file at: {data_path}")

broker = os.getenv("KAFKA_BROKER")
topic = os.getenv("KAFKA_TOPIC")

logger.info(f"🔗 Connecting to Kafka broker: {broker}")
logger.info(f"📨 Target topic: {topic}")

try:
    producer = KafkaProducer(
        bootstrap_servers=broker,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        request_timeout_ms=10000,
        api_version=(0, 10, 1)
    )
    logger.info("✅ Successfully connected to Kafka broker")
except Exception as e:
    logger.error(f"❌ Failed to connect to Kafka broker: {e}")
    exit(1)

try:
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")

    logger.info(f"📄 Data file found, starting to read reviews...")
    
    # Count total lines first for progress tracking
    with open(data_path, 'r') as f:
        total_reviews = sum(1 for _ in f)
    logger.info(f"📊 Total reviews to process: {total_reviews}")
    
    # Process reviews
    sent_count = 0
    error_count = 0
    start_time = datetime.now()
    
    with open(data_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                review = json.loads(line)
                
                # Send to Kafka
                future = producer.send(topic, value=review)
                
                # Get message metadata
                record_metadata = future.get(timeout=10)
                
                sent_count += 1
                
                # Log progress every 10 reviews or for first 5
                if sent_count <= 5 or sent_count % 10 == 0:
                    logger.info(f"✅ [{sent_count}/{total_reviews}] Review sent successfully")
                    logger.info(f"   📍 Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")
                    logger.info(f"   👤 ReviewerID: {review.get('reviewerID', 'N/A')}")
                    logger.info(f"   📦 Product ASIN: {review.get('asin', 'N/A')}")
                    logger.info(f"   ⭐ Rating: {review.get('overall', 'N/A')}")
                    logger.info(f"   📝 Review preview: {review.get('reviewText', '')[:100]}...")
                
                # Calculate and log streaming statistics
                if sent_count % 50 == 0:
                    elapsed_time = (datetime.now() - start_time).total_seconds()
                    rate = sent_count / elapsed_time if elapsed_time > 0 else 0
                    remaining = total_reviews - sent_count
                    eta_seconds = remaining / rate if rate > 0 else 0
                    
                    logger.info(f"📈 STREAMING STATS:")
                    logger.info(f"   📊 Processed: {sent_count}/{total_reviews} ({(sent_count/total_reviews)*100:.1f}%)")
                    logger.info(f"   ⚡ Rate: {rate:.2f} messages/second")
                    logger.info(f"   ⏱️  Elapsed: {elapsed_time:.1f}s")
                    logger.info(f"   🕐 ETA: {eta_seconds:.1f}s remaining")
                    logger.info(f"   ❌ Errors: {error_count}")
                
                time.sleep(1)  # Simulate real-time flow
                
            except json.JSONDecodeError as e:
                error_count += 1
                logger.error(f"❌ JSON decode error on line {line_num}: {e}")
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Error processing line {line_num}: {e}")

    # Final statistics
    total_time = (datetime.now() - start_time).total_seconds()
    final_rate = sent_count / total_time if total_time > 0 else 0
    
    producer.flush()
    logger.info("🔄 Flushing remaining messages...")
    
    logger.info("🎉 STREAMING COMPLETED!")
    logger.info(f"📊 FINAL STATISTICS:")
    logger.info(f"   ✅ Successfully sent: {sent_count}/{total_reviews}")
    logger.info(f"   ❌ Errors encountered: {error_count}")
    logger.info(f"   ⏱️  Total time: {total_time:.2f} seconds")
    logger.info(f"   ⚡ Average rate: {final_rate:.2f} messages/second")
    logger.info(f"   📈 Success rate: {(sent_count/(sent_count+error_count))*100:.1f}%")
    
except Exception as e:
    logger.error(f"❌ Critical error during streaming: {e}")
finally:
    logger.info("🔐 Closing Kafka producer connection...")
    producer.close()
    logger.info("👋 Kafka producer shutdown complete")
