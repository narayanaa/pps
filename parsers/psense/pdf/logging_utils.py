"""Tiny wrapper around the std‑lib *logging* for uniform formatting."""
from __future__ import annotations

import logging
from pathlib import Path


class LoggingUtils:
    def __init__(self, logfile: str | Path):
        log_path = Path(logfile)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
            handlers=[
                logging.FileHandler(log_path),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger("PDFParser")

    # Proxy helpers --------------------------------------------------
    def log_info(self, msg: str, *args):
        self.logger.info(msg, *args)

    def log_error(self, msg: str, *args):
        self.logger.error(msg, *args)

    def log_message(self, level: str, msg: str, *args):
        level = level.lower()
        if level == "info":
            self.logger.info(msg, *args)
        elif level == "warning":
            self.logger.warning(msg, *args)
        elif level == "error":
            self.logger.error(msg, *args)
        elif level == "debug":
            self.logger.debug(msg, *args)
        elif level == "critical":
            self.logger.critical(msg, *args)
        else:
            self.logger.info(msg, *args)  # fallback
