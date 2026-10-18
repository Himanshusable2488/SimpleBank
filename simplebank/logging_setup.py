"""Switches on logging to a file so every action leaves a trace."""
import logging
from pathlib import Path


def setup_logging(log_file="logs/simplebank.log", level=logging.INFO):
    logger = logging.getLogger("simplebank")
    if any(isinstance(h, logging.FileHandler) for h in logger.handlers):
        return  # already set up, do not add a second handler
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
    )
    logger.setLevel(level)
    logger.addHandler(handler)