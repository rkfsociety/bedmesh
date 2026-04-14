import logging

def setup_logger(level=logging.INFO):
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def get_logger(name):
    return logging.getLogger(name)