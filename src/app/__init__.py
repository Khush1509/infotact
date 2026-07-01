from flask import Flask
from .config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Register blueprints or routes
    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    # Start background transcoding worker threads
    try:
        from worker import start_workers
    except ImportError:
        from src.worker import start_workers
    start_workers()

    return app
