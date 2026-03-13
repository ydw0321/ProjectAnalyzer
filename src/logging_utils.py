import logging
import os


def setup_logging(level: str | None = None) -> None:
    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, resolved_level, logging.INFO)

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        root_logger.setLevel(log_level)

    for noisy_logger in ["neo4j", "urllib3", "chromadb"]:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
