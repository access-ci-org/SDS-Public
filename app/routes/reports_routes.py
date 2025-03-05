import json
from flask import request, render_template, jsonify
from flask_login import login_required
from app.models import db
from app.models.userReports import UserReports
from app.logic.reports.reports import sanitize_and_process_reports, save_user_report
from app.logic.reports.get_reports import get_reports_and_feedback
from . import reports_bp


# View user reports
@reports_bp.route("/reports")
@login_required
def view_user_reports():
    all_reports = get_reports_and_feedback()
    return render_template("viewReports.html", user_reports=all_reports)


# 'Report Issue' Button Route
@reports_bp.route("/report-issue", methods=["POST"])
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
@reports_bp.route("/user-feedback", methods=["POST"])
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


# Mark report as resolved
@reports_bp.route("/chage_issue_status", methods=["POST"])
@login_required
def chage_issue_status():
    user_report = request.get_json()
    updated_successfully = False
    with db.atomic() as transaction:
        num_updated = (
            UserReports.update({"resolved": user_report["isResolved"]}).where(
                UserReports.id == user_report["reportId"]
            )
        ).execute()
        if num_updated > 1:
            transaction.rollback()
        else:
            updated_successfully = True

    return json.dumps({"success": updated_successfully})
