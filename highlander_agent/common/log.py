import logging
import logging.config
import logging.handlers
import os


def getLogger(name='unknown'):
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logger.conf'))
    logging.config.fileConfig(config_path)

    loggers = logging.getLogger(name)

    return loggers