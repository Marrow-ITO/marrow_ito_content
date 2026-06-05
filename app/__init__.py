import os

from flask import Flask
from flask_cors import CORS

from app.routes import register_blueprints


def create_app() -> Flask:
    app = Flask(__name__)
    # Required by Flask's flash() / session machinery. POC-only; rotate
    # for any real deployment via the FLASK_SECRET_KEY env var.
    app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-not-for-prod")
    # Cap uploads at 10 MB per request — covers reasonably large note pages.
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    # Open CORS only for the JSON API surface — keeps the browse routes
    # same-origin while letting the React frontend hit /api/* directly.
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    register_blueprints(app)
    return app
