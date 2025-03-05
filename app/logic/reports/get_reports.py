from pathlib import Path
from typing import List, Dict
from app.models.userReports import UserReports
from playhouse.shortcuts import model_to_dict
import json


def get_reports_and_feedback() -> List[Dict[str, str]]:
    """ """
    user_reports = UserReports.select()
    user_reports_list = [model_to_dict(report) for report in user_reports]

    return user_reports_list


def get_user_reports_from_files(path: str = "report") -> List[Dict[str, str]]:
    """
    Reads all of the json generated by user reports from the given path
    and return a pandas.DataFrame with the result
    """
    reports_dir = Path.cwd() / path
    reports = []

    for dir_path in reports_dir.iterdir():
        if dir_path.is_dir():
            report_path = dir_path / f"{path}.json"
        try:
            with open(report_path, "r") as r:
                report_data = json.load(r)
            reports.append(report_data)

        except FileNotFoundError:
            print(f"File not found: {report_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {report_path}")

    return reports


def get_user_feedback_from_files(path: str = "feedback") -> List[Dict[str, str]]:
    """ """

    feedback_dir = Path.cwd() / path
    feedbacks = []

    for dir_path in feedback_dir.iterdir():
        if dir_path.is_dir():
            feedback_path = dir_path / f"feedback.json"

        try:
            with open(feedback_path, "r") as f:
                feedback_data = json.load(f)
            feedbacks.append(feedback_data)

        except FileNotFoundError:
            print(f"File not found; {feedback_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {feedback_path}")

    return feedbacks
