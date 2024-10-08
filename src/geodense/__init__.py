import contextlib
import logging
import sys
from importlib.metadata import PackageNotFoundError, version
from logging import Formatter, NullHandler, StreamHandler

logging.getLogger(__name__).addHandler(NullHandler())

with contextlib.suppress(PackageNotFoundError):
    __version__ = version("geodense")


def get_log_handler(verbose: bool) -> logging.StreamHandler:
    formatter = get_formatter(verbose)
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)
    return handler


def get_formatter(verbose: bool) -> Formatter:
    format_string_default = "[%(levelname)s] %(message)s"
    format_string_verbose = (
        f"[%(levelname)s] [%(filename)s:%(lineno)d] [{__name__}.%(module)s.%(funcName)s] %(message)s"
    )
    format_string = format_string_verbose if verbose else format_string_default
    formatter = logging.Formatter(format_string)
    return formatter


# copied from https://github.com/urllib3/urllib3/blob/f7cd7f3f632cf5224f627536f02c2abf7e4146d1/src/urllib3/__init__.py and adapted
# error handling convention:
# expected caught errors -> log as error
# unexpected caugh errors (this is the case for a generic error handler) -> log as exception
def add_stderr_logger(verbose: bool = False) -> StreamHandler:
    """
    Adding streamhandler to the logger, used for CLI output to stderr.

    Returns the handler after adding it.
    """
    # This method needs to be in this __init__.py to get the __name__ correct
    # even if geodense is vendored within another package.
    # verbose: False
    #   - loglevel:  WARNING
    #   - format_string: default
    # verbose: True
    #   - loglevel:  DEBUG
    #   - format_string: verbose
    level = logging.DEBUG if verbose else logging.WARNING
    handler = get_log_handler(verbose)
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)
    logger.setLevel(level)
    return handler
