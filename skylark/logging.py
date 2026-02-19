import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging(level: int = logging.INFO, logfile: str = 'logs/app.log') -> None:
    """Configure root logger to log to stdout and to a rotating file for local debugging.

    Call this early in `app.py` so both local and cloud runs emit logs to stdout
    (Streamlit captures stdout) and to `logs/app.log` for local inspection.
    """
    logger = logging.getLogger()
    if logger.handlers:
        # already configured
        return

    logger.setLevel(level)

    # Console handler -> stdout
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(ch)

    # File handler for local debugging (rotates at 5MB)
    try:
        os.makedirs(os.path.dirname(logfile), exist_ok=True)
        fh = RotatingFileHandler(logfile, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        fh.setLevel(level)
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        logger.addHandler(fh)
    except Exception:
        # non-fatal; continue without file logging
        logger.warning("Could not initialize file logging; continuing with stdout only.")
