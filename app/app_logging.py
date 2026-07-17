import logging
from logging.handlers import TimedRotatingFileHandler

from app.paths import state_dir

_log_dir = state_dir() / "logs"
_log_dir.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
FORMAT = '%(asctime)s: %(name)s: %(levelname)s: %(message)s'
formatter = logging.Formatter(FORMAT)
handler = TimedRotatingFileHandler(filename=str(_log_dir / 'sds.log'), when='D', interval=31, backupCount=24, atTime='midnight')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(level=logging.DEBUG)

# One line per authenticated /api/v1 request:
#   <timestamp>: <key prefix> "<key label>" <endpoint>
# Complete history lives in these files — rotated weekly (Monday midnight),
# rotated files are never deleted. The api_key_log DB table keeps only the
# newest rows for in-app queries.
_api_log_dir = _log_dir / "api"
_api_log_dir.mkdir(parents=True, exist_ok=True)
api_request_logger = logging.getLogger("sds.api_requests")
_api_handler = TimedRotatingFileHandler(
    filename=str(_api_log_dir / 'api-requests.log'),
    when='W0',
)
_api_handler.setFormatter(logging.Formatter('%(asctime)s: %(message)s'))
api_request_logger.addHandler(_api_handler)
api_request_logger.setLevel(logging.INFO)