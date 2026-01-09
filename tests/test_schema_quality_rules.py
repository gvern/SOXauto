"""
Tests for schema-driven quality rules integration.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

from src.core.quality_checker import (
    DTypeCheck,
    DateRangeCheck,
    SemanticValidityCheck,
    DataQualityEngine,
    build_quality_rules_from_schema
)
from src.core.schema import load_contract


class TestDTypeCheck:
    """Test DTypeCheck quality rule."""
    
    def test_dtype_check_passes(self):
        df = pd.DataFrame({
            "amount": [100.0, 200.5, 300.75],
            "id": ["A001", "A002", "A003"]
        })
        
        rule = DTypeCheck(column_name="amount", expected_dtype="float64")
        passed, message = rule.check(df)
        
        assert passed
        assert "PASS" in message
    
    def test_dtype_check_fails(self):
        df = pd.DataFrame({
            "amount": ["100", "200", "300"],  # strings, not floats
        })
        
        rule = DTypeCheck(column_name="amount", expected_dtype="float64")
        passed, message = rule.check(df)
        
        assert not passed
        assert "FAIL" in message
        assert "object" in message  # pandas dtype for strings


class TestDateRangeCheck:
    """Test DateRangeCheck quality rule."""
    
    def test_date_range_check_passes(self):
        df = pd.DataFrame({
            "date_col": pd.date_range("2025-01-01", periods=10, freq="D")
        })
        
        rule = DateRangeCheck(
            column_name="date_col",
            min_date=datetime(2025, 1, 1),
            max_date=datetime(2025, 12, 31)
        )
        passed, message = rule.check(df)
        
        assert passed
        assert "PASS" in message
    
    def test_date_range_check_fails_min(self):
        df = pd.DataFrame({
            "date_col": pd.date_range("2024-01-01", periods=10, freq="D")
        })
        
        rule = DateRangeCheck(
            column_name="date_col",
            min_date=datetime(2025, 1, 1)
        )
        passed, message = rule.check(df)
        
        assert not passed
        assert "FAIL" in message
        assert "before" in message
    
    def test_date_range_check_fails_max(self):
        df = pd.DataFrame({
            "date_col": pd.date_range("2026-01-01", periods=10, freq="D")
        })
        
        rule = DateRangeCheck(
            column_name="date_col",
            max_date=datetime(2025, 12, 31)
        )
        passed, message = rule.check(df)
        
        assert not passed
        assert "FAIL" in message
        assert "after" in message


class TestSemanticValidityCheck:
    """Test SemanticValidityCheck quality rule."""
    
    def test_amount_semantic_check_passes(self):
        df = pd.DataFrame({
            "amount": [100.0, 200.5, 300.75, 400.00]
        })
        
        rule = SemanticValidityCheck(column_name="amount", semantic_tag="amount")
        passed, message = rule.check(df)
        
        assert passed
        assert "PASS" in message
        assert "100.0%" in message  # All valid
    
    def test_amount_semantic_check_fails(self):
        df = pd.DataFrame({
            "amount": ["invalid", "data", "here", "oops"]
        })
        
        rule = SemanticValidityCheck(column_name="amount", semantic_tag="amount")
        passed, message = rule.check(df)
        
        assert not passed
        assert "FAIL" in message
    
    def test_id_semantic_check_passes(self):
        df = pd.DataFrame({
            "customer_id": ["C001", "C002", "C003", "C004", "C005"]
        })
        
        rule = SemanticValidityCheck(column_name="customer_id", semantic_tag="id")
        passed, message = rule.check(df)
        
        assert passed
        assert "PASS" in message
    
    def test_date_semantic_check_passes(self):
        df = pd.DataFrame({
            "posting_date": pd.date_range("2025-01-01", periods=5, freq="D")
        })
        
        rule = SemanticValidityCheck(column_name="posting_date", semantic_tag="date")
        passed, message = rule.check(df)
        
        assert passed
        assert "PASS" in message


class TestSchemaIntegration:
    """Test auto-generation of quality rules from schema contracts."""
    
    def test_build_rules_from_contract(self):
        contract = load_contract("IPE_07")
        
        rules = build_quality_rules_from_schema(contract, include_semantic=True)
        
        # Should have rules for required columns, dtypes, and semantic checks
        assert len(rules) > 0
        
        # Check for specific rule types
        rule_types = [type(r).__name__ for r in rules]
        assert "ColumnExistsCheck" in rule_types
        assert "DTypeCheck" in rule_types
        assert "SemanticValidityCheck" in rule_types
    
    def test_quality_engine_with_schema_rules(self):
        """Integration test: load contract, generate rules, validate data."""
        contract = load_contract("JDASH")
        
        # Create sample data matching JDASH contract
        df = pd.DataFrame({
            "voucher_id": ["V001", "V002", "V003"],
            "amount_used": [50.0, 75.5, 100.25],
            "usage_date": pd.date_range("2025-09-01", periods=3, freq="D"),
            "order_id": ["O001", "O002", "O003"],
            "customer_id": ["C001", "C002", "C003"],
            "status": ["completed", "completed", "pending"]
        })
        
        # Generate rules from contract
        rules = build_quality_rules_from_schema(contract)
        
        # Run quality checks
        engine = DataQualityEngine()
        report = engine.run_checks(df, rules)
        
        # Should pass since data matches contract
        assert report.status == "PASS"
        assert len(report.details) > 0
