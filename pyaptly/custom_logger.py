import logging

from colorama import Fore, Style

from . import util


class CustomFormatter(logging.Formatter):
    debug = "%(levelname)s - %(filename)s:%(lineno)d: %(message)s"
    info_warn = "%(message)s"
    error_plus = "%(levelname)s: %(message)s"

    FORMATS_COLOR = {
        logging.DEBUG: Style.DIM + debug + Style.RESET_ALL,
        logging.INFO: Fore.YELLOW + info_warn + Style.RESET_ALL,
        logging.WARNING: info_warn,
        logging.ERROR: Fore.RED + error_plus + Style.RESET_ALL,
        logging.CRITICAL: Fore.MAGENTA + error_plus + Style.RESET_ALL,
    }

    FORMATS = {
        logging.DEBUG: debug,
        logging.INFO: info_warn,
        logging.WARNING: info_warn,
        logging.ERROR: error_plus,
        logging.CRITICAL: error_plus,
    }

    def format(self, record):
        if util.isatty():
            formats = self.FORMATS_COLOR   # pragma: no cover
        else:
            formats = self.FORMATS

        log_fmt = formats.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
