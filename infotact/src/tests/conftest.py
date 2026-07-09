import pytest
import sys
import os

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402
from app.config import Config  # noqa: E402


class TestConfig(Config):
    TESTING = True
    UPLOAD_FOLDER = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "test_storage"
    )
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/infotact_test"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    # Clean up test storage if created
    if os.path.exists(TestConfig.UPLOAD_FOLDER):
        import shutil

        shutil.rmtree(TestConfig.UPLOAD_FOLDER)


@pytest.fixture
def client(app):
    return app.test_client()
