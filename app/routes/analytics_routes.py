from flask import render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from pathlib import Path
import json
from app.app_logging import logger
from app.logic.table import initialize_table_info
from app.paths import state_dir
from . import analytics_bp


def analytics_file() -> Path:
    return state_dir() / "analytics" / "analytics_data.json"


def load_analytics_data():
    f = analytics_file()
    if not f.exists():
        return {'searches': [], 'filters': [], 'softwareViews': []}

    try:
        with f.open('r') as af:
            return json.load(af)
    except (json.JSONDecodeError, OSError, ValueError) as e:
        logger.error(f"Analytics data load failed: {e}")
        return {'searches': [], 'filters': [], 'softwareViews':[]}


def save_analytics_data(data):
    f = analytics_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open('w') as af:
        json.dump(data, af, indent=2)

@analytics_bp.route('/analytics/track', methods=['POST'])
def track_analytics():
    try:
        event = request.get_json()
        data = load_analytics_data()

        event_type = event['eventType']
        event_data = event['data']
        event_data['timestamp'] = event['timestamp']

        if event_type == 'search':
            data['searches'].append(event_data)
        elif event_type == 'filter':
            data['filters'].append(event_data)
        elif event_type == 'software_view':
            data['softwareViews'].append(event_data)
        save_analytics_data(data)
        return jsonify({'success': True})
    except Exception as e:
        print(f"error: {e}")
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/analytics/data')
@login_required
def get_analytics_data():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        data = load_analytics_data()

        if start_date and end_date:
            # filter by date range
            for category in ['searches', 'filters', 'softwareViews']:
                data[category] = [
                    item for item in data[category]
                    if start_date <= item['timestamp'][:10] <= end_date
                ]
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@analytics_bp.route('/analytics/dashboard')
@login_required
def analytics_dashboard():
    return render_template('analytics_dashboard.html')