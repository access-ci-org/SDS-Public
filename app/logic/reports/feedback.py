from datetime import datetime
from pathlib import Path
import json


#########################################################################
#   sanitize_and_process_feedback                                       #
#       Process the user feedback. Currently no code is added to for    #
#       sanitization.                                                   #
#   parameter:                                                          #
#       user_feedback {dict}: dict with feedback as a key and the       #
#           feedback retrieved from the user as values                  #
#   return:                                                             #
#       report{dict}: dict with datetime and feedback as keys. datetime #
#           contains the date and time of when the report was received  #
#########################################################################
def sanitize_and_process_feedback(user_feedback):
    # Pull user-submitted form contents from modal
    feedback_text = user_feedback['feedback']
    
    # Generate timestamp
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create report
    report = {
        "datetime": current_datetime,
        "feedback": feedback_text,
    }

    return report

#########################################################################
#   save_user_feedback                                                  #
#       creates a new directory for each feedback and dumps the feedback#
#       text into a json file inside the dir.                           #
#   parameter:                                                          #
#       feedback_report{dict}: dict with 'feedback' and 'datetime' as   #
#           keys. obtained from sanitize_and_process_feedback function  #
#   return:                                                             #
#       True{bool}: If feedback was successfully saved                  #
#       False{bool}: If there was an error saving the feedback          #
#########################################################################
def save_user_feedback(feedback_report):

    try:
        # cwd Returns the current working directory. 
        # In our case it returns the cwd of where the application was run from (the app dir) not this .py file
        feedback_folder = Path.cwd() / "feedback" / feedback_report['datetime']    
        feedback_folder.mkdir(parents=True, exist_ok=True)
        feedback_file = feedback_folder / "feedback.json"

        with open(feedback_file, 'w') as f:
            json.dump(feedback_report, f, indent=4)

        return True

    except Exception as e:
        print(e)

        return False
        