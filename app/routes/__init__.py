from flask import Flask

from app.routes.browse import browse_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(browse_bp)
