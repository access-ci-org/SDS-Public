from datetime import datetime
from pathlib import Path
import json

#############################################################
#   define_and_process_reports                              #
#       Processing for 'Report Issue' button functionality, #
#       allowing users to report problems to the team       #
#       Parameters:                                         #
#           issue_report {JSON}: contents of AJAX call      #
#       Return:                                             #
#           report {dict}: finished user report, ready to   #
#                   send to the server                      #
#############################################################
def sanitize_and_process_reports(issue_report):
    # Get user-submitted feedback from modal
    user_form = issue_report.get('formReport', '')
    
    # Store reportDetails from issueReporting.py into report_details
    report_details = issue_report['reportDetails']

    # Generate timestamp
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Separate report_details into its component parts                  
    page_url = report_details['pageUrl']
    element_type = report_details.get('elementType', '')
    element_class = report_details.get('elementClass', '')
    element_text = report_details.get('elementText', '')
    table_cell_info = report_details.get('tableCellInfo', {})
    custom_issue = report_details.get('customIssue', '')

    # Create the report to be submitted
    report = {
        "datetime": current_datetime,
        "pageUrl": page_url,
        "elementType": element_type,
        "elementClass": element_class,
        "elementText": element_text,
        "tableCellInfo": table_cell_info,
        "userForm": user_form,
        "customIssue": custom_issue,
    }

    return report


#########################################################################
#   save_user_report                                                    #
#       creates a new directory for each report and dumps the report    #
#       text into a json file inside the dir.                           #
#   parameter:                                                          #
#       issue_report{dict}: report with issue information. returned from#
#           sanitize_and_process_reports function                       #
#   return:                                                             #
#       True{bool}: If report was successfully saved                    #
#       False{bool}: If there was an error saving the report            #
#########################################################################
def save_user_report(issue_report):
    
    try:
        # cwd Returns the current working directory. 
        # In our case it returns the cwd of where the application was run from (the app dir) not this .py file
        report_folder = Path.cwd() / "reports" / issue_report['datetime'] # create a path object for new feedback location
        report_folder.mkdir(parents=True, exist_ok=True)
        report_file = report_folder / "report.json"

        with open(report_file, 'w') as f:
            json.dump(issue_report, f, indent=4)
        
        return False
    
    except Exception as e:
        print(e)
        
        return False