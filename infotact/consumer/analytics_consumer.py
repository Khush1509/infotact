import json
import logging
import sys
import time
from confluent_kafka import Consumer, KafkaException, KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Kafka configuration
KAFKA_BROKERS = "localhost:9092"
TOPIC = "video-analytics"
GROUP_ID = "analytics-group"

consumer_conf = {
    "bootstrap.servers": KAFKA_BROKERS,
    "group.id": GROUP_ID,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
}

def create_consumer():
    """Instantiate and return a Kafka Consumer, subscribing to the topic."""
    try:
        consumer = Consumer(consumer_conf)
        consumer.subscribe([TOPIC])
        logging.info("Consumer created – subscribed to %s (group: %s)", TOPIC, GROUP_ID)
        return consumer
    except KafkaException as e:
        logging.error("Failed to create consumer: %s", e)
        raise

def process_message(msg):
    """Handle a single Kafka message.

    Expects the message payload to be JSON-encoded. Logs the event details.
    """
    try:
        payload_bytes = msg.value()
        payload_str = payload_bytes.decode("utf-8")
        data = json.loads(payload_str)
        logging.info("Received event %s for video %s at %s", data.get("event"), data.get("video_id"), data.get("timestamp"))
    except json.JSONDecodeError as e:
        logging.error("Failed to parse JSON payload at offset %d: %s", msg.offset(), e)
    except Exception as e:
        logging.error("Error processing message at offset %d: %s", msg.offset(), e)

def consumer_loop():
    consumer = create_consumer()
    try:
        while True:
            try:
                msg = consumer.poll(timeout=2.0)
                if msg is None:
                    continue  # No message this interval
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logging.info(
                            "End of partition %s [%d] at offset %d",
                            msg.topic(),
                            msg.partition(),
                            msg.offset(),
                        )
                    else:
                        logging.error("Kafka error: %s", msg.error())
                else:
                    process_message(msg)
            except KafkaException as ke:
                logging.error("Kafka exception during poll: %s", ke)
                time.sleep(5)
                consumer.close()
                consumer = create_consumer()
            except Exception as e:
                logging.error("Unexpected error in poll loop: %s", e)
                time.sleep(5)
    finally:
        logging.info("Shutting down consumer")
        consumer.close()

if __name__ == "__main__":
    logging.info("Starting analytics consumer daemon – polling topic '%s'", TOPIC)
    consumer_loop()
