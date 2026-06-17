import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "storage"
    )
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB limit for chunked uploads

    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS = (
        os.environ.get("KAFKA_BOOTSTRAP_SERVERS") or "localhost:9092"
    )
    KAFKA_TOPIC = "video-analytics"

    # Database Settings
    DATABASE_URL = (
        os.environ.get("DATABASE_URL")
        or "postgresql://postgres:postgres@localhost:5432/infotact"
    )
