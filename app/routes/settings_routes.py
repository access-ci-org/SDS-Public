from flask import render_template, request, jsonify, current_app
from flask_login import login_required
from app.logic.table import initialize_table_info
from . import settings_bp


@settings_bp.route("/settings")
@login_required
def settings():
    return render_template(
        "settings.html",
        table_info=initialize_table_info(),
        drop_columns=current_app.config["DROP_COLUMNS"],
        use_curated_info=current_app.config["USE_CURATED_INFO"],
        use_ai_info=current_app.config["USE_AI_INFO"],
        use_api=current_app.config["USE_API"],
        api_curated_columns=current_app.config["API_CURATED_COLUMNS"],
        api_ai_columns=current_app.config["API_AI_COLUMNS"],
    )


@settings_bp.route("/update_col_visibility/<path:column_name>", methods=["POST"])
@login_required
def update_col_visibility(column_name):
    table_info = initialize_table_info()
    if column_name:
        if column_name in table_info.column_names:
            column = table_info.column_names[column_name]
            drop_columns = current_app.config["DROP_COLUMNS"]
            if column in drop_columns:
                drop_columns.remove(column)
            else:
                drop_columns.append(column)
            current_app.config["DROP_COLUMNS"] = drop_columns
            return jsonify({"success": "Column updated successfully"})
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
