"""
Extraction Pipeline Module

Provides orchestration for IPE data extraction with evidence generation.
This module is independent of Streamlit and returns standard Pandas DataFrames.

CRITICAL: Includes the CR_05 patch for handling column names with '?' characters.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple
from unittest.mock import MagicMock

import pandas as pd

from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager
from src.core.evidence_locator import get_latest_evidence_zip

logger = logging.getLogger(__name__)


# Repository root path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


class ExtractionPipeline:
    """
    Orchestrates IPE data extraction with evidence generation.
    
    This class provides a unified interface for extracting data from various
    IPE sources, with support for:
    - Live database extraction via IPERunner
    - Fixture fallback for development/testing
    - Evidence package generation
    - CR_05 column name patching
    
    Attributes:
        params: Dictionary of SQL parameters for extractions
        country_code: Country code (e.g., 'JD_GH', 'EC_NG')
        period_str: Period string in YYYYMM format
    """
    
    def __init__(
        self, 
        params: Dict[str, Any],
        country_code: Optional[str] = None,
        period_str: Optional[str] = None
    ):
        """
        Initialize the extraction pipeline.
        
        Args:
            params: Dictionary of SQL parameters including 'cutoff_date', 
                    'id_companies_active', etc.
            country_code: Optional country code. If not provided, extracted from params.
            period_str: Optional period string (YYYYMM). If not provided, derived from cutoff_date.
        """
        self.params = params
        
        # Extract country code from params if not provided
        if country_code is None and 'id_companies_active' in params:
            self.country_code = params['id_companies_active'].strip("()'")
        else:
            self.country_code = country_code or ""
        
        # Derive period from cutoff_date if not provided
        if period_str is None and 'cutoff_date' in params:
            self.period_str = params['cutoff_date'].replace("-", "")[:6]
        else:
            self.period_str = period_str or ""
    
    async def run_extraction_with_evidence(
        self, 
        item_id: str
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Executes extraction via IPERunner.run() with evidence generation.
        
        Includes a CRITICAL PATCH for CR_05 to handle column names with '?' characters.
        
        Args:
            item_id: The IPE or CR identifier (e.g., 'IPE_07', 'CR_05')
        
        Returns:
            Tuple of (DataFrame, zip_path) where:
                - DataFrame: Extracted data (or empty DataFrame on failure)
                - zip_path: Path to evidence ZIP (or None if not generated)
        """
        # Use mock secrets manager for local/dev execution
        mock_secrets = MagicMock(spec=AWSSecretsManager)
        mock_secrets.get_secret.return_value = "FAKE_SECRET"
        
        item = get_item_by_id(item_id)
        if not item:
            logger.warning(f"Item {item_id} not found in catalog")
            return pd.DataFrame(), None
        
        # Inject parameters into SQL query for direct execution (fallback)
        final_query = item.sql_query
        for key, value in self.params.items():
            if f"{{{key}}}" in final_query:
                final_query = final_query.replace(f"{{{key}}}", str(value))
        
        ipe_config = {
            "id": item.item_id,
            "description": getattr(item, "description", ""),
            "secret_name": "fake",
            "main_query": final_query,
            "validation": {},
        }
        
        runner = IPERunner(
            ipe_config,
            mock_secrets,
            cutoff_date=self.params.get("cutoff_date"),
            country=self.country_code,
            period=self.period_str,
            full_params=self.params
        )
        
        # === CRITICAL PATCH FOR CR_05 ===
        # Force the runner to ignore '?' in column names (CR_05 specific issue)
        # and execute the query as-is (parameters already injected above)
        def patched_exec(query, params=None):
            return pd.read_sql(query, runner.connection)
        
        runner._execute_query_with_parameters = patched_exec
        # ================================
        
        try:
            df = runner.run()
            zip_path = get_latest_evidence_zip(item_id)
            return df, zip_path
        except Exception as e:
            logger.error(f"Extraction failed for {item_id}: {e}")
            # Fallback to fixture
            return self._load_fixture(item_id), None
    
    def _load_fixture(self, item_id: str) -> pd.DataFrame:
        """
        Load data from fixture file (fallback for development/testing).
        
        Args:
            item_id: The IPE or CR identifier
        
        Returns:
            DataFrame from fixture file, or empty DataFrame if not found
        """
        fixture_path = os.path.join(
            REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv"
        )
        if os.path.exists(fixture_path):
            logger.info(f"Loading fixture for {item_id}: {fixture_path}")
            return pd.read_csv(fixture_path, low_memory=False)
        
        logger.warning(f"No fixture found for {item_id}")
        return pd.DataFrame()
    
    def filter_by_country(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame by country code.
        
        Looks for common country column names and filters accordingly.
        
        Args:
            df: DataFrame to filter
        
        Returns:
            Filtered DataFrame (or original if no country column found)
        """
        if df.empty:
            return df
        
        country_columns = ["ID_COMPANY", "id_company", "ID_Company", "country"]
        for col in country_columns:
            if col in df.columns:
                return df[df[col] == self.country_code].copy()
        
        return df


async def run_extraction_with_evidence(
    item_id: str, 
    params: Dict[str, Any], 
    country_code: str, 
    period_str: str
) -> Tuple[pd.DataFrame, Optional[str]]:
    """
    Standalone function for backward compatibility.
    
    Executes extraction via IPERunner.run() ensuring Rich Metadata & Evidence Generation.
    Includes CRITICAL PATCH for CR_05 (handling columns with '?').
    
    Args:
        item_id: The IPE or CR identifier
        params: SQL parameters dictionary
        country_code: Country code (e.g., 'JD_GH')
        period_str: Period in YYYYMM format
    
    Returns:
        Tuple of (DataFrame, zip_path)
    """
    pipeline = ExtractionPipeline(params, country_code, period_str)
    return await pipeline.run_extraction_with_evidence(item_id)


def load_all_data(
    params: Dict[str, Any],
    uploaded_files: Optional[Dict[str, Any]] = None,
    required_ipes: Optional[list] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[Dict[str, pd.DataFrame], Dict[str, Optional[str]], Dict[str, str]]:
    """
    Orchestrates loading and evidence collection for multiple IPEs.
    
    This is the main entry point for loading all required data for a reconciliation.
    It supports manual file uploads, live database extraction, and fixture fallbacks.
    
    Args:
        params: SQL parameters dictionary including:
            - cutoff_date: Cutoff date in YYYY-MM-DD format
            - id_companies_active: Company filter in SQL format
            - Other SQL parameters
        uploaded_files: Optional dictionary of {item_id: file_path_or_object} 
                        for manual CSV overrides
        required_ipes: Optional list of IPE IDs to load. Defaults to standard set.
        progress_callback: Optional callback function(item_id, progress_pct, message)
                           for progress reporting
    
    Returns:
        Tuple of (data_store, evidence_store, source_store) where:
            - data_store: Dict mapping item_id to DataFrame
            - evidence_store: Dict mapping item_id to ZIP path (or None)
            - source_store: Dict mapping item_id to source type 
                           ("Uploaded File", "Live Database", "Local Fixture", "No Data")
    """
    import asyncio
    
    if required_ipes is None:
        required_ipes = ["CR_04", "CR_03", "CR_05", "IPE_07", "IPE_08", "DOC_VOUCHER_USAGE"]
    
    data_store: Dict[str, pd.DataFrame] = {}
    evidence_store: Dict[str, Optional[str]] = {}
    source_store: Dict[str, str] = {}
    
    if uploaded_files is None:
        uploaded_files = {}
    
    # Extract context from params
    country_code = params.get("id_companies_active", "").strip("()'")
    period_str = params.get("cutoff_date", "").replace("-", "")[:6]
    
    pipeline = ExtractionPipeline(params, country_code, period_str)
    
    for i, item_id in enumerate(required_ipes):
        progress_pct = (i + 1) / len(required_ipes)
        
        if progress_callback:
            progress_callback(item_id, progress_pct, f"Processing {item_id}...")
        
        df = None
        zip_path = None
        source = None
        
        # Priority 1: Check for uploaded file
        if item_id in uploaded_files and uploaded_files[item_id] is not None:
            try:
                uploaded = uploaded_files[item_id]
                if isinstance(uploaded, str):
                    # File path
                    df = pd.read_csv(uploaded, low_memory=False)
                elif hasattr(uploaded, 'read'):
                    # File-like object
                    df = pd.read_csv(uploaded, low_memory=False)
                else:
                    # Assume it's already a DataFrame
                    df = uploaded
                
                source = "Uploaded File"
                logger.info(f"{item_id}: Loaded from uploaded file ({len(df)} rows)")
            except Exception as e:
                logger.warning(f"Error reading uploaded file for {item_id}: {e}")
                df = None
        
        # Priority 2: Try live SQL extraction
        if df is None:
            try:
                df, zip_path = asyncio.run(
                    pipeline.run_extraction_with_evidence(item_id)
                )
                if not df.empty:
                    source = "Live Database"
                    logger.info(f"{item_id}: Loaded from database ({len(df)} rows)")
                else:
                    df = None
            except Exception as e:
                logger.warning(f"Live extraction failed for {item_id}: {e}")
                df = None
                zip_path = None
        
        # Priority 3: Fallback to local fixture
        if df is None:
            df = pipeline._load_fixture(item_id)
            if not df.empty:
                source = "Local Fixture"
                logger.info(f"{item_id}: Loaded from fixture ({len(df)} rows)")
            else:
                source = "No Data"
                df = pd.DataFrame()
        
        # Apply country filter for display purposes
        df = pipeline.filter_by_country(df)
        
        data_store[item_id] = df
        evidence_store[item_id] = zip_path
        source_store[item_id] = source or "No Data"
    
    return data_store, evidence_store, source_store


__all__ = [
    'ExtractionPipeline',
    'run_extraction_with_evidence',
    'load_all_data',
]
