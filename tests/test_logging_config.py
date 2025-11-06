"""
Tests for the structured JSON logging configuration.

These tests validate that:
1. Logging can be configured with JSON formatting
2. Log messages include expected fields (timestamp, level, name, message, service)
3. Additional context can be added to log messages
4. Both JSON and standard formats work correctly
"""

import pytest
import logging
import json
import io
import sys
from src.core.logging_config import setup_logging, get_logger, CustomJsonFormatter


def test_json_formatter_fields():
    """Test that CustomJsonFormatter adds the expected standard fields."""
    # Create a logger with JSON formatter
    logger = logging.getLogger("test_json")
    logger.setLevel(logging.INFO)
    
    # Capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    formatter = CustomJsonFormatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Log a message
    logger.info("Test message")
    
    # Parse the JSON output
    log_output = log_capture.getvalue().strip()
    log_data = json.loads(log_output)
    
    # Verify required fields
    assert "timestamp" in log_data
    assert "level" in log_data
    assert log_data["level"] == "INFO"
    assert "name" in log_data
    assert log_data["name"] == "test_json"
    assert "message" in log_data
    assert log_data["message"] == "Test message"
    assert "service" in log_data
    assert log_data["service"] == "soxauto-cpg1"
    
    # Clean up
    logger.removeHandler(handler)


def test_json_formatter_with_extra_fields():
    """Test that extra fields are included in JSON output."""
    # Create a logger with JSON formatter
    logger = logging.getLogger("test_json_extra")
    logger.setLevel(logging.INFO)
    
    # Capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    formatter = CustomJsonFormatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Log a message with extra fields
    logger.info("Test message with context", extra={
        "ipe_id": "IPE_07",
        "cutoff_date": "2024-01-31",
        "row_count": 150
    })
    
    # Parse the JSON output
    log_output = log_capture.getvalue().strip()
    log_data = json.loads(log_output)
    
    # Verify extra fields are present
    assert log_data["ipe_id"] == "IPE_07"
    assert log_data["cutoff_date"] == "2024-01-31"
    assert log_data["row_count"] == 150
    
    # Clean up
    logger.removeHandler(handler)


def test_setup_logging_json_format():
    """Test that setup_logging configures JSON formatting correctly."""
    # Save original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    
    try:
        # Setup JSON logging
        setup_logging(level=logging.INFO, format_as_json=True)
        
        # Add a custom handler to capture output
        log_capture = io.StringIO()
        capture_handler = logging.StreamHandler(log_capture)
        capture_handler.setLevel(logging.INFO)
        
        # Use the same formatter as the root handler
        if root_logger.handlers:
            capture_handler.setFormatter(root_logger.handlers[0].formatter)
        
        root_logger.addHandler(capture_handler)
        
        try:
            # Get a logger and log a message
            logger = get_logger("test_setup")
            logger.info("Test setup message", extra={"test_field": "test_value"})
            
            # Get the output
            log_output = log_capture.getvalue().strip()
            lines = [line for line in log_output.split('\n') if line]
            
            # Should have at least one line
            assert len(lines) >= 1
            
            # Find the line with our test message
            test_line = None
            for line in lines:
                try:
                    log_data = json.loads(line)
                    if log_data.get("message") == "Test setup message":
                        test_line = log_data
                        break
                except json.JSONDecodeError:
                    continue
            
            assert test_line is not None, "Could not find test message in logs"
            
            # Verify JSON structure
            assert "timestamp" in test_line
            assert "level" in test_line
            assert test_line["level"] == "INFO"
            assert "service" in test_line
            assert test_line["service"] == "soxauto-cpg1"
            assert test_line["message"] == "Test setup message"
            assert test_line["test_field"] == "test_value"
            
        finally:
            root_logger.removeHandler(capture_handler)
            
    finally:
        # Restore original handlers and level
        root_logger.handlers = original_handlers
        root_logger.level = original_level


def test_setup_logging_standard_format():
    """Test that setup_logging can use standard formatting."""
    # Save original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    
    try:
        # Setup standard logging
        setup_logging(level=logging.INFO, format_as_json=False)
        
        # Add a custom handler to capture output
        log_capture = io.StringIO()
        capture_handler = logging.StreamHandler(log_capture)
        capture_handler.setLevel(logging.INFO)
        
        # Use the same formatter as the root handler
        if root_logger.handlers:
            capture_handler.setFormatter(root_logger.handlers[0].formatter)
        
        root_logger.addHandler(capture_handler)
        
        try:
            # Get a logger and log a message
            logger = get_logger("test_standard")
            logger.info("Test standard message")
            
            # Get output
            log_output = log_capture.getvalue().strip()
            lines = [line for line in log_output.split('\n') if line]
            
            # Verify we have output
            assert len(lines) >= 1
            
            # Find the line with our test message
            test_line = None
            for line in lines:
                if "Test standard message" in line:
                    test_line = line
                    break
            
            assert test_line is not None, "Could not find test message in logs"
            
            # Verify it's NOT JSON (should contain hyphens from standard format)
            assert " - " in test_line
            assert "test_standard" in test_line
            assert "INFO" in test_line
            assert "Test standard message" in test_line
            
        finally:
            root_logger.removeHandler(capture_handler)
            
    finally:
        # Restore original handlers and level
        root_logger.handlers = original_handlers
        root_logger.level = original_level


def test_get_logger():
    """Test that get_logger returns a properly configured logger."""
    logger = get_logger("test_get_logger")
    
    assert logger is not None
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_get_logger"


def test_logging_levels():
    """Test that different logging levels work correctly with JSON format."""
    # Create a logger with JSON formatter
    logger = logging.getLogger("test_levels")
    logger.setLevel(logging.DEBUG)
    
    # Capture output
    log_capture = io.StringIO()
    handler = logging.StreamHandler(log_capture)
    formatter = CustomJsonFormatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Log messages at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Parse all log lines
    log_lines = log_capture.getvalue().strip().split('\n')
    assert len(log_lines) == 4
    
    # Verify each level
    levels = []
    for line in log_lines:
        log_data = json.loads(line)
        levels.append(log_data["level"])
    
    assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]
    
    # Clean up
    logger.removeHandler(handler)
