# core/logger.py
import logging
import sys

def get_logger(name: str):
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stdout)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        h.setFormatter(fmt)
        logger.addHandler(h)
        logger.setLevel("INFO")
    return logger
