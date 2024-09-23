from datetime import datetime
import pytz

def get_last_updated(file_path="./static/last_updated.txt", timezone='US/Eastern'):
    """
    returns datetime of when the software_table data was last updated
    """
    with open(file_path, 'r') as luf:
        date_time = luf.readline().strip()

    try:
        date_obj = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        # Format output
        output = date_obj.strftime("%B %d, %Y at %I:%M:%S %p Eastern Daylight Time")
        return output
    except Exception as e:
        print("ERROR trying to convert datetime", e)
        return(date_time)