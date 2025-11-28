"""
Headless Reconciliation Engine (run_reconciliation)

Provides the main entry point for running complete SOX reconciliation workflows
without a graphical interface. This is the key module for automation via
Temporal.io or n8n.

Usage:
    from src.core.recon.run_reconciliation import run_reconciliation
    
    params = {
        'cutoff_date': '2025-09-30',
        'id_companies_active': "('EC_NG')",
        'gl_accounts': ['18412', '13003'],
    }
    
    result = run_reconciliation(params)
    
    # Result contains:
    # - dataframes: Dict[str, DataFrame] - All extracted/processed DataFrames
    # - metrics: Dict[str, Any] - Reconciliation metrics and summaries
    # - categorization: Dict[str, Any] - Bridge categorization results
    # - status: str - Overall status ('SUCCESS', 'WARNING', 'ERROR')
    # - errors: List[str] - Any errors encountered

Dependencies:
    - Issue #1: Extraction Pipeline (src/core/extraction_pipeline.py)
    - Issue #2: Categorization Pipeline (src/bridges/cat_pipeline.py)
    - Existing bridges (src/bridges/timing_difference.py, etc.)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

# Import extraction modules
from src.core.extraction_pipeline import load_all_data

# Import preprocessing modules
from src.core.quality_checker import DataQualityEngine
from src.core.scope_filtering import (
    filter_ipe08_scope,
    filter_gl_18412,
    get_non_marketing_summary,
)

# Import categorization pipeline
from src.bridges.cat_pipeline import categorize_nav_vouchers, get_categorization_summary

# Import bridge functions
from src.bridges.classifier import (
    classify_bridges,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
    calculate_timing_difference_bridge,
)
from src.bridges.catalog import load_rules

# Import catalog for quality rules
from src.core.catalog.cpg1 import get_item_by_id

# Import summary builder for reconciliation metrics
from src.core.recon.summary_builder import SummaryBuilder


logger = logging.getLogger(__name__)


def run_reconciliation(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a complete SOX reconciliation workflow in headless mode.
    
    This function orchestrates the entire reconciliation pipeline:
    1. Extraction - Load data from sources (database or fixtures)
    2. Preprocessing - Apply quality checks and scope filtering
    3. Categorization - Classify NAV GL entries by bridge category
    4. Bridge Analysis - Calculate reconciliation bridges and adjustments
    
    Args:
        params: Dictionary containing reconciliation parameters:
            - cutoff_date (str): Cutoff date in YYYY-MM-DD format (required)
            - id_companies_active (str): Company filter in SQL format, 
                                         e.g., "('EC_NG')" (required)
            - gl_accounts (List[str], optional): GL accounts to include
            - required_ipes (List[str], optional): IPE IDs to load
            - uploaded_files (Dict[str, Any], optional): Manual file uploads
            - run_bridges (bool, optional): Whether to run bridge analysis (default: True)
            - validate_quality (bool, optional): Whether to run quality checks (default: True)
    
    Returns:
        Dictionary containing all reconciliation results:
        {
            'status': str - 'SUCCESS', 'WARNING', or 'ERROR'
            'timestamp': str - ISO timestamp of execution
            'params': dict - Input parameters used
            'dataframes': dict - All DataFrames (as serializable dicts)
            'dataframe_summaries': dict - Row counts and column info
            'evidence_paths': dict - Paths to evidence packages
            'data_sources': dict - Source of each data item
            'quality_reports': dict - Quality check results
            'categorization': dict - Bridge categorization results
            'bridges': dict - Bridge calculation results
            'reconciliation': dict - Overall reconciliation metrics
            'errors': list - Any errors encountered
            'warnings': list - Any warnings generated
        }
    
    Example:
        >>> params = {
        ...     'cutoff_date': '2025-09-30',
        ...     'id_companies_active': "('EC_NG')",
        ... }
        >>> result = run_reconciliation(params)
        >>> print(f"Status: {result['status']}")
        >>> print(f"Total rows processed: {sum(s['row_count'] for s in result['dataframe_summaries'].values())}")
    """
    # Initialize result structure
    result: Dict[str, Any] = {
        'status': 'SUCCESS',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'params': params,
        'dataframes': {},
        'dataframe_summaries': {},
        'evidence_paths': {},
        'data_sources': {},
        'quality_reports': {},
        'categorization': {},
        'bridges': {},
        'reconciliation': {},
        'errors': [],
        'warnings': [],
    }
    
    # Validate required parameters
    validation_errors = _validate_params(params)
    if validation_errors:
        result['status'] = 'ERROR'
        result['errors'].extend(validation_errors)
        return result
    
    # Extract parameters with defaults
    cutoff_date = params['cutoff_date']
    required_ipes = params.get('required_ipes', _get_default_ipes())
    uploaded_files = params.get('uploaded_files', {})
    run_bridges = params.get('run_bridges', True)
    validate_quality = params.get('validate_quality', True)
    
    try:
        # =========================================================
        # PHASE 1: EXTRACTION
        # =========================================================
        logger.info("Phase 1: Starting data extraction...")
        
        data_store, evidence_store, source_store = load_all_data(
            params=params,
            uploaded_files=uploaded_files,
            required_ipes=required_ipes,
        )
        
        result['evidence_paths'] = evidence_store
        result['data_sources'] = source_store
        
        # Store DataFrame summaries (not full DataFrames for JSON serialization)
        for item_id, df in data_store.items():
            result['dataframe_summaries'][item_id] = _get_dataframe_summary(df)
        
        logger.info(f"Phase 1 complete: Loaded {len(data_store)} items")
        
        # =========================================================
        # PHASE 2: PREPROCESSING & QUALITY CHECKS
        # =========================================================
        logger.info("Phase 2: Running preprocessing and quality checks...")
        
        processed_data = {}
        
        # Apply scope filtering for IPE_08
        if 'IPE_08' in data_store:
            ipe_08_filtered = filter_ipe08_scope(data_store['IPE_08'])
            processed_data['IPE_08_filtered'] = ipe_08_filtered
            result['dataframe_summaries']['IPE_08_filtered'] = _get_dataframe_summary(ipe_08_filtered)
            
            # Add Non-Marketing summary
            nm_summary = get_non_marketing_summary(data_store['IPE_08'])
            result['categorization']['ipe_08_non_marketing_summary'] = nm_summary
        
        # Apply GL 18412 filter for CR_03
        if 'CR_03' in data_store:
            cr_03_gl18412 = filter_gl_18412(data_store['CR_03'])
            processed_data['CR_03_GL18412'] = cr_03_gl18412
            result['dataframe_summaries']['CR_03_GL18412'] = _get_dataframe_summary(cr_03_gl18412)
        
        # Run quality checks if enabled
        if validate_quality:
            quality_engine = DataQualityEngine()
            
            for item_id, df in data_store.items():
                catalog_item = get_item_by_id(item_id)
                if catalog_item and catalog_item.quality_rules:
                    report = quality_engine.run_checks(df, catalog_item.quality_rules)
                    result['quality_reports'][item_id] = {
                        'status': report.status,
                        'details': report.details,
                    }
                    if report.status == 'FAIL':
                        result['warnings'].append(f"Quality check failed for {item_id}")
        
        logger.info("Phase 2 complete: Preprocessing and quality checks done")
        
        # =========================================================
        # PHASE 3: CATEGORIZATION
        # =========================================================
        logger.info("Phase 3: Running categorization pipeline...")
        
        # Get required DataFrames for categorization
        cr_03_df = data_store.get('CR_03')
        ipe_08_df = data_store.get('IPE_08')
        doc_voucher_usage_df = data_store.get('DOC_VOUCHER_USAGE')
        
        if cr_03_df is not None and not cr_03_df.empty:
            # Apply categorization
            categorized_df = categorize_nav_vouchers(
                cr_03_df=cr_03_df,
                ipe_08_df=ipe_08_df,
                doc_voucher_usage_df=doc_voucher_usage_df,
            )
            
            processed_data['CR_03_categorized'] = categorized_df
            result['dataframe_summaries']['CR_03_categorized'] = _get_dataframe_summary(categorized_df)
            
            # Get categorization summary
            cat_summary = get_categorization_summary(categorized_df)
            result['categorization']['summary'] = cat_summary
            result['categorization']['by_category'] = cat_summary.get('by_category', {})
            result['categorization']['by_voucher_type'] = cat_summary.get('by_voucher_type', {})
            result['categorization']['by_integration_type'] = cat_summary.get('by_integration_type', {})
        else:
            result['warnings'].append("CR_03 data not available for categorization")
        
        logger.info("Phase 3 complete: Categorization done")
        
        # =========================================================
        # PHASE 4: BRIDGE ANALYSIS
        # =========================================================
        if run_bridges:
            logger.info("Phase 4: Running bridge analysis...")
            
            bridges_result = _run_bridge_analysis(
                data_store=data_store,
                processed_data=processed_data,
                cutoff_date=cutoff_date,
            )
            
            result['bridges'] = bridges_result
            
            logger.info("Phase 4 complete: Bridge analysis done")
        
        # =========================================================
        # PHASE 5: RECONCILIATION METRICS
        # =========================================================
        logger.info("Phase 5: Calculating reconciliation metrics...")
        
        summary_builder = SummaryBuilder(data_store)
        recon_metrics = summary_builder.build()
        
        result['reconciliation'] = recon_metrics
        
        logger.info("Phase 5 complete: Reconciliation metrics calculated")
        
        # =========================================================
        # FINALIZE
        # =========================================================
        # Store serializable versions of key DataFrames
        result['dataframes'] = _serialize_dataframes(data_store, processed_data)
        
        # Determine final status
        if result['errors']:
            result['status'] = 'ERROR'
        elif result['warnings']:
            result['status'] = 'WARNING'
        else:
            result['status'] = 'SUCCESS'
        
        logger.info(f"Reconciliation complete with status: {result['status']}")
        
    except Exception as e:
        logger.exception(f"Error during reconciliation: {e}")
        result['status'] = 'ERROR'
        result['errors'].append(f"Reconciliation failed: {str(e)}")
    
    return result


def _validate_params(params: Dict[str, Any]) -> List[str]:
    """Validate required reconciliation parameters."""
    errors = []
    
    if 'cutoff_date' not in params:
        errors.append("Missing required parameter: 'cutoff_date'")
    
    if 'id_companies_active' not in params:
        errors.append("Missing required parameter: 'id_companies_active'")
    
    # Validate cutoff_date format
    if 'cutoff_date' in params:
        try:
            datetime.strptime(params['cutoff_date'], '%Y-%m-%d')
        except ValueError:
            errors.append("'cutoff_date' must be in YYYY-MM-DD format")
    
    return errors


def _get_default_ipes() -> List[str]:
    """Return the default list of IPEs required for reconciliation."""
    return [
        'CR_04',      # NAV GL Balances (Actuals)
        'CR_03',      # NAV GL Entries (for categorization)
        'CR_05',      # FX Rates
        'IPE_07',     # Customer balances
        'IPE_08',     # Voucher liabilities
        'IPE_10',     # Customer prepayments
        'DOC_VOUCHER_USAGE',  # Voucher usage for timing bridge
    ]


def _get_dataframe_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Generate a summary of a DataFrame for JSON serialization."""
    if df is None or df.empty:
        return {
            'row_count': 0,
            'column_count': 0,
            'columns': [],
            'dtypes': {},
            'memory_mb': 0,
        }
    
    return {
        'row_count': len(df),
        'column_count': len(df.columns),
        'columns': list(df.columns),
        'dtypes': {col: str(dtype) for col, dtype in df.dtypes.items()},
        'memory_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
    }


def _run_bridge_analysis(
    data_store: Dict[str, pd.DataFrame],
    processed_data: Dict[str, pd.DataFrame],
    cutoff_date: str,
) -> Dict[str, Any]:
    """
    Run all bridge calculations.
    
    Returns a dictionary with bridge results.
    """
    bridges = {
        'vtc_adjustment': None,
        'customer_posting_group': None,
        'timing_difference': None,
        'classified_transactions': None,
    }
    
    # Get required DataFrames
    ipe_08_filtered = processed_data.get('IPE_08_filtered')
    ipe_07_df = data_store.get('IPE_07')
    categorized_cr_03 = processed_data.get('CR_03_categorized')
    
    # 1. VTC Adjustment Bridge
    if ipe_08_filtered is not None and not ipe_08_filtered.empty:
        try:
            vtc_amount, vtc_proof_df, vtc_metrics = calculate_vtc_adjustment(
                ipe_08_df=ipe_08_filtered,
                categorized_cr_03_df=categorized_cr_03,
            )
            bridges['vtc_adjustment'] = {
                'amount': float(vtc_amount) if pd.notna(vtc_amount) else 0,
                'proof_row_count': len(vtc_proof_df) if vtc_proof_df is not None else 0,
                'metrics': vtc_metrics,
            }
        except Exception as e:
            logger.warning(f"VTC adjustment calculation failed: {e}")
            bridges['vtc_adjustment'] = {'error': str(e)}
    
    # 2. Customer Posting Group Bridge
    if ipe_07_df is not None and not ipe_07_df.empty:
        try:
            cpg_amount, cpg_proof_df = calculate_customer_posting_group_bridge(ipe_07_df)
            bridges['customer_posting_group'] = {
                'amount': float(cpg_amount) if pd.notna(cpg_amount) else 0,
                'problem_customers_count': len(cpg_proof_df) if cpg_proof_df is not None else 0,
            }
        except Exception as e:
            logger.warning(f"Customer posting group bridge failed: {e}")
            bridges['customer_posting_group'] = {'error': str(e)}
    
    # 3. Timing Difference Bridge
    # Requires Jdash data which may not be available
    jdash_df = data_store.get('JDASH')  # May need to be loaded separately
    if ipe_08_filtered is not None and not ipe_08_filtered.empty:
        try:
            timing_variance, timing_proof_df = calculate_timing_difference_bridge(
                jdash_df=jdash_df,
                ipe_08_df=ipe_08_filtered,
                cutoff_date=cutoff_date,
            )
            bridges['timing_difference'] = {
                'variance': float(timing_variance) if pd.notna(timing_variance) else 0,
                'proof_row_count': len(timing_proof_df) if timing_proof_df is not None else 0,
            }
        except Exception as e:
            logger.warning(f"Timing difference bridge failed: {e}")
            bridges['timing_difference'] = {'error': str(e)}
    
    # 4. Bridge Classification (general rule-based)
    # Apply to IPE_31 or similar transactional data
    ipe_31_df = data_store.get('IPE_31')
    if ipe_31_df is not None and not ipe_31_df.empty:
        try:
            bridge_rules = load_rules()
            classified_df = classify_bridges(ipe_31_df, bridge_rules)
            
            # Count by bridge key
            if 'bridge_key' in classified_df.columns:
                bridge_counts = classified_df['bridge_key'].value_counts(dropna=False).to_dict()
            else:
                bridge_counts = {}
            
            bridges['classified_transactions'] = {
                'total_rows': len(classified_df),
                'classified_count': classified_df['bridge_key'].notna().sum() if 'bridge_key' in classified_df.columns else 0,
                'by_bridge_type': bridge_counts,
            }
        except Exception as e:
            logger.warning(f"Bridge classification failed: {e}")
            bridges['classified_transactions'] = {'error': str(e)}
    
    return bridges


def _serialize_dataframes(
    data_store: Dict[str, pd.DataFrame],
    processed_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    """
    Convert DataFrames to JSON-serializable format.
    
    For large DataFrames, only includes summary information.
    For smaller DataFrames, includes the full data as records.
    """
    MAX_ROWS_FOR_FULL_DATA = 1000
    
    serialized = {}
    
    all_data = {**data_store, **processed_data}
    
    for name, df in all_data.items():
        if df is None or df.empty:
            serialized[name] = {'records': [], 'truncated': False}
            continue
        
        try:
            # Convert datetime columns to strings
            df_copy = df.copy()
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                    df_copy[col] = df_copy[col].astype(str)
            
            if len(df_copy) <= MAX_ROWS_FOR_FULL_DATA:
                serialized[name] = {
                    'records': df_copy.to_dict(orient='records'),
                    'truncated': False,
                }
            else:
                # Only include first N rows for large DataFrames
                serialized[name] = {
                    'records': df_copy.head(MAX_ROWS_FOR_FULL_DATA).to_dict(orient='records'),
                    'truncated': True,
                    'total_rows': len(df_copy),
                }
        except Exception as e:
            logger.warning(f"Could not serialize DataFrame {name}: {e}")
            serialized[name] = {'error': str(e)}
    
    return serialized


__all__ = [
    'run_reconciliation',
]
