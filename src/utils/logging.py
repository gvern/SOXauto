"""
JSON logging utilities for SOXauto.

Provides a minimal dependency-free JSON formatter and a setup helper
that plays well with Temporal workflows and activities.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict


class JsonFormatter(logging.Formatter):
    """Simple JSON formatter without external dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Optional extras
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)

        # Merge extra fields (provided via LoggerAdapter or 'extra=')
        for key, value in record.__dict__.items():
            if key in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
            ):
                continue
            # Avoid overwriting base keys unless intentional
            if key not in base:
                base[key] = value

        # Add global context
        base.setdefault("service", os.getenv("SOX_SERVICE", "soxauto-cpg1"))
        base.setdefault("env", os.getenv("ENV", "dev"))

        return json.dumps(base, ensure_ascii=False)


def setup_json_logging(level: int = logging.INFO) -> None:
    """Configure root logger with JSON formatter once."""
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) and isinstance(getattr(h, "formatter", None), JsonFormatter) for h in root.handlers):
        return  # already configured

    root.setLevel(level)

    # Remove existing handlers to avoid duplicate logs in some environments
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)


def enrich(logger: logging.Logger, **context: Any) -> logging.LoggerAdapter:
    """Return a LoggerAdapter that injects static context into each record."""
    return logging.LoggerAdapter(logger, extra=context)
