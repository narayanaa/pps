import time
from typing import Any

from .logging_utils import LoggingUtils


class ErrorHandler:
    def __init__(self):
        pass

    def handle_error(self, error: Exception, context: str) -> bool:
        """Handles an error and decides whether to continue."""
        LoggingUtils("parser.log").log_message("error", f"{context}: {str(error)}")
        return True  # Continue parsing by default

    def retry_operation(self, operation: callable, max_attempts: int = 3) -> Any:
        """Retries a failed operation."""
        for attempt in range(max_attempts):
            try:
                return operation()
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                time.sleep(2 ** attempt)  # Exponential backoff

    def handle_error(self, error: Exception, context: str) -> bool:
        LoggingUtils("parser.log").log_message("error", f"{context}: {str(error)}")
        return True

    def handle_exception(self, stage, e):
        LoggingUtils("parser.log").log_message("error", f"{stage}: {str(e)}")
