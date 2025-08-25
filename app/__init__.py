import secrets
import sys
from pathlib import Path
from flask import Flask, send_file
from flask_login import LoginManager
import yaml
from peewee import DoesNotExist
from app.models.users import Users
from app.logic.table import initialize_table_info

app = Flask(__name__)
app.secret_key = secrets.token_hex()

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


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
    general_conf = config.get("general", {})
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
USE_API = api_conf.get("use_api") or False
USE_CURATED_INFO = api_conf.get("use_curated_info") or False
USE_AI_INFO = api_conf.get("use_ai_info") or False

# styles config
PRIMARY_COLOR = styles_conf.get("primary_color") or "#1b365d"
SECONDARY_COLOR = styles_conf.get("secondary_color") or  "#324a6d"
SITE_TITLE = styles_conf.get("site_title") or "SDS"
LOGO = styles_conf.get("logo") or  "./logo.svg"

# general config
DEFAULT_USER = general_conf.get("user_name")
DEFAULT_PASS = Users.hash_password(general_conf.get("password"))
SHARE_SOFTWARE = general_conf.get("share_software") or "False"
SHOW_CONTAINER_PAGE = general_conf.get("show_container_page", "True")
HIDE_DATA = general_conf.get('hide_data',[])
IFRAME = general_conf.get("iframe",False)

if not USE_AI_INFO and not USE_CURATED_INFO and USE_API:
    print("Not using API information")
    USE_API = False


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
    HIDE_DATA=HIDE_DATA,
    API_AI_COLUMNS=API_AI_COLUMNS,
    API_CURATED_COLUMNS=API_CURATED_COLUMNS,
    PRIMARY_COLOR=PRIMARY_COLOR,
    SECONDARY_COLOR=SECONDARY_COLOR,
    SITE_TITLE=SITE_TITLE,
    LOGO=LOGO,
    DEFAULT_PASS=DEFAULT_PASS,
    DEFAULT_USER=DEFAULT_USER,
    SHARE_SOFTWARE=SHARE_SOFTWARE,
    SHOW_CONTAINER_PAGE=SHOW_CONTAINER_PAGE,
    IFRAME=IFRAME
)


# Global template varialbes (used for by html files)
@app.context_processor
def inject_global_vars():
    return {
        "primary_color": app.config["PRIMARY_COLOR"],
        "secondary_color": app.config["SECONDARY_COLOR"],
        "site_title": app.config["SITE_TITLE"],
        "logo": app.config["LOGO"],
        "show_container_page": app.config["SHOW_CONTAINER_PAGE"],
        "iframe": app.config["IFRAME"]
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
