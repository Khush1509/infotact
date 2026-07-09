#!/usr/bin/env python
"""Entry point to run the Infotact Flask application locally.
It creates the app using the factory defined in src/app/__init__.py and
starts the development server on port 5000.
Ensure you have a virtual environment activated and the required
packages installed (see requirements.txt).
"""

from src.app import create_app

app = create_app()

if __name__ == "__main__":
    # Enable debug mode for development; remove in production.
    app.run(host="127.0.0.1", port=5000, debug=True)
