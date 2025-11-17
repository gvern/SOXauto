"""
Data Quality Checker Module

Provides a reusable framework for automating data validation checks on extracted DataFrames.
This implements the CFO's request for standardized "Data Checks" across all processes.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod
import pandas as pd


@dataclass
class QualityRule(ABC):
    """Base class for data quality rules."""
    
    @abstractmethod
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        """
        Execute the quality check on a DataFrame.
        
        Args:
            df: The DataFrame to check
            
        Returns:
            Tuple of (pass/fail bool, detail message string)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return a human-readable name for this rule."""
        pass


@dataclass
class RowCountCheck(QualityRule):
    """Check that DataFrame has a row count within specified bounds."""
    min_rows: int
    max_rows: Optional[int] = None
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        row_count = len(df)
        
        if row_count < self.min_rows:
            return False, f"RowCountCheck: FAIL ({row_count} rows, expected >= {self.min_rows})"
        
        if self.max_rows is not None and row_count > self.max_rows:
            return False, f"RowCountCheck: FAIL ({row_count} rows, expected <= {self.max_rows})"
        
        max_msg = f", <= {self.max_rows}" if self.max_rows is not None else ""
        return True, f"RowCountCheck: PASS ({row_count} rows, expected >= {self.min_rows}{max_msg})"
    
    def get_name(self) -> str:
        return "RowCountCheck"


@dataclass
class ColumnExistsCheck(QualityRule):
    """Check that a specified column exists in the DataFrame."""
    column_name: str
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name in df.columns:
            return True, f"ColumnExistsCheck: PASS (column '{self.column_name}' exists)"
        else:
            available_cols = ", ".join(df.columns.tolist()[:5])
            if len(df.columns) > 5:
                available_cols += "..."
            return False, f"ColumnExistsCheck: FAIL (column '{self.column_name}' not found. Available: {available_cols})"
    
    def get_name(self) -> str:
        return "ColumnExistsCheck"


@dataclass
class NumericSumCheck(QualityRule):
    """Check that the sum of a numeric column meets a condition."""
    column_name: str
    should_be_zero: bool
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name not in df.columns:
            return False, f"NumericSumCheck: FAIL (column '{self.column_name}' not found)"
        
        try:
            column_sum = df[self.column_name].sum()
            
            if self.should_be_zero:
                if column_sum == 0:
                    return True, f"NumericSumCheck: PASS (sum of '{self.column_name}' is 0)"
                else:
                    return False, f"NumericSumCheck: FAIL (sum of '{self.column_name}' is {column_sum}, expected 0)"
            else:
                if column_sum != 0:
                    return True, f"NumericSumCheck: PASS (sum of '{self.column_name}' is {column_sum}, expected non-zero)"
                else:
                    return False, f"NumericSumCheck: FAIL (sum of '{self.column_name}' is 0, expected non-zero)"
        except (TypeError, ValueError) as e:
            return False, f"NumericSumCheck: FAIL (column '{self.column_name}' is not numeric: {e})"
    
    def get_name(self) -> str:
        return "NumericSumCheck"


@dataclass
class NoNullsCheck(QualityRule):
    """Check that a column contains no null values."""
    column_name: str
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name not in df.columns:
            return False, f"NoNullsCheck: FAIL (column '{self.column_name}' not found)"
        
        null_count = df[self.column_name].isnull().sum()
        
        if null_count == 0:
            return True, f"NoNullsCheck: PASS (column '{self.column_name}' has no nulls)"
        else:
            total_rows = len(df)
            return False, f"NoNullsCheck: FAIL (column '{self.column_name}' has {null_count} null values out of {total_rows} rows)"
    
    def get_name(self) -> str:
        return "NoNullsCheck"


@dataclass
class QualityReport:
    """Container for quality check results."""
    status: str  # "PASS" or "FAIL"
    details: List[str] = field(default_factory=list)
    
    def __str__(self) -> str:
        """Return a human-readable report."""
        lines = [f"Quality Report: {self.status}"]
        lines.append("-" * 50)
        for detail in self.details:
            lines.append(f"  {detail}")
        return "\n".join(lines)


class DataQualityEngine:
    """Engine for running data quality checks on DataFrames."""
    
    def run_checks(self, df: pd.DataFrame, rules: List[QualityRule]) -> QualityReport:
        """
        Run all quality checks on the provided DataFrame.
        
        Args:
            df: DataFrame to validate
            rules: List of QualityRule instances to apply
            
        Returns:
            QualityReport with overall status and detailed results
        """
        if not rules:
            return QualityReport(status="PASS", details=["No rules to check"])
        
        details = []
        all_passed = True
        
        for rule in rules:
            passed, message = rule.check(df)
            details.append(message)
            if not passed:
                all_passed = False
        
        status = "PASS" if all_passed else "FAIL"
        return QualityReport(status=status, details=details)
