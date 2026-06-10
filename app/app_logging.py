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