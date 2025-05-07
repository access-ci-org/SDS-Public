from flask import Flask
import yaml

app = Flask(__name__)

try:
    with open("config.yaml", "r") as c:
        config = yaml.safe_load(c)
    api_conf = config["api"]
    styles_conf = config.get("styles", {})
except FileNotFoundError as e:
    print(f"Unable to find config file config.yaml: {e}")
    exit(1)
except KeyError as ke:
    print(f"Required config keys not found. {ke}")
    exit(1)
except Exception as e:
    print(f"Error while trying to read config file: {e}")
    exit(1)

# api config
API_KEY = api_conf.get("api_key")

# styles config
PRIMARY_COLOR = styles_conf.get("primary_color", "#1b365d")
SECONDARY_COLOR = styles_conf.get("secondary_color", "#324a6d")
SITE_TITLE = styles_conf.get("site_title", "SDS")

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
    PRIMARY_COLOR=PRIMARY_COLOR,
    SECONDARY_COLOR=SECONDARY_COLOR,
    SITE_TITLE=SITE_TITLE,
)

from app import routes