"""Logging configuration for OutSystems-Docs MCP."""

import logging
import sys

from osdocs.config import get_app_config, resolve_path

_configured = False


def _log_uncaught_exception(exc_type, exc_value, exc_tb):
    """sys.excepthook replacement so a fatal crash lands in the log file, not just stderr."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logging.getLogger("osdocs-mcp").critical(
        "Unhandled exception", exc_info=(exc_type, exc_value, exc_tb)
    )


def _configure_root() -> None:
    """Attach console/file handlers to the root logger exactly once.

    All module loggers (``get_logger(__name__)``) have no handlers of their own and simply
    propagate here — this is what keeps every log line from being written multiple times.
    """
    global _configured
    if _configured:
        return
    _configured = True

    config = get_app_config()
    log_level = config.get("logging.level", "INFO")
    log_file = config.get("logging.file", "")

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # capture all levels, filter at handler

    # Console handler (stderr, so stdout stays reserved for MCP stdio protocol messages)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    root_logger.addHandler(console_handler)

    # File handler (if configured)
    if log_file:
        log_path = resolve_path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(log_level)  # Honor configured logging.level
        file_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        root_logger.addHandler(file_handler)

    sys.excepthook = _log_uncaught_exception


def get_logger(name: str = "osdocs-mcp") -> logging.Logger:
    """Get a module logger. Ensures the root logger's handlers are configured exactly once."""
    _configure_root()
    return logging.getLogger(name)
