import logging
import os

# Ensure logs/ directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")

def get_logger(name="pipeline"):
    """
    Returns a configured logger instance.
    Each module can call get_logger(__name__) for scoped logging.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:  # Avoid duplicate handlers
        logger.setLevel(logging.DEBUG)

        # Console handler (INFO and above)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

        # File handler (DEBUG and above)
        fh = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))

        logger.addHandler(ch)
        logger.addHandler(fh)

    return logger
