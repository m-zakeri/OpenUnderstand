import time
import logging
import configparser
from os.path import basename
from openunderstand.gen.javaLabeled import JavaParserLabeled


class ClassTypeData:
    def __init__(self):
        self.parentClass = None
        self.childClass = None
        self.file_path: str = ""
        self.package_name: str = ""
        self.line: int = -1
        self.column: int = -1
        self.prefixes: list = []

    def set_child_class(self, child):
        self.childClass = child

    def set_parent_class(self, parent):
        self.parentClass = parent

    def set_file_path(self, file_path: str):
        self.file_path = file_path

    def set_package_name(self, name: str):
        self.package_name = name

    def set_line(self, line: int):
        self.line = line

    def set_column(self, column: int):
        self.column = column

    def set_prefixes(self, prefix_list: list):
        self.prefixes = prefix_list

    def get_long_name(self) -> str:
        # IDENTIFIER(), not getText(): getText() on a class declaration is the
        # entire class body, which ended up spliced into longnames as
        # "org.json.classJSONML{privatestaticObjectparse(...". get_name()
        # below already uses the right accessor.
        return self.package_name + "." + str(self.childClass.IDENTIFIER())

    def get_type(self) -> str:
        return "extends" + " " + self.parentClass

    def get_name(self) -> str:
        return str(self.childClass.IDENTIFIER())

    def get_contents(self) -> str:
        return self.childClass.getText()

    def get_prefixes(self) -> list:
        return self.prefixes


def timer_decorator():
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            logger = setup_logger()
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


import os


#: Used when config.ini is absent, which is the normal case for an installed
#: package: a user who runs `pip install openunderstand` has no config file,
#: and until these defaults existed the first call raised KeyError('Logging')
#: from a file they were never told to create.
_DEFAULTS = {
    # "auto": use the C++ parse accelerator when the installed wheel carries
    # one, and the pure-Python ANTLR runtime when it does not. Hardcoding
    # "Python" here meant a user who pip-installed a wheel that ships the
    # accelerator never got it; hardcoding "C++" would log a fallback warning
    # on every pure-Python install. Both trees are identical -- build.py
    # asserts that with speedy_antlr_tool.validate, and both engines produce
    # the same database fingerprint on every fixture.
    "Config": {"engine_core": "auto"},
    "Logging": {"filename": "", "level": "INFO"},
}


def setup_config():
    """Configuration, with defaults for everything the code reads.

    The file is looked for beside the current working directory first -- which
    is where the CLI writes it -- and then at the historical location three
    levels above this module. Missing keys fall back to _DEFAULTS rather than
    raising, so the library is usable without any configuration at all.
    """
    config = configparser.ConfigParser()
    config.read_dict(_DEFAULTS)
    config.read([
        os.path.join(os.getcwd(), "config.ini"),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "config.ini"
        ),
    ])
    return config


_LOGGER = None


def setup_logger():
    """The shared logger, created once.

    Memoized because `timer_decorator` calls this per listener per file: it
    used to add a new FileHandler on every call, so a 22-file analysis ended
    up with hundreds of handlers all writing the same lines.

    With no log filename configured it logs to stderr rather than failing --
    an analysis library should not require a log destination to run.
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    config = setup_config()
    logger = logging.getLogger("openunderstand")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    filename = config["Logging"].get("filename", "")
    try:
        handler = logging.FileHandler(filename) if filename else logging.StreamHandler()
    except OSError:
        handler = logging.StreamHandler()
    handler.setLevel(getattr(logging, config["Logging"].get("level", "INFO").upper(),
                             logging.INFO))
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)

    _LOGGER = logger
    return logger
