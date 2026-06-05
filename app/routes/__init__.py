from flask import Flask

from app.routes.api import api_bp
from app.routes.browse import browse_bp
from app.routes.concept_ui import concept_ui_bp
from app.routes.crud import crud_bp
from app.routes.search import search_bp


def register_blueprints(app: Flask) -> None:
    app.register_blueprint(browse_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(crud_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(concept_ui_bp)
