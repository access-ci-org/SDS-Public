import secrets
import sys
from pathlib import Path
from flask import Flask, send_file
from flask_login import LoginManager
import yaml
from peewee import DoesNotExist
from app.models.users import Users
from app.logic.table import TableInfo, initialize_table_info

app = Flask(__name__)
app.secret_key = secrets.token_hex()

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    try:
        return Users.get_by_id(int(user_id))
    except DoesNotExist:
        return None


try:
    with open("config.yaml", "r", encoding="utf-8") as c:
        config = yaml.safe_load(c)
    api_conf = config["api"]
    styles_conf = config.get("styles", {})
    gneneral_conf = config.get("general", {})
except FileNotFoundError as e:
    print(f"Unable to find config file config.yaml: {e}")
    sys.exit(1)
except KeyError as ke:
    print(f"Required config keys not found. {ke}")
    sys.exit(1)
except Exception as e:
    print(f"Error while trying to read config file: {e}")
    sys.exit(1)

# api config
API_KEY = api_conf.get("api_key")
USE_API = api_conf.get("use_api", False)
USE_CURATED_INFO = api_conf.get("use_curated_info", False)
USE_AI_INFO = api_conf.get("use_ai_info", False)

# styles config
PRIMARY_COLOR = styles_conf.get("primary_color", "#1b365d")
SECONDARY_COLOR = styles_conf.get("secondary_color", "#324a6d")
SITE_TITLE = styles_conf.get("site_title", "SDS")
LOGO = styles_conf.get("logo", "")

# default config
DEFAULT_PASS = Users.hash_password(gneneral_conf.get("password"))
DEFAULT_USER = gneneral_conf.get("user_name")

if not USE_AI_INFO and not USE_CURATED_INFO and USE_API:
    print("Not using API information")
    USE_API = False

DROP_COLUMNS = []

API_AI_COLUMNS = [
    "ai_description",
    "ai_software_type",
    "ai_software_class",
    "ai_research_field",
    "ai_research_area",
    "ai_research_discipline",
    "ai_core_features",
    "ai_general_tags",
    "ai_example_use",
]

API_CURATED_COLUMNS = [
    "software_web_page",
    "software_documentation",
    "software_use_link",
]
app.config.update(
    API_KEY=API_KEY,
    USE_API=USE_API,
    USE_CURATED_INFO=USE_CURATED_INFO,
    USE_AI_INFO=USE_AI_INFO,
    DROP_COLUMNS=DROP_COLUMNS,
    API_AI_COLUMNS=API_AI_COLUMNS,
    API_CURATED_COLUMNS=API_CURATED_COLUMNS,
    PRIMARY_COLOR=PRIMARY_COLOR,
    SECONDARY_COLOR=SECONDARY_COLOR,
    SITE_TITLE=SITE_TITLE,
    LOGO=LOGO,
    DEFAULT_PASS=DEFAULT_PASS,
    DEFAULT_USER=DEFAULT_USER,
)


# Global template varialbes (used for by html files)
@app.context_processor
def inject_global_vars():
    return {
        "primary_color": app.config["PRIMARY_COLOR"],
        "secondary_color": app.config["SECONDARY_COLOR"],
        "site_title": app.config["SITE_TITLE"],
        "logo": app.config["LOGO"],
    }


# Utility route (image for navbar)
@app.route("/image_file")
def image_file():
    logo_path = Path(app.config["LOGO"]).resolve()
    return send_file(logo_path, as_attachment=True)


from app.routes import init_app

init_app(app)

with app.app_context():
    initialize_table_info()
