from . import app
from flask import (
    render_template,
    jsonify,
    request
)

from peewee import DoesNotExist
from app.logic.reports import sanitize_and_process_reports, save_user_report
from app.logic.table import TableInfo, add_line_breaks_at_commas
from app.logic.lastUpdated import get_last_updated
from app.logic.convertMarkdown import convert_markdown_to_html
import pandas as pd

table_info = TableInfo()


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
    df = pd.read_csv("app/data/final.csv", keep_default_na=False)
    df.rename(columns=table_info.column_names, inplace=True)

    df['Versions'] = df['Versions'].apply(add_line_breaks_at_commas)

    table = df.to_html(
            classes='table table-striped table-bordered" id = "softwareTable',
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
    return jsonify({"use": convert_markdown_to_html(error_text)})


# 'Report Issue' Button Route
@app.route("/report-issue", methods=["POST"])
def report_issue():
    user_report = request.get_json()
    if "elementText" in user_report:
        issue_report = sanitize_and_process_reports(user_report, report_type="report")
        report_saved = save_user_report(issue_report)

        if report_saved:
            return jsonify({"success": "Issue reported successfully"})

        return ({"error": "Unable to save issue report"}), 500

    return jsonify({"error": "Missing key elementText"}), 400


## Flask Route Definition for User Feedback Button
## process_feedback() is called anytime a POST is sent to /user-feedback
@app.route("/user-feedback", methods=["POST"])
def process_feedback():
    # Grab Ajax Request
    user_feedback = request.get_json()

    if "userMessage" in user_feedback:
        feedback_report = sanitize_and_process_reports(
            user_feedback, report_type="feedback"
        )
        feedback_saved = save_user_report(feedback_report)

        if feedback_saved:
            return jsonify({"success": "Feedback processed successfully"})

        return ({"error": "Unable to save user feedback"}), 500

    return jsonify({"error": "Missing key userMessage."}), 400
