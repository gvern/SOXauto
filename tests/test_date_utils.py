"""
Unit tests for centralized date normalization utilities (src/utils/date_utils.py).

These tests verify:
1. Parsing various date input formats
2. Normalization to midnight (00:00:00)
3. Month start/end calculations (including leap years)
4. Strict YYYY-MM-DD validation
5. Error handling for invalid inputs

Run with: pytest tests/test_date_utils.py -v
"""

import os
import sys
from datetime import date, datetime

import pandas as pd
import pytest

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.utils.date_utils import (
    parse_date,
    normalize_date,
    month_start,
    month_end,
    validate_yyyy_mm_dd,
    format_yyyy_mm_dd,
)


class TestParseDate:
    """Tests for parse_date() function."""
    
    def test_parse_string_date(self):
        """Test parsing string dates in YYYY-MM-DD format."""
        result = parse_date("2024-10-31")
        assert isinstance(result, pd.Timestamp)
        assert result == pd.Timestamp("2024-10-31")
    
    def test_parse_string_datetime(self):
        """Test parsing string with time component."""
        result = parse_date("2024-10-31 14:30:00")
        assert result == pd.Timestamp("2024-10-31 14:30:00")
    
    def test_parse_date_object(self):
        """Test parsing datetime.date object."""
        input_date = date(2024, 10, 31)
        result = parse_date(input_date)
        assert result == pd.Timestamp("2024-10-31")
    
    def test_parse_datetime_object(self):
        """Test parsing datetime.datetime object."""
        input_dt = datetime(2024, 10, 31, 14, 30, 0)
        result = parse_date(input_dt)
        assert result == pd.Timestamp("2024-10-31 14:30:00")
    
    def test_parse_timestamp(self):
        """Test parsing pd.Timestamp (passthrough)."""
        input_ts = pd.Timestamp("2024-10-31")
        result = parse_date(input_ts)
        assert result == input_ts
    
    def test_parse_with_timezone(self):
        """Test parsing with timezone parameter."""
        result = parse_date("2024-10-31", tz="UTC")
        assert result.tz is not None
        assert str(result.tz) == "UTC"
    
    def test_parse_empty_string_raises_error(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            parse_date("")
    
    def test_parse_none_raises_error(self):
        """Test that None raises ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            parse_date(None)
    
    def test_parse_invalid_string_raises_error(self):
        """Test that invalid date string raises ValueError."""
        with pytest.raises(ValueError, match="Unable to parse"):
            parse_date("not-a-date")
    
    def test_parse_unsupported_type_raises_error(self):
        """Test that unsupported type raises TypeError."""
        with pytest.raises(TypeError, match="Unsupported date type"):
            parse_date(12345)


class TestNormalizeDate:
    """Tests for normalize_date() function."""
    
    def test_normalize_date_only(self):
        """Test normalizing a date string (already at midnight)."""
        result = normalize_date("2024-10-31")
        assert result == pd.Timestamp("2024-10-31 00:00:00")
    
    def test_normalize_datetime_with_time(self):
        """Test normalizing a datetime with non-zero time component."""
        result = normalize_date("2024-10-31 14:30:45")
        assert result == pd.Timestamp("2024-10-31 00:00:00")
        # Verify time component is zeroed
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
    
    def test_normalize_preserves_date(self):
        """Test that only time is normalized, date is preserved."""
        result = normalize_date("2023-02-28 23:59:59")
        assert result == pd.Timestamp("2023-02-28 00:00:00")
    
    def test_normalize_with_timezone(self):
        """Test normalizing with timezone."""
        result = normalize_date("2024-10-31 14:30:00", tz="UTC")
        assert result == pd.Timestamp("2024-10-31 00:00:00", tz="UTC")
    
    def test_normalize_various_input_types(self):
        """Test that normalize_date works with various input types."""
        inputs = [
            "2024-10-31",
            date(2024, 10, 31),
            datetime(2024, 10, 31, 14, 30),
            pd.Timestamp("2024-10-31 14:30:00"),
        ]
        expected = pd.Timestamp("2024-10-31 00:00:00")
        
        for input_val in inputs:
            result = normalize_date(input_val)
            assert result == expected


class TestMonthStart:
    """Tests for month_start() function."""
    
    def test_month_start_from_mid_month(self):
        """Test getting first day from middle of month."""
        result = month_start("2024-10-15")
        assert result == pd.Timestamp("2024-10-01 00:00:00")
    
    def test_month_start_from_last_day(self):
        """Test getting first day from last day of month."""
        result = month_start("2024-10-31")
        assert result == pd.Timestamp("2024-10-01 00:00:00")
    
    def test_month_start_from_first_day(self):
        """Test getting first day when input is already first day."""
        result = month_start("2024-10-01")
        assert result == pd.Timestamp("2024-10-01 00:00:00")
    
    def test_month_start_february_leap_year(self):
        """Test month start for February in leap year."""
        result = month_start("2024-02-29")
        assert result == pd.Timestamp("2024-02-01 00:00:00")
    
    def test_month_start_december(self):
        """Test month start for December (year boundary)."""
        result = month_start("2024-12-31")
        assert result == pd.Timestamp("2024-12-01 00:00:00")


class TestMonthEnd:
    """Tests for month_end() function."""
    
    def test_month_end_october(self):
        """Test last day of October (31 days)."""
        result = month_end("2024-10-01")
        assert result == pd.Timestamp("2024-10-31 00:00:00")
    
    def test_month_end_april(self):
        """Test last day of April (30 days)."""
        result = month_end("2024-04-15")
        assert result == pd.Timestamp("2024-04-30 00:00:00")
    
    def test_month_end_february_leap_year(self):
        """Test last day of February in leap year (29 days)."""
        result = month_end("2024-02-10")
        assert result == pd.Timestamp("2024-02-29 00:00:00")
    
    def test_month_end_february_non_leap_year(self):
        """Test last day of February in non-leap year (28 days)."""
        result = month_end("2023-02-10")
        assert result == pd.Timestamp("2023-02-28 00:00:00")
    
    def test_month_end_from_last_day(self):
        """Test month_end when input is already last day."""
        result = month_end("2024-10-31")
        assert result == pd.Timestamp("2024-10-31 00:00:00")
    
    def test_month_end_december(self):
        """Test last day of December (year boundary)."""
        result = month_end("2024-12-15")
        assert result == pd.Timestamp("2024-12-31 00:00:00")
    
    def test_month_end_all_months_2024(self):
        """Test month_end for all months in 2024 (leap year)."""
        expected_days = {
            1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
        }
        
        for month, expected_day in expected_days.items():
            input_date = f"2024-{month:02d}-15"
            result = month_end(input_date)
            assert result.day == expected_day, f"Month {month} should end on day {expected_day}"
            assert result.month == month
            assert result.year == 2024


class TestValidateYyyyMmDd:
    """Tests for validate_yyyy_mm_dd() function."""
    
    def test_validate_valid_date(self):
        """Test validation passes for valid YYYY-MM-DD date."""
        # Should not raise exception
        validate_yyyy_mm_dd("2024-10-31")
    
    def test_validate_leap_year_date(self):
        """Test validation passes for leap year date."""
        validate_yyyy_mm_dd("2024-02-29")
    
    def test_validate_invalid_separator(self):
        """Test validation fails for wrong separator."""
        with pytest.raises(ValueError, match="does not match YYYY-MM-DD format"):
            validate_yyyy_mm_dd("2024/10/31")
    
    def test_validate_two_digit_year(self):
        """Test validation fails for 2-digit year."""
        with pytest.raises(ValueError, match="does not match YYYY-MM-DD format"):
            validate_yyyy_mm_dd("24-10-31")
    
    def test_validate_invalid_month(self):
        """Test validation fails for invalid month."""
        with pytest.raises(ValueError, match="Invalid date value"):
            validate_yyyy_mm_dd("2024-13-01")
    
    def test_validate_invalid_day(self):
        """Test validation fails for invalid day."""
        with pytest.raises(ValueError, match="Invalid date value"):
            validate_yyyy_mm_dd("2024-10-32")
    
    def test_validate_february_non_leap_year(self):
        """Test validation fails for Feb 29 in non-leap year."""
        with pytest.raises(ValueError, match="Invalid date value"):
            validate_yyyy_mm_dd("2023-02-29")
    
    def test_validate_april_31(self):
        """Test validation fails for April 31 (only 30 days)."""
        with pytest.raises(ValueError, match="Invalid date value"):
            validate_yyyy_mm_dd("2024-04-31")
    
    def test_validate_non_string_input(self):
        """Test validation fails for non-string input."""
        with pytest.raises(ValueError, match="Expected string"):
            validate_yyyy_mm_dd(20241031)
    
    def test_validate_empty_string(self):
        """Test validation fails for empty string."""
        with pytest.raises(ValueError, match="does not match YYYY-MM-DD format"):
            validate_yyyy_mm_dd("")
    
    def test_validate_with_time_component(self):
        """Test validation fails when time component is included."""
        with pytest.raises(ValueError, match="does not match YYYY-MM-DD format"):
            validate_yyyy_mm_dd("2024-10-31 14:30:00")


class TestFormatYyyyMmDd:
    """Tests for format_yyyy_mm_dd() function."""
    
    def test_format_string_date(self):
        """Test formatting from string date."""
        result = format_yyyy_mm_dd("2024-10-31")
        assert result == "2024-10-31"
    
    def test_format_datetime_with_time(self):
        """Test formatting strips time component."""
        result = format_yyyy_mm_dd("2024-10-31 14:30:00")
        assert result == "2024-10-31"
    
    def test_format_date_object(self):
        """Test formatting from date object."""
        result = format_yyyy_mm_dd(date(2024, 10, 31))
        assert result == "2024-10-31"
    
    def test_format_datetime_object(self):
        """Test formatting from datetime object."""
        result = format_yyyy_mm_dd(datetime(2024, 10, 31, 14, 30))
        assert result == "2024-10-31"
    
    def test_format_timestamp(self):
        """Test formatting from pd.Timestamp."""
        result = format_yyyy_mm_dd(pd.Timestamp("2024-10-31 14:30:00"))
        assert result == "2024-10-31"
    
    def test_format_preserves_leading_zeros(self):
        """Test that single-digit months/days have leading zeros."""
        result = format_yyyy_mm_dd("2024-01-05")
        assert result == "2024-01-05"


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_year_boundary_december_to_january(self):
        """Test month calculations across year boundary."""
        # December month start
        result = month_start("2024-12-31")
        assert result == pd.Timestamp("2024-12-01 00:00:00")
        
        # December month end
        result = month_end("2024-12-01")
        assert result == pd.Timestamp("2024-12-31 00:00:00")
    
    def test_century_leap_year_2000(self):
        """Test leap year calculation for century year 2000 (was leap year)."""
        result = month_end("2000-02-15")
        assert result == pd.Timestamp("2000-02-29 00:00:00")
    
    def test_century_non_leap_year_1900(self):
        """Test leap year calculation for century year 1900 (not leap year)."""
        result = month_end("1900-02-15")
        assert result == pd.Timestamp("1900-02-28 00:00:00")
    
    def test_normalize_preserves_timezone_naive(self):
        """Test that normalized dates remain timezone-naive by default."""
        result = normalize_date("2024-10-31")
        assert result.tz is None
    
    def test_month_functions_remove_timezone(self):
        """Test that month_start and month_end return timezone-naive results."""
        # Even if we parse with timezone, month functions should be naive
        input_with_tz = pd.Timestamp("2024-10-31", tz="UTC")
        
        result_start = month_start(input_with_tz)
        assert result_start.tz is None
        
        result_end = month_end(input_with_tz)
        assert result_end.tz is None


class TestIntegrationScenarios:
    """Integration tests simulating real-world usage patterns."""
    
    def test_cutoff_date_workflow(self):
        """Test typical cutoff date processing workflow."""
        cutoff_date_str = "2024-09-30"
        
        # Validate input
        validate_yyyy_mm_dd(cutoff_date_str)
        
        # Normalize for processing
        cutoff = normalize_date(cutoff_date_str)
        assert cutoff == pd.Timestamp("2024-09-30 00:00:00")
        
        # Get month boundaries
        start = month_start(cutoff)
        end = month_end(cutoff)
        
        assert start == pd.Timestamp("2024-09-01 00:00:00")
        assert end == pd.Timestamp("2024-09-30 00:00:00")
    
    def test_rolling_window_calculation(self):
        """Test calculating a rolling 1-year window (like timing.py)."""
        cutoff_date = "2025-09-30"
        
        cutoff_dt = normalize_date(cutoff_date)
        
        # Calculate start date: 1st of (cutoff_month + 1) - 1 year
        # This mimics the logic in timing.py
        next_month_first = (cutoff_dt.replace(day=1) + pd.DateOffset(months=1))
        start_dt = next_month_first - pd.DateOffset(years=1)
        
        assert start_dt == pd.Timestamp("2024-10-01 00:00:00")
        assert cutoff_dt == pd.Timestamp("2025-09-30 00:00:00")
    
    def test_reconciliation_month_window(self):
        """Test calculating reconciliation month window (like vtc.py)."""
        cutoff_date = "2024-09-30"
        
        cutoff_dt = normalize_date(cutoff_date)
        month_start_dt = month_start(cutoff_dt)
        month_end_dt = month_end(cutoff_dt)
        
        # Verify window bounds
        assert month_start_dt == pd.Timestamp("2024-09-01 00:00:00")
        assert month_end_dt == pd.Timestamp("2024-09-30 00:00:00")
        
        # Verify filtering logic would work
        test_date_in_range = pd.Timestamp("2024-09-15")
        assert month_start_dt <= test_date_in_range <= month_end_dt
        
        test_date_before = pd.Timestamp("2024-08-31")
        assert not (month_start_dt <= test_date_before <= month_end_dt)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
