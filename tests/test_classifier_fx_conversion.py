"""
Tests for FX conversion integration in bridge classifier functions.

Tests that classifier functions correctly use FXConverter to report amounts in USD.
"""

import os
import sys
import pandas as pd
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from src.bridges.classifier import (
    calculate_vtc_adjustment,
    _categorize_nav_vouchers,
    calculate_timing_difference_bridge,
    calculate_integration_error_adjustment,
)
from src.utils.fx_utils import FXConverter


# ========================================================================
# Tests for calculate_vtc_adjustment with FX conversion
# ========================================================================


def test_calculate_vtc_adjustment_with_fx_conversion():
    """Test VTC adjustment with FX conversion to USD."""
    # Create FX rates
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG'],
        'FX_rate': [15.5, 4.0]
    })
    fx_converter = FXConverter(cr05_df)
    
    # Create IPE_08 data with canceled refund vouchers in different currencies
    ipe_08_df = pd.DataFrame([
        {
            "id": "V001",
            "business_use_formatted": "refund",
            "Is_Valid": "valid",
            "is_active": 0,
            "remaining_amount": 1550.0,  # 1550 GHS = 100 USD
            "ID_COMPANY": "JD_GH"
        },
        {
            "id": "V002",
            "business_use_formatted": "refund",
            "Is_Valid": "valid",
            "is_active": 0,
            "remaining_amount": 400.0,  # 400 NGN = 100 USD
            "ID_COMPANY": "EC_NG"
        },
    ])
    
    # No cancellations in NAV, so all vouchers unmatched
    cr_03_df = pd.DataFrame()
    
    adjustment_amount, proof_df = calculate_vtc_adjustment(
        ipe_08_df, cr_03_df, fx_converter=fx_converter
    )
    
    # Should convert to USD: 100 + 100 = 200
    assert adjustment_amount == pytest.approx(200.0, rel=1e-6)
    assert 'Amount_USD' in proof_df.columns
    assert len(proof_df) == 2


def test_calculate_vtc_adjustment_without_fx_conversion():
    """Test VTC adjustment without FX converter (local currency)."""
    ipe_08_df = pd.DataFrame([
        {
            "id": "V001",
            "business_use_formatted": "refund",
            "Is_Valid": "valid",
            "is_active": 0,
            "remaining_amount": 1550.0,
            "ID_COMPANY": "JD_GH"
        },
        {
            "id": "V002",
            "business_use_formatted": "refund",
            "Is_Valid": "valid",
            "is_active": 0,
            "remaining_amount": 400.0,
            "ID_COMPANY": "EC_NG"
        },
    ])
    
    cr_03_df = pd.DataFrame()
    
    # Call without FX converter
    adjustment_amount, proof_df = calculate_vtc_adjustment(
        ipe_08_df, cr_03_df, fx_converter=None
    )
    
    # Should use local currency: 1550 + 400 = 1950
    assert adjustment_amount == pytest.approx(1950.0, rel=1e-6)
    assert 'Amount_USD' not in proof_df.columns


def test_calculate_vtc_adjustment_fx_missing_company_column():
    """Test VTC adjustment when company column is missing but FX converter provided."""
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    fx_converter = FXConverter(cr05_df)
    
    # Create data without ID_COMPANY column
    ipe_08_df = pd.DataFrame([
        {
            "id": "V001",
            "business_use_formatted": "refund",
            "Is_Valid": "valid",
            "is_active": 0,
            "remaining_amount": 1550.0,
            # No ID_COMPANY column
        },
    ])
    
    cr_03_df = pd.DataFrame()
    
    # Should fall back to local currency
    adjustment_amount, proof_df = calculate_vtc_adjustment(
        ipe_08_df, cr_03_df, fx_converter=fx_converter
    )
    
    assert adjustment_amount == pytest.approx(1550.0, rel=1e-6)


# ========================================================================
# Tests for calculate_timing_difference_bridge with FX conversion
# ========================================================================


def test_calculate_timing_difference_bridge_with_fx_conversion():
    """Test timing difference bridge with FX conversion to USD."""
    # Create FX rates
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG'],
        'FX_rate': [15.5, 4.0]
    })
    fx_converter = FXConverter(cr05_df)
    
    # Create Jdash data
    jdash_df = pd.DataFrame([
        {"Voucher Id": "V001", "Amount Used": 100.0},
        {"Voucher Id": "V002", "Amount Used": 50.0},
    ])
    
    # Create IPE_08 data with variances
    ipe_08_df = pd.DataFrame([
        {
            "id": "V001",
            "business_use": "refund",
            "is_active": 0,
            "created_at": "2025-08-01",
            "TotalAmountUsed": 310.0,  # 310 GHS variance = 20 USD
            "ID_COMPANY": "JD_GH"
        },
        {
            "id": "V002",
            "business_use": "apology_v2",
            "is_active": 0,
            "created_at": "2025-08-15",
            "TotalAmountUsed": 250.0,  # 250 NGN variance = 62.5 USD
            "ID_COMPANY": "EC_NG"
        },
    ])
    
    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, cutoff_date="2025-09-30", fx_converter=fx_converter
    )
    
    # Should have Amount_USD column
    assert 'Amount_USD' in proof_df.columns
    # Variances: (310-100)/15.5 + (250-50)/4.0 = 13.55 + 50 = 63.55
    assert bridge_amount == pytest.approx(63.55, abs=0.1)


def test_calculate_timing_difference_bridge_without_fx_conversion():
    """Test timing difference bridge without FX converter (local currency)."""
    jdash_df = pd.DataFrame([
        {"Voucher Id": "V001", "Amount Used": 100.0},
    ])
    
    ipe_08_df = pd.DataFrame([
        {
            "id": "V001",
            "business_use": "refund",
            "is_active": 0,
            "created_at": "2025-08-01",
            "TotalAmountUsed": 310.0,
            "ID_COMPANY": "JD_GH"
        },
    ])
    
    # Call without FX converter
    bridge_amount, proof_df = calculate_timing_difference_bridge(
        jdash_df, ipe_08_df, cutoff_date="2025-09-30", fx_converter=None
    )
    
    # Should use local currency variance: 310 - 100 = 210
    assert bridge_amount == pytest.approx(210.0, rel=1e-6)
    assert 'Amount_USD' not in proof_df.columns


# ========================================================================
# Tests for calculate_integration_error_adjustment with FX conversion
# ========================================================================


def test_calculate_integration_error_adjustment_with_fx_conversion():
    """Test integration error adjustment with FX conversion to USD."""
    # Create FX rates
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH', 'EC_NG'],
        'FX_rate': [15.5, 4.0]
    })
    fx_converter = FXConverter(cr05_df)
    
    # Create integration errors data
    ipe_rec_errors_df = pd.DataFrame([
        {
            "Source_System": "Cash Deposits",
            "Amount": 1550.0,  # 1550 GHS = 100 USD
            "Integration_Status": "Error",
            "Transaction_ID": "T001",
            "ID_COMPANY": "JD_GH"
        },
        {
            "Source_System": "Refunds",
            "Amount": 400.0,  # 400 NGN = 100 USD
            "Integration_Status": "Failed",
            "Transaction_ID": "T002",
            "ID_COMPANY": "EC_NG"
        },
    ])
    
    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df, fx_converter=fx_converter
    )
    
    # Should convert to USD: 100 + 100 = 200
    assert adjustment_amount == pytest.approx(200.0, rel=1e-6)
    assert 'Amount_USD' in proof_df.columns
    assert len(proof_df) == 2


def test_calculate_integration_error_adjustment_without_fx_conversion():
    """Test integration error adjustment without FX converter (local currency)."""
    ipe_rec_errors_df = pd.DataFrame([
        {
            "Source_System": "Cash Deposits",
            "Amount": 1550.0,
            "Integration_Status": "Error",
            "Transaction_ID": "T001",
            "ID_COMPANY": "JD_GH"
        },
        {
            "Source_System": "Refunds",
            "Amount": 400.0,
            "Integration_Status": "Failed",
            "Transaction_ID": "T002",
            "ID_COMPANY": "EC_NG"
        },
    ])
    
    # Call without FX converter
    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df, fx_converter=None
    )
    
    # Should use local currency: 1550 + 400 = 1950
    assert adjustment_amount == pytest.approx(1950.0, rel=1e-6)
    assert 'Amount_USD' not in proof_df.columns


def test_integration_error_adjustment_fx_with_unknown_companies():
    """Test integration errors with some unknown companies in FX rates."""
    # Create FX rates with only one company
    cr05_df = pd.DataFrame({
        'Company_Code': ['JD_GH'],
        'FX_rate': [15.5]
    })
    fx_converter = FXConverter(cr05_df, default_rate=1.0)
    
    ipe_rec_errors_df = pd.DataFrame([
        {
            "Source_System": "Cash Deposits",
            "Amount": 1550.0,  # Known company: 1550/15.5 = 100 USD
            "Integration_Status": "Error",
            "Transaction_ID": "T001",
            "ID_COMPANY": "JD_GH"
        },
        {
            "Source_System": "Refunds",
            "Amount": 100.0,  # Unknown company: 100/1.0 = 100 USD (default)
            "Integration_Status": "Failed",
            "Transaction_ID": "T002",
            "ID_COMPANY": "UNKNOWN_CO"
        },
    ])
    
    adjustment_amount, proof_df = calculate_integration_error_adjustment(
        ipe_rec_errors_df, fx_converter=fx_converter
    )
    
    # Should convert known company and use default for unknown: 100 + 100 = 200
    assert adjustment_amount == pytest.approx(200.0, rel=1e-6)
    assert 'Amount_USD' in proof_df.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
