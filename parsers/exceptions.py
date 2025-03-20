import logging
from app.app_logging import logger

class DataProcessingError(Exception):
    """Custom exception for data processing error"""

    def __init__(
        self, message: str, level: int = logging.ERROR, exec_info: Exception = None
    ):
        super().__init__(message)
        self.level = level
        self.exec_info = exec_info
        # Log the error when it's created
        logger.log(self.level, message, exc_info=exec_info)