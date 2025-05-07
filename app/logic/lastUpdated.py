from datetime import datetime
from pathlib import Path


def get_last_updated(
    file_path: str = "app/static/last_updated.txt", timezone: str = "US/Eastern"
) -> str:
    """
    returns datetime of when the software_table data was last updated
    """
    path = Path.cwd() / file_path
    with open(path, "r") as luf:
        date_time = luf.readline().strip()

    try:
        date_obj = datetime.strptime(date_time, "%Y-%d-%m %H:%M:%S")
        # Format output
        output = date_obj.strftime("%B %d, %Y at %I:%M:%S %p Eastern Daylight Time")
        return output
    except Exception as e:
        print("ERROR trying to convert datetime", e)
        return date_time
