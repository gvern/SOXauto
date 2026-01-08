"""
Date normalization utilities for SOXauto PG-01.

This module provides a centralized, tested API for date parsing and normalization
across the repository. It eliminates ad-hoc date parsing logic and ensures
consistent timezone/normalization behavior.

Key Functions:
    - parse_date(): Parse various date inputs to pd.Timestamp
    - normalize_date(): Normalize to midnight (00:00:00)
    - month_start(): Get first day of month
    - month_end(): Get last day of month (handles leap years)
    - validate_yyyy_mm_dd(): Strict YYYY-MM-DD format validation

Usage Example:
    >>> from src.utils.date_utils import normalize_date, month_end
    >>> cutoff = normalize_date("2024-10-31")
    >>> print(cutoff)
    Timestamp('2024-10-31 00:00:00')
    >>> print(month_end("2024-02-10"))
    Timestamp('2024-02-29 00:00:00')
"""

from datetime import datetime, date
from typing import Union, Optional
import pandas as pd
import re


def parse_date(
    value: Union[str, date, datetime, pd.Timestamp],
    *,
    tz: Optional[str] = None
) -> pd.Timestamp:
    """
    Parse various date inputs into a pandas Timestamp.
    
    This function accepts multiple input formats and converts them to a
    standardized pd.Timestamp object. It is the foundation for all other
    date normalization functions in this module.
    
    Args:
        value: Date value to parse. Can be:
            - String in ISO format (e.g., "2024-10-31", "2024-10-31 14:30:00")
            - datetime.date object
            - datetime.datetime object
            - pd.Timestamp object
        tz: Optional timezone string (e.g., "UTC", "US/Eastern").
            If None (default), returns timezone-naive Timestamp.
    
    Returns:
        pd.Timestamp: Parsed timestamp, timezone-naive unless tz is specified
    
    Raises:
        ValueError: If the input cannot be parsed as a valid date
        TypeError: If the input type is not supported
    
    Examples:
        >>> parse_date("2024-10-31")
        Timestamp('2024-10-31 00:00:00')
        
        >>> parse_date("2024-10-31 14:30:00")
        Timestamp('2024-10-31 14:30:00')
        
        >>> from datetime import date
        >>> parse_date(date(2024, 10, 31))
        Timestamp('2024-10-31 00:00:00')
        
        >>> parse_date("2024-10-31", tz="UTC")
        Timestamp('2024-10-31 00:00:00+0000', tz='UTC')
    """
    if value is None:
        raise ValueError("Date value cannot be None")
    
    # Handle pd.Timestamp input
    if isinstance(value, pd.Timestamp):
        result = value
    # Handle datetime.datetime and datetime.date
    elif isinstance(value, (datetime, date)):
        result = pd.Timestamp(value)
    # Handle string input
    elif isinstance(value, str):
        value = value.strip()
        if not value:
            raise ValueError("Date string cannot be empty")
        try:
            result = pd.to_datetime(value)
        except Exception as e:
            raise ValueError(f"Unable to parse date string '{value}': {e}")
    else:
        raise TypeError(
            f"Unsupported date type: {type(value).__name__}. "
            f"Expected str, date, datetime, or pd.Timestamp"
        )
    
    # Apply timezone if requested
    if tz is not None:
        if result.tz is None:
            # Localize naive timestamp
            result = result.tz_localize(tz)
        else:
            # Convert timezone-aware timestamp
            result = result.tz_convert(tz)
    
    return result


def normalize_date(
    value: Union[str, date, datetime, pd.Timestamp],
    *,
    tz: Optional[str] = None
) -> pd.Timestamp:
    """
    Parse and normalize a date value to midnight (00:00:00).
    
    This function is the standard way to convert cutoff dates and reconciliation
    dates throughout the codebase. It ensures all dates are normalized to
    00:00:00 time component for consistent comparisons.
    
    Args:
        value: Date value to normalize (see parse_date for supported formats)
        tz: Optional timezone string. If None (default), returns timezone-naive.
    
    Returns:
        pd.Timestamp: Normalized timestamp at 00:00:00
    
    Raises:
        ValueError: If the input cannot be parsed as a valid date
        TypeError: If the input type is not supported
    
    Examples:
        >>> normalize_date("2024-10-31")
        Timestamp('2024-10-31 00:00:00')
        
        >>> normalize_date("2024-10-31 14:30:00")
        Timestamp('2024-10-31 00:00:00')
        
        >>> normalize_date("2024-10-31", tz="UTC")
        Timestamp('2024-10-31 00:00:00+0000', tz='UTC')
    
    Note:
        The normalize() method sets the time component to 00:00:00 while
        preserving the date and timezone information.
    """
    parsed = parse_date(value, tz=tz)
    return parsed.normalize()


def month_start(
    value: Union[str, date, datetime, pd.Timestamp]
) -> pd.Timestamp:
    """
    Get the first day of the month for a given date.
    
    Args:
        value: Date value (see parse_date for supported formats)
    
    Returns:
        pd.Timestamp: First day of the month at 00:00:00, timezone-naive
    
    Raises:
        ValueError: If the input cannot be parsed as a valid date
        TypeError: If the input type is not supported
    
    Examples:
        >>> month_start("2024-10-31")
        Timestamp('2024-10-01 00:00:00')
        
        >>> month_start("2024-02-15")
        Timestamp('2024-02-01 00:00:00')
    """
    parsed = parse_date(value)
    # Remove timezone for consistency
    if parsed.tz is not None:
        parsed = parsed.tz_localize(None)
    return parsed.replace(day=1).normalize()


def month_end(
    value: Union[str, date, datetime, pd.Timestamp]
) -> pd.Timestamp:
    """
    Get the last day of the month for a given date.
    
    This function correctly handles leap years and months with different
    numbers of days (28, 29, 30, or 31).
    
    Args:
        value: Date value (see parse_date for supported formats)
    
    Returns:
        pd.Timestamp: Last day of the month at 00:00:00, timezone-naive
    
    Raises:
        ValueError: If the input cannot be parsed as a valid date
        TypeError: If the input type is not supported
    
    Examples:
        >>> month_end("2024-02-10")  # Leap year
        Timestamp('2024-02-29 00:00:00')
        
        >>> month_end("2023-02-10")  # Non-leap year
        Timestamp('2023-02-28 00:00:00')
        
        >>> month_end("2024-10-01")
        Timestamp('2024-10-31 00:00:00')
        
        >>> month_end("2024-04-15")
        Timestamp('2024-04-30 00:00:00')
    
    Note:
        This uses pandas MonthEnd offset which correctly handles all
        edge cases including leap years.
    """
    parsed = parse_date(value)
    # Remove timezone for consistency
    if parsed.tz is not None:
        parsed = parsed.tz_localize(None)
    
    # Use pandas MonthEnd offset to get the last day of the month
    # MonthEnd(0) gives us the last day of the current month
    last_day = parsed + pd.offsets.MonthEnd(0)
    return last_day.normalize()


def validate_yyyy_mm_dd(value: str) -> None:
    """
    Validate that a string is in strict YYYY-MM-DD format.
    
    This function performs strict validation using both regex pattern matching
    and datetime parsing to ensure the date is valid. Use this for input
    validation where strict format is required (e.g., API parameters, SQL params).
    
    Args:
        value: String to validate
    
    Returns:
        None: Returns nothing if validation passes
    
    Raises:
        ValueError: If the string is not in YYYY-MM-DD format or represents
                   an invalid date (e.g., "2024-02-30")
    
    Examples:
        >>> validate_yyyy_mm_dd("2024-10-31")  # Returns None (success)
        
        >>> validate_yyyy_mm_dd("2024-02-29")  # Leap year - OK
        
        >>> validate_yyyy_mm_dd("2023-02-29")  # Not a leap year
        Traceback (most recent call last):
            ...
        ValueError: Invalid date value '2023-02-29': day is out of range for month
        
        >>> validate_yyyy_mm_dd("2024/10/31")  # Wrong separator
        Traceback (most recent call last):
            ...
        ValueError: Date string '2024/10/31' does not match YYYY-MM-DD format
        
        >>> validate_yyyy_mm_dd("24-10-31")  # 2-digit year
        Traceback (most recent call last):
            ...
        ValueError: Date string '24-10-31' does not match YYYY-MM-DD format
    
    Note:
        This function is useful for validating user input before passing
        to database queries or other critical operations.
    """
    if not isinstance(value, str):
        raise ValueError(
            f"Expected string, got {type(value).__name__}: {value}"
        )
    
    value = value.strip()
    
    # Check format with regex: YYYY-MM-DD
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, value):
        raise ValueError(
            f"Date string '{value}' does not match YYYY-MM-DD format. "
            f"Expected format: YYYY-MM-DD (e.g., '2024-10-31')"
        )
    
    # Validate it's a real date using strptime
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as e:
        raise ValueError(f"Invalid date value '{value}': {e}")


def format_yyyy_mm_dd(value: Union[str, date, datetime, pd.Timestamp]) -> str:
    """
    Format a date value as YYYY-MM-DD string.
    
    This is the inverse of parse_date, converting any date type back to
    the standard string format used throughout the codebase.
    
    Args:
        value: Date value to format (see parse_date for supported formats)
    
    Returns:
        str: Date formatted as YYYY-MM-DD
    
    Raises:
        ValueError: If the input cannot be parsed as a valid date
        TypeError: If the input type is not supported
    
    Examples:
        >>> format_yyyy_mm_dd("2024-10-31")
        '2024-10-31'
        
        >>> from datetime import date
        >>> format_yyyy_mm_dd(date(2024, 10, 31))
        '2024-10-31'
        
        >>> format_yyyy_mm_dd(pd.Timestamp("2024-10-31 14:30:00"))
        '2024-10-31'
    """
    parsed = parse_date(value)
    return parsed.strftime('%Y-%m-%d')


__all__ = [
    'parse_date',
    'normalize_date',
    'month_start',
    'month_end',
    'validate_yyyy_mm_dd',
    'format_yyyy_mm_dd',
]
