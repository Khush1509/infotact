"""analytics_consumer.py – Standalone Kafka consumer daemon.

Listens to the ``video-analytics`` topic, decodes JSON payloads, and
persists aggregated video metrics to PostgreSQL via ``consumer.db``.

Run directly:
    python infotact/consumer/analytics_consumer.py
"""

import json
import logging
import sys
import time

from confluent_kafka import Consumer, KafkaException, KafkaError

from consumer.db import aggregate_event, ensure_schema, get_connection

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Kafka configuration ────────────────────────────────────────────────────
KAFKA_BROKERS = "localhost:9092"
TOPIC = "video-analytics"
GROUP_ID = "analytics-group"

consumer_conf = {
    "bootstrap.servers": KAFKA_BROKERS,
    "group.id": GROUP_ID,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": True,
}


# ── Consumer helpers ───────────────────────────────────────────────────────

def create_consumer():
    """Instantiate and return a Kafka Consumer, subscribing to the topic."""
    try:
        consumer = Consumer(consumer_conf)
        consumer.subscribe([TOPIC])
        log.info("Consumer created – subscribed to %s (group: %s)", TOPIC, GROUP_ID)
        return consumer
    except KafkaException as exc:
        log.error("Failed to create consumer: %s", exc)
        raise


def process_message(msg, db_conn):
    """Decode a Kafka message and persist its analytics event to the database.

    Args:
        msg:     A confluent_kafka Message object.
        db_conn: An open psycopg2 database connection.
    """
    try:
        payload_str = msg.value().decode("utf-8")
        data = json.loads(payload_str)
        log.info(
            "Received event '%s' for video '%s' at %s",
            data.get("event"),
            data.get("video_id"),
            data.get("timestamp"),
        )
        aggregate_event(db_conn, data)
    except json.JSONDecodeError as exc:
        log.error("Failed to parse JSON payload at offset %d: %s", msg.offset(), exc)
    except Exception as exc:
        log.error("Error processing message at offset %d: %s", msg.offset(), exc)


def consumer_loop():
    """Main polling loop – reconnects to Kafka and DB on transient failures."""
    db_conn = get_connection()
    ensure_schema(db_conn)

    consumer = create_consumer()
    try:
        while True:
            try:
                msg = consumer.poll(timeout=2.0)
                if msg is None:
                    continue  # No message this interval – keep polling

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        log.info(
                            "End of partition %s [%d] at offset %d",
                            msg.topic(),
                            msg.partition(),
                            msg.offset(),
                        )
                    else:
                        log.error("Kafka error: %s", msg.error())
                else:
                    process_message(msg, db_conn)

            except KafkaException as exc:
                log.error("Kafka exception during poll: %s – reconnecting in 5s", exc)
                time.sleep(5)
                consumer.close()
                consumer = create_consumer()

            except psycopg2.OperationalError as exc:          # noqa: F821
                log.error("DB connection lost: %s – reconnecting in 5s", exc)
                time.sleep(5)
                try:
                    db_conn = get_connection()
                    ensure_schema(db_conn)
                except Exception as inner:
                    log.error("DB reconnect failed: %s", inner)

            except Exception as exc:
                log.error("Unexpected error in poll loop: %s", exc)
                time.sleep(5)

    finally:
        log.info("Shutting down consumer")
        consumer.close()
        db_conn.close()


if __name__ == "__main__":
    import psycopg2  # noqa: F401 – available at runtime via requirements.txt
    log.info("Starting analytics consumer daemon – polling topic '%s'", TOPIC)
    consumer_loop()
