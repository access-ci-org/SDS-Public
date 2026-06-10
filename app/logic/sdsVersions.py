from app import app
from app.app_logging import logger
import requests
from packaging.version import Version, InvalidVersion

PRIORITY_TO_ALERT = {
  "high": "danger",
  "medium": "warning",
  "low": "info",
}

def get_pending_updates():
    """
    Fetches SDS versions and returns:
    - Any versions newer than the current version
    - A deprecation notice if the current version is deprecated
    """
    headers = {
        "X-API-Key": app.config["API_KEY"],
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(
            f"{app.config['SDS_API_URL']}api/v1.1/get-sds-version",
            headers=headers,
            timeout=8
        )
        if response.status_code != 200:
            logger.warning(f"Error from api server while trying to fetch SDS versions: status {response.status_code}")
            return []

        data = response.json()["data"]
        current_version_str = app.config["SDS_VERSION"]

        try:
            current_version = Version(current_version_str)
        except InvalidVersion:
            logger.error(f"Current SDS version '{current_version_str}' is not a valid version string")
            return []

        alerts = []

        for entry in data:
            try:
                entry_version = Version(entry["version_number"])
            except InvalidVersion:
                logger.warning(f"Skipping invalid version number in SDS data: {entry['version_number']}")
                continue

            # Check if current version is deprecated
            if entry_version == current_version and entry["status"] == "deprecated":
                alerts.append({
                    **entry,
                    "alert_type": "danger",
                    "alert_message": f"Your current version ({current_version_str}) is deprecated. Please update immediately."
                })

            # Collect anything newer than current
            elif entry_version > current_version:
                alerts.append({
                    **entry,
                    "alert_type": "warning" if entry["update_priority"] == "high" else "info",
                    "alert_message": f"SDS v{entry['version_number']} is available ({entry['status']}){': ' + entry['description'] if entry['description'] else ''}."
                })

        logger.info(f"Found {len(alerts)} relevant update(s) for current version {current_version_str}")
        return alerts

    except Exception as e:
        logger.error(f"Error while trying to fetch SDS versions: {e}")
        return []