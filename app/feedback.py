from datetime import datetime

def sanitize_and_process_feedback(user_feedback):
    # Pull user-submitted form contents from modal
    userForm = user_feedback.get('feedbackForm', '')                   
    
    # Generate timestamp
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Create report
    report = {
        "datetime": current_datetime,
        "userForm": userForm,
    }

    return report