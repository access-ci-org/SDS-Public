from datetime import datetime


#############################################################
#   define_and_process_reports                              #
#       Processing for 'Report Issue' button functionality, #
#       allowing users to report problems to the team       #
#       Parameters:                                         #
#           issue_report: contents of AJAX call             #
#       Return:                                             #
#           report: finished user report, ready to send     #
#                   to the server                           #
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