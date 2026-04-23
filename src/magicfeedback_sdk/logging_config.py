import logging


def configure_logger(name="magicfeedback_sdk"):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    return logger
