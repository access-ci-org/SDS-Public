import csv
from pathlib import Path
from flask import render_template, request, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.logic.table import initialize_table_info, get_table, organize_table, combine_columns, TableInfo
from app.routes.analytics_routes import ANALYTICS_FILE
from . import settings_bp


@settings_bp.route("/settings")
@login_required
def settings():
    return render_template(
        "settings.html",
        table_info=initialize_table_info(),
        hide_data=current_app.config["HIDE_DATA"],
        use_curated_info=current_app.config["USE_CURATED_INFO"],
        use_ai_info=current_app.config["USE_AI_INFO"],
        use_api=current_app.config["USE_API"],
        api_curated_columns=current_app.config["API_CURATED_COLUMNS"],
        api_ai_columns=current_app.config["API_AI_COLUMNS"],
        share_with_devs=current_app.config["SHARE_WITH_DEVS"],
        share_with_others=current_app.config["SHARE_WITH_OTHERS"]
    )

@settings_bp.route("/update_col_visibility/<path:column_name>", methods=["POST"])
@login_required
def update_col_visibility(column_name):
    if column_name:
        if column_name == "shareWithDevs":
            current_user.shareWithDevs = current_user.toggle_share_with_devs()
            return jsonify({"success": "Share preference udpated successfully"})
        return jsonify({"error": "Invalid column name"}), 400

    return jsonify({"error": "Missing column name"}), 400


@settings_bp.route("/update_col_order", methods=["POST"])
@login_required
def update_column_order():
    data = request.get_json()
    new_col_order = data.get("col_order", [])
    table_info = initialize_table_info()
    try:
        table_info.column_order = new_col_order
        return jsonify({"success": "Column order updated successfully"})
    except Exception as e:
        print(e)
        return jsonify({"error": "Missing column name"}), 500


@settings_bp.route("/update_col_name", methods=["POST"])
@login_required
def update_column_name():
    data = request.get_json()
    original_key = data.get("original_key")
    new_name = data.get("new_name")
    table_info = initialize_table_info()
    try:
        if original_key in table_info.column_names:
            table_info.column_names[original_key] = new_name
            return jsonify({"success": "Column renamed successfully"})

        return jsonify({"error": "Column not found"}), 404
    except Exception as e:
        print(e)
        return jsonify({"error": "Error renaming column"}), 500

@settings_bp.route("/download_software_csv")
@login_required
def download_software_csv():
    # get table info exactly like they are in the '/' route
    table_object = get_table()
    table_info = TableInfo()
    df = organize_table(table_object, table_info)
    df = combine_columns(df, [
        ('Description', 'AI Description'),
    ])
    df = combine_columns(df, [
        ('AI Research Discipline', 'AI Research Field')
    ], combine_data= True)
    try:
        csv_file_path = Path("table.csv")
        # create path and file
        csv_file_path.parent.mkdir(parents=True, exist_ok=True)
        csv_file_path.touch()
        df.to_csv(csv_file_path, index=False)
        return send_file(csv_file_path.resolve(), download_name="software_data.csv", as_attachment=True), 200
    except Exception as e:
        return jsonify({"error": "Error creating csv file"}), 500

@settings_bp.route("/download_software_json")
@login_required
def download_software_json():
    # get table info exactly like they are in the '/' route
    table_object = get_table()
    table_info = TableInfo()
    df = organize_table(table_object, table_info)
    df = combine_columns(df, [
        ('Description', 'AI Description'),
    ])
    df = combine_columns(df, [
        ('AI Research Discipline', 'AI Research Field')
    ], combine_data= True)
    # set software col as key
    df = df.set_index('Software')
    try:
        json_file_path = Path("table.json")
        json_file_path.parent.mkdir(parents=True, exist_ok=True)
        json_file_path.touch()
        df.to_json(json_file_path, orient="index", indent=2)

        return send_file(json_file_path.resolve(), download_name="software_data.json", as_attachment=True), 200
    except Exception as e:
        return jsonify({"error": "Error creating csv file"}), 500

@settings_bp.route("/download_analytics_json")
@login_required
def download_analytics_json():
    try:
        analytics_file = Path(ANALYTICS_FILE)
        # ensure file and path exists
        analytics_file.parent.mkdir(parents=True, exist_ok=True)
        analytics_file.touch()

        return send_file(analytics_file.resolve(), download_name="analytics_data.json", as_attachment=True), 200
    except Exception as e:
        return jsonify({"error": "Error fetching analytics file"}), 500