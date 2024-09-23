from flask import Flask, render_template, jsonify, send_file, request
from dotenv import load_dotenv
from app.logic.reports.reports import sanitize_and_process_reports, save_user_report
from app.logic.reports.feedback import sanitize_and_process_feedback, save_user_feedback
from app.logic.example_use import find_example_use
from app.logic.software_table.softwareTable import create_software_table
from app.logic.lastUpdated import get_last_updated
import re

import pandas as pd
# import logging

app = Flask(__name__)

# Main Route
@app.route("/")
def software_search():
    try:
        df = pd.read_csv("./data/CSV/softwareTable.csv", keep_default_na=False)
    except FileNotFoundError as e:
        df = create_software_table()
        print(e)
    
    table = df.to_html(classes='table-striped" id = "softwareTable',index=False,border=1).replace('\\n', '<br>')

    # column map with column names as keys and index as values. special characters are stripped from column names so "✨General Tags" becomes "GeneralTags" 
    column_map = {re.sub(r'[^a-zA-Z0-9]', '', col): df.columns.get_loc(col) for col in df.columns}

    last_updated = get_last_updated()

    return render_template("software_search.html",
                           table=table,
                           column_map=column_map,
                           last_updated=last_updated)

# 'Example Use' Modal Route
@app.route("/example_use/<path:software_name>")
def get_example_use(software_name):
    
    example_use = find_example_use(software_name)
    if example_use:
        return (jsonify({"use": example_use}))
    
    return (jsonify({"use": '**Unable to find use case record**'}))

# 'Report Issue' Button Route
@app.route("/report-issue", methods=['POST'])
def report_issue():
    user_report = request.get_json()

    if 'reportDetails' in user_report:
        issue_report = sanitize_and_process_reports(user_report)
        report_saved = save_user_report(issue_report)

        if report_saved:
            return jsonify({'success': "Issue reported successfully"})
        
        return({'error': "Unable to save issue report"}), 500

    return jsonify({'error': 'Missing key reportDetails'}), 400


## Flask Route Definition for User Feedback Button
## process_feedback() is called anytime a POST is sent to /user-feedback
@app.route("/user-feedback", methods=['POST'])
def process_feedback():
    # Grab Ajax Request
    user_feedback = request.get_json()

    if 'feedback' in user_feedback:
        feedback_report = sanitize_and_process_feedback(user_feedback)
        feedback_saved = save_user_feedback(feedback_report)
        
        if feedback_saved:
            return jsonify({'success': 'Feedback processed successfully'})
        
        return({'error': "Unable to save user feedback"}), 500

    return jsonify({'error': "Missing key feedback."}), 400

# Display Images
@app.route("/images/<filename>")
def get_image(filename):
    if 'png' in filename:
        mimetype = 'image/png'
    elif 'svg' in filename:
        mimetype='image/svg+xml'

    return send_file(f'static/images/{filename}', mimetype=mimetype)


# Flask Bootloader
if __name__ == '__main__':
    load_dotenv()
    app.run(debug=True, host='0.0.0.0', port=8080)
