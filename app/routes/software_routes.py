import json
from flask import current_app
from flask import render_template, jsonify, flash, redirect, url_for, request
from peewee import DoesNotExist
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.logic.table import get_table, organize_table, combine_columns
from app.logic.lastUpdated import get_last_updated
from app.logic.convertMarkdown import convert_markdown_to_html
from app.logic.containers import get_containers_for_software
from app.logic.table import initialize_table_info
from app.paths import state_dir
from . import software_bp


def website_titles_path():
    return state_dir() / "websites" / "website_titles.json"


# Main Route
@software_bp.route("/")
def software_search():
    table_object = get_table()
    if not table_object:
        return render_template(
            "software_search.html",
            table="No data available to software create table. See https://github.com/access-ci-org/SDS-Public/blob/stand-alone/SDS_SETUP.md#data-preparation for instructions",
            column_names='{}',
            last_updated="",
            use_ai_info="False",
            use_curated_info="False",
            use_api="False",
        )
    table_info = initialize_table_info()
    df = organize_table(table_object, table_info)
    df = combine_columns(df, [
        ('Description', 'AI Description'),
    ])
    df = combine_columns(df, [
        ('AI Research Discipline', 'AI Research Field')
    ], combine_data= True)
    df = df.filter(['Software',
                    'Resource',
                    'Containers',
                    'Description',
                    'AI Tags',
                    'AI Research Discipline',
                    'AI Software Type'
                    ])
    df['Documentation, Uses, and more'] = 'Documentation, Uses, and more'

    table = df.to_html(
        classes='table table-striped" id = "softwareTable',
        index=False,
        border=1,
    ).replace('\\n', '<br>')
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

    if 'AI Example Use' in current_app.config['HIDE_DATA']:
        return jsonify({"error": "Example use is hidden by admin"}), 204
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
    return jsonify({"use": convert_markdown_to_html(error_text)}), 204

@software_bp.route("/container/<path:software_name>")
def get_software_container(software_name):
    try:
        software = Software.get(Software.software_name == software_name)
    except DoesNotExist:
        return jsonify({"error": "Software not found"}), 404
    try:
        containers = get_containers_for_software(software.id)
        container_json = json.dumps(containers)
        return container_json
    except Exception as e:
        print(e)
        flash(f"Unable to retrieve containers for {software_name}", "danger")
        return redirect(url_for("software.software_search"))

@software_bp.route("/software_info/<path:software_name>")
def software_info(software_name):

    try:
        table_object = get_table()
        table_info = initialize_table_info()
        df = organize_table(table_object, table_info)
        table = df.loc[df["Software"] == software_name]
        if table.empty:
            return "", 204
        table = combine_columns(table, [
            ('Description', 'AI Description'),
        ])
        table = combine_columns(table, [
            ('AI Research Discipline', 'AI Research Field')
        ], combine_data= True)
        table = table.to_json(
                index=False,
                orient='records'
                )
        return table
    except Exception as e:
        print(e)
        # raise e
        return jsonify({}), 204


@software_bp.route("/get-external-site-title", methods=['POST'])
def get_external_site_title():
    try:
        data = request.get_json()
        url = data.get('url').strip()
        website_titles = {}
        with open(website_titles_path(), 'r') as wt:
            website_titles = json.load(wt)
        title = website_titles.get(url, "")
        return jsonify({
            'title': title,
            'url': url
        })
    except FileNotFoundError as fe:
        # if file doesn't yet exist then just return the url for now
        print(fe)
        return jsonify({
            'title': url,
            'url' : url
        })
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500