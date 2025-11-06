"""
Centralized logging configuration for SOXauto.

This module sets up structured JSON logging with consistent formatting
across the application. All log messages include:
- timestamp
- level
- logger name
- message
- service identifier
- Temporal context (when available)
"""

import logging
import sys
from pythonjsonlogger.json import JsonFormatter


class CustomJsonFormatter(JsonFormatter):
    """
    Custom JSON formatter that adds standard fields to all log records.
    """
    
    def add_fields(self, log_record, record, message_dict):
        """
        Add custom fields to the log record.
        
        Args:
            log_record: Dictionary that will be logged as JSON
            record: Original LogRecord object
            message_dict: Dictionary of extra fields
        """
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add standard fields
        log_record['timestamp'] = self.formatTime(record, self.datefmt)
        log_record['level'] = record.levelname
        log_record['name'] = record.name
        log_record['service'] = 'soxauto-cpg1'
        
        # Add message if not already present
        if 'message' not in log_record:
            log_record['message'] = record.getMessage()


def setup_logging(level=logging.INFO, format_as_json=True):
    """
    Configure application-wide logging.
    
    Args:
        level: Logging level (default: INFO)
        format_as_json: If True, use JSON formatting; if False, use standard formatting
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    if format_as_json:
        # JSON formatter for production
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            datefmt='%Y-%m-%dT%H:%M:%S'
        )
    else:
        # Standard formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Log that configuration is complete
    root_logger.info("Logging configuration initialized", extra={
        "format": "json" if format_as_json else "standard",
        "level": logging.getLevelName(level)
    })


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
