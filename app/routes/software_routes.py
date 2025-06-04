import json
import requests
from flask import current_app
import re
from bs4 import BeautifulSoup
from flask import render_template, jsonify, flash, redirect, url_for, request
from peewee import DoesNotExist
from app.models.aiSoftwareInfo import AISoftwareInfo
from app.models.software import Software
from app.logic.table import get_table, organize_table, combine_columns
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

    print("Going to front", df.columns)
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
    software_id = Software.get(Software.software_name == software_name).id
    try:
        containers = get_containers_for_software(software_id)
        container_json = json.dumps(containers)
        return container_json
    except Exception as e:
        print(e)
        flash(f"Unable to retireve containers for {software_name}", "danger")
        return redirect(url_for("software_search"))

@software_bp.route("/software_info/<path:software_name>")
def software_info(software_name):

    try:
        table_object = get_table()
        table_info = initialize_table_info()
        df = organize_table(table_object, table_info)
        df = combine_columns(df, [
            ('Description', 'AI Description'),
        ])
        df = combine_columns(df, [
            ('AI Research Discipline', 'AI Research Field')
        ], combine_data= True)
        table = df.loc[df["Software"] == software_name]
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
        url = data.get('url')
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Set headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = None

        # get titles
        if not title:
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text()

        # clean up title
        if title:
            title = re.sub(r'\s+', ' ', title.strip())
        else:
            title = ''

        return jsonify({
            'title': title,
            'url': url
        })

    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Failed ot fetch URL: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'An error occured: {str(e)}'}), 500