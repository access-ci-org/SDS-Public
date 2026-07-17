from flask import Blueprint

# Blueprints for each route catagory
auth_bp = Blueprint("auth", __name__)
software_bp = Blueprint("software", __name__)
container_bp = Blueprint("container", __name__)
settings_bp = Blueprint("settings", __name__)
analytics_bp = Blueprint("analytics", __name__)
api_bp = Blueprint("api", __name__, url_prefix="/api/v1")
edit_bp = Blueprint("edit", __name__)
banner_bp = Blueprint("banner", __name__)
test_bp = Blueprint("test", __name__)

from . import auth_routes
from . import software_routes
from . import container_routes
from . import settings_routes
from . import analytics_routes
from . import api_routes
from . import edit_routes
from . import banner_routes
from . import test_routes

def init_app(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(software_bp)
    app.register_blueprint(container_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(edit_bp)
    app.register_blueprint(banner_bp)
    app.register_blueprint(test_bp)
