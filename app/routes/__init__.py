from flask import Blueprint

# Blueprints for each route catagory
auth_bp = Blueprint("auth", __name__)
software_bp = Blueprint("software", __name__)
container_bp = Blueprint("container", __name__)
settings_bp = Blueprint("settings", __name__)

from . import auth_routes
from . import software_routes
from . import container_routes
from . import settings_routes


def init_app(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(software_bp)
    app.register_blueprint(container_bp)
    app.register_blueprint(settings_bp)
