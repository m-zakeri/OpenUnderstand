import time
import logging
import configparser
from os.path import basename


def timer_decorator(logger):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            file_address = kwargs.get("file_address")
            result = func(self, *args, **kwargs)
            end_time = time.time()
            elapsed_time = end_time - start_time
            logger.info(
                f"The function '{func.__name__}' with file address '{basename(file_address)}' took {elapsed_time:.2f} seconds to execute."
            )
            return result

        return wrapper

    return decorator


def setup_config():
    config = configparser.ConfigParser()
    config.read("config.ini")
    return config


def setup_logger():
    # Read configurations from config.ini file
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Create logger object
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler and set the log level based on the configuration
    file_handler = logging.FileHandler(config["Logging"]["filename"])
    file_handler.setLevel(getattr(logging, config["Logging"]["level"].upper()))

    # Create log formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add file handler to the logger
    logger.addHandler(file_handler)

    return logger
