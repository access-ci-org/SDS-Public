from . import app
from flask import (
    render_template,
    jsonify,
    request
)
import json
from app.logic.table import TableInfo,get_display_table, add_char_at_commas
from app.logic.lastUpdated import get_last_updated
from app.logic.convertMarkdown import convert_markdown_to_html

table_info = TableInfo()

software_csv = "app/data/final.csv"
WEBSITE_TITLES = 'app/data/website_titles.json'

@app.context_processor
def inject_global_vars():
    return dict(
        primary_color=app.config["PRIMARY_COLOR"],
        secondary_color=app.config["SECONDARY_COLOR"],
        site_title=app.config["SITE_TITLE"],
    )

# Main Route
@app.route("/")
def software_search():
    df =  get_display_table()
    df['Versions'] = df['Versions'].apply(add_char_at_commas)

    df = df.filter(['Software',
                    'Installed on',
                    'AI Description',
                    'AI Tags',
                    'AI Research Discipline',
                    'AI Software Type',
                    ])
    df = df.rename(columns={"AI General Tags": "AI Tags"})
    df['Documentation, Uses, and more'] = 'Documentation, Uses, and more'
    table = df.to_html(
            classes='" id = "softwareTable',
            index=False,
            border=1,
            escape=False
        ).replace("\\n", "<br>")

    last_updated = get_last_updated()
    return render_template(
        "software_search.html",
        table=table,
        column_names=table_info.column_names,
        last_updated=last_updated
    )


# 'Example Use' Modal Route
@app.route("/example_use/<path:software_name>")
def get_example_use(software_name):
    example_use = ""
    try:
        with open(f"example_uses/{software_name}.txt", "r") as f:
            example_use = f.read()

    except FileNotFoundError as fnf:
        print(fnf)

    if example_use:
        example_use_html = convert_markdown_to_html(example_use)
        return jsonify({"use": example_use_html})

    error_text = "**Unable to find use case record**"
    return jsonify({"use": convert_markdown_to_html(error_text)}), 204

@app.route("/software_info/<path:software_name>")
def software_info(software_name):

    try:
        df = get_display_table()
        # df['Versions'] = df['Versions'].apply(add_char_at_commas)
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

@app.route("/get-external-site-title", methods=['POST'])
def get_external_site_title():
    try:
        data = request.get_json()
        url = data.get('url').strip()
        webiste_titles = {}
        with open(WEBSITE_TITLES, 'r') as wt:
            webiste_titles = json.load(wt)
        title = webiste_titles.get(url, "")
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
        return jsonify({'error': f'An error occured: {str(e)}'}), 500