from datetime import datetime
from pathlib import Path
from typing import Dict, Any
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
def sanitize_and_process_reports(
    issue_report: Dict[str, Any], report_type: str
) -> Dict[str, Any]:

    # Generate timestamp
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create the report to be submitted
    if report_type == "feedback":
        report = {
            "datetime": current_datetime,
            "user_message": issue_report.get("userMessage", ""),
            "report_type": report_type,
        }
        return report

    report = {
        "datetime": current_datetime,
        "user_message": issue_report.get("userMessage", ""),
        "element_text": issue_report.get("cellText", ""),
        "row_name": issue_report.get("rowName", ""),
        "row_index": issue_report.get("rowIndex", ""),
        "column_name": issue_report.get("columnName", ""),
        "column_index": issue_report.get("columnIndex", ""),
        "report_type": report_type,
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
def save_user_report(issue_report: Dict[str, Any]) -> bool:

    try:
        report_type = issue_report["report_type"]

        report_folder = (
            Path.cwd() / report_type / issue_report["datetime"]
        )  # create a path object for new feedback location
        report_folder.mkdir(parents=True, exist_ok=True)
        report_file = report_folder / f"{report_type}.json"

        with open(report_file, "w") as f:
            json.dump(issue_report, f, indent=4)

        issue_report["datetime"] = datetime.strptime(
            issue_report["datetime"], "%Y-%m-%d_%H-%M-%S"
        )

        return True

    except KeyError:
        print(
            f"Improperly formatted issue_report. One or multiple keys missing: \n{issue_report}"
        )
        return False

    except Exception as e:
        print(e)

        return False
