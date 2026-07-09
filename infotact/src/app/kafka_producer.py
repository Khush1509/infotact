import json
import logging
try:
    from confluent_kafka import Producer
except ImportError:
    class Producer:
        """Fallback dummy Producer when confluent_kafka is unavailable."""
        def __init__(self, conf=None):
            pass
        def produce(self, *args, **kwargs):
            pass
        def poll(self, timeout=0):
            pass
        def flush(self, timeout=10.0):
            pass
from .config import Config

class KafkaProducer:
    """Reusable Kafka producer for the Flask application.

    Initializes a persistent ``confluent_kafka.Producer`` using the bootstrap
    server configuration defined in ``Config``. Provides a ``send`` method that
    serialises a Python ``dict`` to JSON and publishes it to the ``video-analytics``
    topic (or a custom topic). Errors and delivery reports are logged.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        conf = {
            "bootstrap.servers": Config.KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "infotact-producer",
            "acks": "all",
        }
        self.producer = Producer(conf)
        self.logger.info("KafkaProducer initialized with %s", Config.KAFKA_BOOTSTRAP_SERVERS)

    def _delivery_report(self, err, msg):
        """Callback executed by ``confluent_kafka`` for each delivered message.

        Logs successes and failures.
        """
        if err is not None:
            self.logger.error("Message delivery failed: %s", err)
        else:
            self.logger.debug(
                "Message delivered to %s [partition %s] at offset %s",
                msg.topic(), msg.partition(), msg.offset()
            )

    def send(self, payload: dict, topic: str = Config.KAFKA_TOPIC) -> None:
        """Serialize *payload* to JSON and publish it to *topic*.

        Args:
            payload: The Python dictionary to send.
            topic:   Kafka topic – defaults to the application‑wide constant.
        """
        try:
            json_str = json.dumps(payload)
        except (TypeError, ValueError) as exc:
            self.logger.error("Failed to serialise payload %r: %s", payload, exc)
            return
        self.producer.produce(
            topic=topic,
            value=json_str.encode("utf-8"),
            callback=self._delivery_report,
        )
        self.producer.poll(0)

    def flush(self, timeout: float = 10.0) -> None:
        """Block until all queued messages are delivered or *timeout* expires."""
        self.producer.flush(timeout)
