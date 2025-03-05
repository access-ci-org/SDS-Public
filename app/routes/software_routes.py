import json
from flask import current_app
from flask import render_template, jsonify, flash, redirect, url_for
from peewee import DoesNotExist
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.logic.table import get_table, organize_table
from app.logic.lastUpdated import get_last_updated
from app.logic.convertMarkdown import convert_markdown_to_html
from app.logic.containers import get_containers_for_software
from app.logic.table import initialize_table_info
from . import software_bp


# Main Route
@software_bp.route("/")
def software_search():
    table_object = get_table()
    table_info = initialize_table_info()
    df = organize_table(table_object, table_info)
    table = df.to_html(
        classes='table table-striped table-bordered" id = "softwareTable',
        index=False,
        border=1,
    ).replace("\\n", "<br>")
    last_updated = get_last_updated()
    return render_template(
        "software_search.html",
        table=table,
        column_names=table_info.column_names,
        last_updated=last_updated,
        use_ai_info=current_app.config["USE_AI_INFO"],
        use_curated_info=current_app.config["USE_CURATED_INFO"],
        use_api=current_app.config["USE_API"],
    )


# 'Example Use' Modal Route
@software_bp.route("/example_use/<path:software_name>")
def get_example_use(software_name):
    example_use = None
    try:
        software_id = Software.get(Software.software_name == software_name)
        software_ai_info = AISoftwareInfo.get(AISoftwareInfo.software_id == software_id)
        example_use = software_ai_info.ai_example_use
    except DoesNotExist as dne:
        print(dne)

    if example_use:
        example_use_html = convert_markdown_to_html(software_ai_info.ai_example_use)
        return jsonify({"use": example_use_html})

    error_text = "**Unable to find use case record**"
    return jsonify({"use": convert_markdown_to_html(error_text)})

@software_bp.route("/container/<path:software_name>")
def get_software_container(software_name):
    software_id = Software.get(Software.software_name == software_name).id
    try:
        containers = get_containers_for_software(software_id)
        container_json = json.dumps(containers)
        return container_json
    except Exception as e:
        print(e)
        flash(f"Unable to retireve containers for {software_name}", "danger")
        return redirect(url_for("software_search"))
