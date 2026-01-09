"""
Data Quality Checker Module

Provides a reusable framework for automating data validation checks on extracted DataFrames.
This implements the CFO's request for standardized "Data Checks" across all processes.

New: Integrates with schema contract system to auto-generate quality rules from contracts.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from abc import ABC, abstractmethod
from datetime import datetime
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
            return (
                False,
                f"ColumnExistsCheck: FAIL (column '{self.column_name}' not found. "
                f"Available: {available_cols})"
            )

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
                    return (
                        True,
                        f"NumericSumCheck: PASS (sum of '{self.column_name}' is {column_sum}, "
                        f"expected non-zero)"
                    )
                else:
                    return (
                        False,
                        f"NumericSumCheck: FAIL (sum of '{self.column_name}' is 0, expected non-zero)"
                    )
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
            return (
                False,
                f"NoNullsCheck: FAIL (column '{self.column_name}' has {null_count} null values "
                f"out of {total_rows} rows)"
            )

    def get_name(self) -> str:
        return "NoNullsCheck"


@dataclass
class DTypeCheck(QualityRule):
    """Check that a column has the expected data type."""
    column_name: str
    expected_dtype: str  # "int64", "float64", "object", "datetime64[ns]", etc.
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name not in df.columns:
            return False, f"DTypeCheck: FAIL (column '{self.column_name}' not found)"
        
        actual_dtype = str(df[self.column_name].dtype)
        
        # Normalize dtype strings for comparison
        expected_normalized = self._normalize_dtype(self.expected_dtype)
        actual_normalized = self._normalize_dtype(actual_dtype)
        
        if expected_normalized == actual_normalized:
            return True, f"DTypeCheck: PASS (column '{self.column_name}' is {actual_dtype})"
        else:
            return False, (
                f"DTypeCheck: FAIL (column '{self.column_name}' is {actual_dtype}, "
                f"expected {self.expected_dtype})"
            )
    
    def _normalize_dtype(self, dtype: str) -> str:
        """Normalize dtype string for flexible comparison."""
        dtype_lower = dtype.lower()
        
        # Map common variations
        if "int" in dtype_lower:
            return "integer"
        elif "float" in dtype_lower or "double" in dtype_lower:
            return "float"
        elif "datetime" in dtype_lower or "timestamp" in dtype_lower:
            return "datetime"
        elif "object" in dtype_lower or "string" in dtype_lower:
            return "string"
        elif "bool" in dtype_lower:
            return "boolean"
        
        return dtype_lower
    
    def get_name(self) -> str:
        return "DTypeCheck"


@dataclass
class DateRangeCheck(QualityRule):
    """Check that date column values fall within specified range."""
    column_name: str
    min_date: Optional[datetime] = None
    max_date: Optional[datetime] = None
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name not in df.columns:
            return False, f"DateRangeCheck: FAIL (column '{self.column_name}' not found)"
        
        # Convert to datetime if not already
        try:
            col = pd.to_datetime(df[self.column_name], errors='coerce')
        except Exception as e:
            return False, f"DateRangeCheck: FAIL (cannot convert '{self.column_name}' to datetime: {e})"
        
        # Filter out NaT (missing dates)
        valid_dates = col.dropna()
        
        if len(valid_dates) == 0:
            return False, f"DateRangeCheck: FAIL (column '{self.column_name}' has no valid dates)"
        
        # Check min date
        if self.min_date is not None:
            min_date_pd = pd.Timestamp(self.min_date)
            violations_min = (valid_dates < min_date_pd).sum()
            if violations_min > 0:
                earliest = valid_dates.min()
                return False, (
                    f"DateRangeCheck: FAIL (column '{self.column_name}' has {violations_min} "
                    f"dates before {self.min_date.date()}, earliest: {earliest.date()})"
                )
        
        # Check max date
        if self.max_date is not None:
            max_date_pd = pd.Timestamp(self.max_date)
            violations_max = (valid_dates > max_date_pd).sum()
            if violations_max > 0:
                latest = valid_dates.max()
                return False, (
                    f"DateRangeCheck: FAIL (column '{self.column_name}' has {violations_max} "
                    f"dates after {self.max_date.date()}, latest: {latest.date()})"
                )
        
        # All checks passed
        date_range_str = f"{valid_dates.min().date()} to {valid_dates.max().date()}"
        constraint_str = ""
        if self.min_date:
            constraint_str += f" >= {self.min_date.date()}"
        if self.max_date:
            constraint_str += f" <= {self.max_date.date()}" if constraint_str else f"<= {self.max_date.date()}"
        
        return True, (
            f"DateRangeCheck: PASS (column '{self.column_name}' range {date_range_str}"
            f"{', within constraints' + constraint_str if constraint_str else ''})"
        )
    
    def get_name(self) -> str:
        return "DateRangeCheck"


@dataclass
class SemanticValidityCheck(QualityRule):
    """Check that a column conforms to its semantic type (amount, id, code, etc.)."""
    column_name: str
    semantic_tag: str  # "amount", "id", "code", "date", etc.
    
    def check(self, df: pd.DataFrame) -> tuple[bool, str]:
        if self.column_name not in df.columns:
            return False, f"SemanticValidityCheck: FAIL (column '{self.column_name}' not found)"
        
        col = df[self.column_name]
        
        if self.semantic_tag == "amount":
            # Check that numeric amounts are reasonable
            try:
                numeric_col = pd.to_numeric(col, errors='coerce')
                valid_count = numeric_col.notna().sum()
                total_count = len(col)
                
                if valid_count == 0:
                    return False, f"SemanticValidityCheck: FAIL ('{self.column_name}' has no valid numeric amounts)"
                
                valid_pct = (valid_count / total_count) * 100
                if valid_pct < 95:  # Require at least 95% valid
                    return False, (
                        f"SemanticValidityCheck: FAIL ('{self.column_name}' only {valid_pct:.1f}% "
                        f"valid numeric amounts, expected >= 95%)"
                    )
                
                return True, (
                    f"SemanticValidityCheck: PASS ('{self.column_name}' is {valid_pct:.1f}% "
                    f"valid numeric amounts)"
                )
            except Exception as e:
                return False, f"SemanticValidityCheck: FAIL ('{self.column_name}' amount validation error: {e})"
        
        elif self.semantic_tag == "id" or self.semantic_tag == "key":
            # Check that IDs/keys are non-null and mostly unique
            null_count = col.isnull().sum()
            total_count = len(col)
            
            if null_count > 0:
                null_pct = (null_count / total_count) * 100
                if null_pct > 5:  # Allow up to 5% nulls
                    return False, (
                        f"SemanticValidityCheck: FAIL ('{self.column_name}' has {null_pct:.1f}% "
                        f"null IDs, expected <= 5%)"
                    )
            
            # Check uniqueness
            unique_count = col.nunique()
            uniqueness_pct = (unique_count / total_count) * 100 if total_count > 0 else 0
            
            return True, (
                f"SemanticValidityCheck: PASS ('{self.column_name}' has {uniqueness_pct:.1f}% "
                f"unique values, {null_count} nulls)"
            )
        
        elif self.semantic_tag == "date":
            # Check that dates are parseable
            try:
                date_col = pd.to_datetime(col, errors='coerce')
                valid_count = date_col.notna().sum()
                total_count = len(col)
                
                if valid_count == 0:
                    return False, f"SemanticValidityCheck: FAIL ('{self.column_name}' has no valid dates)"
                
                valid_pct = (valid_count / total_count) * 100
                if valid_pct < 95:
                    return False, (
                        f"SemanticValidityCheck: FAIL ('{self.column_name}' only {valid_pct:.1f}% "
                        f"valid dates, expected >= 95%)"
                    )
                
                return True, (
                    f"SemanticValidityCheck: PASS ('{self.column_name}' is {valid_pct:.1f}% valid dates)"
                )
            except Exception as e:
                return False, f"SemanticValidityCheck: FAIL ('{self.column_name}' date validation error: {e})"
        
        else:
            # Generic check - just ensure column is not entirely null
            null_count = col.isnull().sum()
            total_count = len(col)
            null_pct = (null_count / total_count) * 100 if total_count > 0 else 0
            
            if null_pct >= 100:
                return False, f"SemanticValidityCheck: FAIL ('{self.column_name}' is entirely null)"
            
            return True, (
                f"SemanticValidityCheck: PASS ('{self.column_name}' semantic:{self.semantic_tag}, "
                f"{null_pct:.1f}% null)"
            )
    
    def get_name(self) -> str:
        return "SemanticValidityCheck"


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


def build_quality_rules_from_schema(contract: Any, include_semantic: bool = True) -> List[QualityRule]:
    """
    Auto-generate quality rules from a SchemaContract.
    
    Generates rules based on:
    - Required columns (ColumnExistsCheck)
    - Data types (DTypeCheck)
    - Semantic tags (SemanticValidityCheck)
    - Validation rules from contract (DateRangeCheck, etc.)
    
    Args:
        contract: SchemaContract instance (imported from src.core.schema.models)
        include_semantic: Whether to include semantic validity checks
    
    Returns:
        List of QualityRule instances
    
    Example:
        >>> from src.core.schema import load_contract
        >>> contract = load_contract("IPE_07")
        >>> rules = build_quality_rules_from_schema(contract)
        >>> engine = DataQualityEngine()
        >>> report = engine.run_checks(df, rules)
    """
    rules: List[QualityRule] = []
    
    for field in contract.fields:
        # Required column check
        if field.required:
            rules.append(ColumnExistsCheck(column_name=field.name))
        
        # Data type check
        if field.dtype:
            rules.append(DTypeCheck(column_name=field.name, expected_dtype=field.dtype))
        
        # Semantic validity check
        if include_semantic and field.semantic_tag and field.semantic_tag.value != "other":
            rules.append(SemanticValidityCheck(
                column_name=field.name,
                semantic_tag=field.semantic_tag.value
            ))
        
        # Date range check from validation_rules
        if "min_date" in field.validation_rules or "max_date" in field.validation_rules:
            min_date = field.validation_rules.get("min_date")
            max_date = field.validation_rules.get("max_date")
            
            # Convert string dates to datetime if needed
            if isinstance(min_date, str):
                min_date = datetime.fromisoformat(min_date)
            if isinstance(max_date, str):
                max_date = datetime.fromisoformat(max_date)
            
            rules.append(DateRangeCheck(
                column_name=field.name,
                min_date=min_date,
                max_date=max_date
            ))
        
        # No nulls check for critical fields
        if field.reconciliation_critical and field.required:
            rules.append(NoNullsCheck(column_name=field.name))
    
    return rules

