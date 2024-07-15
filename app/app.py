from flask import Flask, render_template, jsonify, send_file, request
from dotenv import load_dotenv
from app.reports import sanitize_and_process_reports
from app.feedback import sanitize_and_process_feedback
from app.softwareTable import create_software_table

import os
import re
import json
import pandas as pd
from datetime import datetime
# import logging

app = Flask(__name__)

# Main Route
@app.route("/")
def software_search():
    try:
        df = pd.read_csv("./data/CSV/softwareTable.csv", keep_default_na=False)
        print("Table found!")
    except FileNotFoundError as e:
        df = create_software_table()
        print(e)
    
    table = df.to_html(classes='table-striped" id = "softwareTable',index=False,border=1).replace('\\n', '<br>')
    return render_template("software_search.html",table=table)

# 'Example Use' Modal Route
@app.route("/example_use/<software_name>")
def get_example_use(software_name):
    
    if software_name == '7-Zip':
        software_name = '7z'

    file_directory = "./data/exampleUse/"
    
    normalize_software_name = re.escape(software_name).lower()

    pattern = re.compile(normalize_software_name, re.IGNORECASE)

    try:
        for filename in os.listdir(file_directory):
            if pattern.search(filename):
                with open(os.path.join(file_directory,filename),'r') as file:
                    file_content = file.read()
                    return(jsonify({"use": file_content}))
        return jsonify({"use": '**Unable to find use case record**'})
    except Exception as e:
        print(e)
        return(jsonify({"use": '**Unable to find use case record**'})), 500

# 'Report Issue' Button Route
@app.route("/report-issue", methods=['POST'])
def report_issue():
    issue_report = request.get_json()

    if issue_report['reportDetails']:
        report = sanitize_and_process_reports(issue_report)
        current_datetime = report['datetime']

        report_folder = os.path.join('reports', current_datetime)
        os.makedirs(report_folder, exist_ok=True)
        report_filename = os.path.join(report_folder, 'report.json')
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=4)

    else:
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_folder = os.path.join('reports', current_datetime)
        os.makedirs(report_folder, exist_ok=True)
        report_filename = os.path.join(report_folder, 'report.json')
        with open(report_filename, 'w') as f:
            json.dump(issue_report, f, indent=4)

    return jsonify({'message': 'Issue reported successfully'})


## Flask Route Definition for User Feedback Button
## process_feedback() is called anytime a POST is sent to /user-feedback
@app.route("/user-feedback", methods=['POST'])
def process_feedback():
    # Grab Ajax Request
    user_feedback = request.get_json()

    # Sanitize Feedback if necessary
    if user_feedback['feedbackForm']:
        feedback = sanitize_and_process_feedback(user_feedback)
        current_datetime = feedback['datetime']

        # Create folder and make feedback file
        feedback_folder = os.path.join('feedback', current_datetime)
        os.makedirs(feedback_folder, exist_ok=True)
        feedback_filename = os.path.join(feedback_folder, 'feedback.json')
        with open(feedback_filename, 'w') as f:
            json.dump(feedback, f, indent=4)

    else:
        current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        feedback_folder = os.path.join('feedback', current_datetime)
        os.makedirs(feedback_folder, exist_ok=True)
        feedback_filename = os.path.join(feedback_folder, 'feedback.json')
        with open(feedback_filename, 'w') as f:
            json.dump(user_feedback, f, indent=4)

    return jsonify({'success': 'Feedback processed successfully'})


######################
### TESTING-IGNORE ###
######################
# Set up basic logging
#logging.basicConfig(level=logging.DEBUG)

#@app.route("/data", methods=['POST'])
#def data():
    try:
        # Log start of the request processing
        logging.debug("Starting to process request")
        # Read parameters from DataTables
        draw = request.form.get('draw', type=int, default=1)                        # A counter to ensure that the Ajax requests are processed sequentially.
        start = request.form.get('start', type=int, default=0)                      # The starting index of the data to be fetched (for pagination)
        length = request.form.get('length', type=int, default=10)                   # The number of records to fetch (page size)
        order_column = request.form.get('order[0][column]', type=int, default=0)    # The column index to sort by
        order_dir = request.form.get('order[0][dir]', default='asc')                # The direction of sorting ('asc' or 'desc')
        search_value = request.form.get('search[value]', default='')                # The search term entered by the user

        logging.debug(f"Draw: {draw}, Start: {start}, Length: {length}, Order Column: {order_column}, Order Dir: {order_dir}, Search Value: {search_value}")

        # Read the CSV file
        csv_path = './data/CSV/softwareTable.csv'  # Adjust path to your CSV file
        logging.debug(f"Reading CSV file from: {csv_path}")
        df = pd.read_csv(csv_path)  # Adjust path to your CSV file

        # Define the column mapping
        columns = [
        'Software','RP Name','✨Software Type','✨Software Class','✨Research Field','✨Research Area','✨Research Discipline','Software Description',
        '✨Core Features','✨General Tags',"Software's Web Page",'Software Documentation','Example Software Use','RP Software Documentation','Version Info',
        '✨AI Description','✨Example Use'
        ]
        logging.debug(f"CSV columns: {columns}")

        # Filtering
        if search_value:
            logging.debug(f"Applying search filter: {search_value}")
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_value, case=False).any(), axis=1)]

        # Sorting
        logging.debug(f"Sorting by column: {columns[order_column]}, direction: {order_dir}")
        if order_dir == 'asc':
            df = df.sort_values(by=columns[order_column])
        else:
            df = df.sort_values(by=columns[order_column], ascending=False)

        # Paging
        records_total = len(df)
        logging.debug(f"Total records: {records_total}")
        df_page = df.iloc[start:start+length]
        records_filtered = len(df)
        logging.debug(f"Filtered records: {records_filtered}")

        # Prepare the response
        # Reorder DataFrame columns to match the expected order
        df_page_reordered = df_page[columns]

        # Convert reordered DataFrame to list of dictionaries
        data_reordered = df_page_reordered.to_dict(orient='records')

        response = {
            "draw": draw,
            "recordsTotal": records_total,
            "recordsFiltered": records_filtered,
            "data": data_reordered
        }

        # Limit the data shown in logs for debugging
        logging.debug(f"Records Total: {records_total}, Records Filtered: {records_filtered}")
        logging.debug(f"Data Sample: {df_page.head().to_dict(orient='records')}")

        return jsonify(response)

    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return jsonify({"error": str(e)})
##################
### END IGNORE ###
##################


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
