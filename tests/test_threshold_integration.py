"""
Integration Tests for Threshold Evaluation in Variance Pipeline.

Tests variance computation with FX conversion and threshold evaluation.
"""

import pytest
import pandas as pd
import numpy as np

from src.core.reconciliation.analysis.variance import (
    compute_variance_pivot_local,
    evaluate_thresholds_variance_pivot,
)
from src.core.reconciliation.analysis.review_tables import build_review_table
from src.utils.fx_utils import FXConverter
from src.core.reconciliation.thresholds import clear_cache


class TestVarianceThresholdIntegration:
    """Integration tests for variance + threshold evaluation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        clear_cache()
        
        # Create sample NAV pivot (local currency)
        self.nav_pivot = pd.DataFrame({
            "country_code": ["EG", "EG", "NG"],
            "category": ["Voucher", "Compensation", "Voucher"],
            "voucher_type": ["refund", "apology", "store_credit"],
            "nav_amount_local": [10000.0, 5000.0, 165000.0],  # EGP, EGP, NGN
        })
        
        # Create sample TV pivot (local currency)
        self.tv_pivot = pd.DataFrame({
            "country_code": ["EG", "EG", "NG"],
            "category": ["Voucher", "Voucher", "Voucher"],
            "voucher_type": ["refund", "store_credit", "store_credit"],
            "tv_amount_local": [9000.0, 1000.0, 160000.0],  # EGP, EGP, NGN
        })
        
        # Create FX rates (CR_05)
        cr05_df = pd.DataFrame({
            "Company_Code": ["JM_EG", "EC_NG"],
            "FX_rate": [50.0, 1650.0],  # 1 USD = 50 EGP, 1 USD = 1650 NGN
        })
        
        self.fx_converter = FXConverter(cr05_df)
        self.cutoff_date = "2025-09-30"
    
    def test_compute_variance_with_fx(self):
        """Test variance computation with FX conversion."""
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=self.nav_pivot,
            tv_pivot_local_df=self.tv_pivot,
            fx_converter=self.fx_converter,
            cutoff_date=self.cutoff_date,
        )
        
        # Check structure
        assert len(variance_df) == 4  # 4 unique buckets after outer join
        assert "variance_amount_local" in variance_df.columns
        assert "variance_amount_usd" in variance_df.columns
        assert "fx_rate_used" in variance_df.columns
        assert "fx_missing" in variance_df.columns
        
        # Check EG refund variance (NAV=10000, TV=9000, variance=+1000 EGP)
        eg_refund = variance_df[
            (variance_df["country_code"] == "EG") &
            (variance_df["voucher_type"] == "refund")
        ]
        assert len(eg_refund) == 1
        assert eg_refund.iloc[0]["variance_amount_local"] == 1000.0  # EGP
        assert abs(eg_refund.iloc[0]["variance_amount_usd"] - 20.0) < 0.1  # 1000/50 = 20 USD
        
        # Check NG store_credit variance (NAV=165000, TV=160000, variance=+5000 NGN)
        ng_store = variance_df[
            (variance_df["country_code"] == "NG") &
            (variance_df["voucher_type"] == "store_credit")
        ]
        assert len(ng_store) == 1
        assert abs(ng_store.iloc[0]["variance_amount_local"] - 5000.0) < 0.1  # NGN
        assert abs(ng_store.iloc[0]["variance_amount_usd"] - 3.03) < 0.1  # 5000/1650 ≈ 3.03 USD
    
    def test_evaluate_thresholds_on_variance(self):
        """Test threshold evaluation on variance pivot."""
        # Compute variance first
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=self.nav_pivot,
            tv_pivot_local_df=self.tv_pivot,
            fx_converter=self.fx_converter,
            cutoff_date=self.cutoff_date,
        )
        
        # Evaluate thresholds for GL 18412
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=variance_df,
            gl_account="18412",
        )
        
        # Check threshold columns added
        assert "threshold_usd" in evaluated_df.columns
        assert "status" in evaluated_df.columns
        assert "threshold_contract_version" in evaluated_df.columns
        assert "threshold_contract_hash" in evaluated_df.columns
        assert "threshold_source" in evaluated_df.columns
        
        # All rows should have threshold values
        assert evaluated_df["threshold_usd"].notna().all()
        assert evaluated_df["status"].isin(["OK", "INVESTIGATE"]).all()
        
        # Check specific thresholds (based on DEFAULT.yaml: 1000 USD for BUCKET_USD)
        # EG refund: variance=20 USD, should be OK (< 1000)
        eg_refund = evaluated_df[
            (evaluated_df["country_code"] == "EG") &
            (evaluated_df["voucher_type"] == "refund")
        ]
        assert eg_refund.iloc[0]["status"] == "OK"
        
        # Check that threshold metadata is populated
        assert eg_refund.iloc[0]["threshold_contract_version"] >= 1
        assert len(eg_refund.iloc[0]["threshold_contract_hash"]) > 0
        assert eg_refund.iloc[0]["threshold_source"] in ["catalog", "fallback"]
    
    def test_threshold_investigation_flag(self):
        """Test that large variances are flagged as INVESTIGATE."""
        # Create pivot with large variance
        nav_pivot_large = pd.DataFrame({
            "country_code": ["EG"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "nav_amount_local": [100000.0],  # 100k EGP = 2000 USD
        })
        
        tv_pivot_large = pd.DataFrame({
            "country_code": ["EG"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "tv_amount_local": [50000.0],  # 50k EGP = 1000 USD
        })
        
        # Variance = 50k EGP = 1000 USD, should trigger INVESTIGATE (threshold=1000)
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=nav_pivot_large,
            tv_pivot_local_df=tv_pivot_large,
            fx_converter=self.fx_converter,
            cutoff_date=self.cutoff_date,
        )
        
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=variance_df,
            gl_account="18412",
        )
        
        # Should be marked as INVESTIGATE (variance >= threshold)
        assert evaluated_df.iloc[0]["status"] == "INVESTIGATE"
        assert abs(evaluated_df.iloc[0]["variance_amount_usd"] - 1000.0) < 1.0
    
    def test_missing_fx_rate_handling(self):
        """Test that missing FX rates are handled gracefully."""
        # Create pivot for country without FX rate
        nav_pivot_unknown = pd.DataFrame({
            "country_code": ["XX"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "nav_amount_local": [1000.0],
        })
        
        tv_pivot_unknown = pd.DataFrame({
            "country_code": ["XX"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "tv_amount_local": [900.0],
        })
        
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=nav_pivot_unknown,
            tv_pivot_local_df=tv_pivot_unknown,
            fx_converter=self.fx_converter,
            cutoff_date=self.cutoff_date,
        )
        
        # Should have fx_missing flag
        assert variance_df.iloc[0]["fx_missing"] == True
        
        # FXConverter uses default_rate=1.0 when company not found
        # So variance_usd = variance_local / 1.0 = 100.0 USD
        assert abs(variance_df.iloc[0]["variance_amount_usd"] - 100.0) < 0.1
        
        # Evaluate thresholds
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=variance_df,
            gl_account="18412",
        )
        
        # Variance = 100 USD, threshold = 1000 USD, should be OK
        # (FX missing doesn't force INVESTIGATE if variance_usd is valid)
        assert evaluated_df.iloc[0]["status"] == "OK"
    
    def test_build_review_table_integration(self):
        """Test building review table from evaluated variance."""
        # Compute variance and evaluate thresholds
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=self.nav_pivot,
            tv_pivot_local_df=self.tv_pivot,
            fx_converter=self.fx_converter,
            cutoff_date=self.cutoff_date,
        )
        
        # Add a large variance to trigger INVESTIGATE
        large_variance_row = pd.DataFrame({
            "country_code": ["EG"],
            "category": ["Voucher"],
            "voucher_type": ["compensation"],
            "nav_amount_local": [100000.0],
            "tv_amount_local": [0.0],
            "variance_amount_local": [100000.0],
            "nav_amount_usd": [2000.0],
            "tv_amount_usd": [0.0],
            "variance_amount_usd": [2000.0],
            "fx_rate_used": [50.0],
            "fx_missing": [False],
        })
        variance_df = pd.concat([variance_df, large_variance_row], ignore_index=True)
        
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=variance_df,
            gl_account="18412",
        )
        
        # Build review table (bucket-level only, no drilldown)
        review_df = build_review_table(
            variance_pivot_with_status=evaluated_df,
            gl_account="18412",
        )
        
        # Check structure
        assert "country_code" in review_df.columns
        assert "gl_account" in review_df.columns
        assert "bucket_status" in review_df.columns
        assert "row_type" in review_df.columns
        
        # Should only contain INVESTIGATE buckets
        if not review_df.empty:
            assert (review_df["bucket_status"] == "INVESTIGATE").all()
            assert (review_df["row_type"] == "bucket_summary").all()
    
    def test_empty_variance_handling(self):
        """Test handling of empty variance DataFrame."""
        empty_df = pd.DataFrame(columns=[
            "country_code", "category", "voucher_type",
            "nav_amount_local", "tv_amount_local", "variance_amount_local",
            "nav_amount_usd", "tv_amount_usd", "variance_amount_usd",
            "fx_rate_used", "fx_missing",
        ])
        
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=empty_df,
            gl_account="18412",
        )
        
        assert len(evaluated_df) == 0
        assert "threshold_usd" in evaluated_df.columns
        assert "status" in evaluated_df.columns


class TestPhase3WorkflowOrder:
    """Test the validated Phase 3 workflow order."""
    
    def test_phase3_workflow(self):
        """
        Test complete Phase 3 workflow:
        1. Build NAV pivot (local)
        2. Build TV pivot (local)
        3. Compute variance (local)
        4. Apply FX to USD
        5. Evaluate thresholds (USD)
        6. Build review table
        """
        # Step 1-2: NAV and TV pivots (simulated, already in local currency)
        nav_pivot = pd.DataFrame({
            "country_code": ["EG"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "nav_amount_local": [60000.0],  # EGP
        })
        
        tv_pivot = pd.DataFrame({
            "country_code": ["EG"],
            "category": ["Voucher"],
            "voucher_type": ["refund"],
            "tv_amount_local": [10000.0],  # EGP
        })
        
        # Step 3-4: Compute variance and apply FX
        cr05_df = pd.DataFrame({
            "Company_Code": ["JM_EG"],
            "FX_rate": [50.0],
        })
        fx_converter = FXConverter(cr05_df)
        
        variance_df = compute_variance_pivot_local(
            nav_pivot_local_df=nav_pivot,
            tv_pivot_local_df=tv_pivot,
            fx_converter=fx_converter,
            cutoff_date="2025-09-30",
        )
        
        # Verify variance computation
        assert len(variance_df) == 1
        assert variance_df.iloc[0]["variance_amount_local"] == 50000.0  # EGP
        assert abs(variance_df.iloc[0]["variance_amount_usd"] - 1000.0) < 1.0  # USD
        
        # Step 5: Evaluate thresholds (on USD amounts)
        evaluated_df = evaluate_thresholds_variance_pivot(
            variance_df=variance_df,
            gl_account="18412",
        )
        
        # Verify threshold evaluation
        assert "status" in evaluated_df.columns
        # Variance = 1000 USD, threshold = 1000 USD, should be INVESTIGATE (>=)
        assert evaluated_df.iloc[0]["status"] == "INVESTIGATE"
        
        # Step 6: Build review table
        review_df = build_review_table(
            variance_pivot_with_status=evaluated_df,
            gl_account="18412",
        )
        
        # Verify review table
        assert len(review_df) == 1
        assert review_df.iloc[0]["bucket_status"] == "INVESTIGATE"
        assert review_df.iloc[0]["gl_account"] == "18412"
        
        # Verify audit trail is complete
        assert review_df.iloc[0]["threshold_contract_version"] >= 1
        assert len(review_df.iloc[0]["threshold_contract_hash"]) == 64  # SHA256


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
