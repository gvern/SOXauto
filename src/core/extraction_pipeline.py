"""
Extraction Pipeline Module

Provides orchestration for IPE data extraction with evidence generation.
This module is independent of Streamlit and returns standard Pandas DataFrames.

"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, Callable
from unittest.mock import MagicMock

import pandas as pd

from src.core.runners.mssql_runner import IPERunner
from src.core.catalog.cpg1 import get_item_by_id
from src.utils.aws_utils import AWSSecretsManager
from src.utils.sql_template import render_sql
from src.utils.query_params_builder import build_complete_query_params
from src.core.evidence.evidence_locator import get_latest_evidence_zip
from src.core.jdash_loader import load_jdash_data

logger = logging.getLogger(__name__)


# Repository root path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _build_sql_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Build complete SQL parameters aligned with selected period/country and query defaults."""
    cutoff_date = params.get("cutoff_date")
    if not cutoff_date:
        return dict(params)

    countries = params.get("countries") or params.get("company") or params.get("company_code")
    return build_complete_query_params(
        cutoff_date=str(cutoff_date),
        countries=countries,
        run_id=params.get("run_id"),
        period=params.get("period"),
        overrides=params,
    )


class ExtractionPipeline:
    """
    Orchestrates IPE data extraction with evidence generation.
    
    This class provides a unified interface for extracting data from various
    IPE sources, with support for:
    - Live database extraction via IPERunner
    - Fixture fallback for development/testing
    - Evidence package generation
    
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
        
        # QA VERIFIED: Country code extraction logic supports both direct 'company' parameter
        # and extraction from 'id_companies_active' SQL format
        # This ensures compatibility with both --company flag and legacy parameter format
        # Extract country code from params if not provided
        # Priority 1: Check for direct 'company' parameter
        # Priority 2: Extract from 'id_companies_active' SQL format
        if country_code is None:
            if 'company' in params:
                self.country_code = params['company']
            elif 'id_companies_active' in params:
                self.country_code = params['id_companies_active'].strip("()'")
            else:
                self.country_code = ""
        else:
            self.country_code = country_code
        
        # Derive period from cutoff_date if not provided
        if period_str is None and 'cutoff_date' in params:
            self.period_str = params['cutoff_date'].replace("-", "")[:6]
        else:
            self.period_str = period_str or ""
        self.last_extraction_source: str = "none"
    
    async def run_extraction_with_evidence(
        self, 
        item_id: str
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """
        Executes extraction via IPERunner.run() with evidence generation.
        
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
            self.last_extraction_source = "none"
            return pd.DataFrame(), None
        if not item.sql_query:
            logger.warning(f"Item {item_id} has no SQL query in catalog")
            self.last_extraction_source = "none"
            return pd.DataFrame(), None
        
        try:
            sql_params = _build_sql_params(self.params)
            final_query = render_sql(item.sql_query, sql_params, strict=True)

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
                full_params=sql_params,
            )

            df = runner.run()
            zip_path = get_latest_evidence_zip(item_id)
            self.last_extraction_source = "live"
            return df, zip_path
        except Exception as e:
            logger.error(f"Extraction failed for {item_id}: {e}")
            # Fallback to fixture
            fixture_df = self._load_fixture(item_id)
            self.last_extraction_source = "fixture" if not fixture_df.empty else "none"
            return fixture_df, None
    
    def _load_fixture(self, item_id: str) -> pd.DataFrame:
        """
        Load data from fixture file (fallback for development/testing).
        
        QA VERIFIED: Multi-entity fixture loading implemented
        Supports multi-entity fixture structure:
        - Priority 1: tests/fixtures/{company}/fixture_{item_id}.csv (entity-specific)
        - Priority 2: tests/fixtures/fixture_{item_id}.csv (root fallback)
        
        This allows different entities to have separate test fixtures while maintaining
        backward compatibility with root-level fixtures.
        
        Args:
            item_id: The IPE or CR identifier
        
        Returns:
            DataFrame from fixture file, or empty DataFrame if not found
        """
        def read_fixture_csv(path: str) -> pd.DataFrame:
            """Read fixture CSV with tolerant fallback for malformed lines."""
            try:
                return pd.read_csv(path, low_memory=False)
            except pd.errors.ParserError as exc:
                logger.warning(
                    "Malformed CSV fixture for %s at %s (%s). Retrying with tolerant parser.",
                    item_id,
                    path,
                    exc,
                )
                return pd.read_csv(
                    path,
                    engine="python",
                    on_bad_lines="skip",
                )

        # Try entity-specific fixture first if company code is available
        if self.country_code:
            entity_fixture_path = os.path.join(
                REPO_ROOT, "tests", "fixtures", self.country_code, f"fixture_{item_id}.csv"
            )
            if os.path.exists(entity_fixture_path):
                logger.info(f"Loading entity-specific fixture for {item_id}: {entity_fixture_path}")
                return read_fixture_csv(entity_fixture_path)
        
        # Fallback to root-level fixture
        fixture_path = os.path.join(
            REPO_ROOT, "tests", "fixtures", f"fixture_{item_id}.csv"
        )
        if os.path.exists(fixture_path):
            logger.info(f"Loading fixture for {item_id} from root fixtures: {fixture_path}")
            return read_fixture_csv(fixture_path)
        
        logger.warning(f"No fixture found for {item_id} (checked entity-specific and root)")
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
    progress_callback: Optional[Callable[[str, float, str], None]] = None
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
        required_ipes = [
            "CR_04",
            "CR_03",
            "CR_05",
            "IPE_07",
            "IPE_08",
            "IPE_10",
            "IPE_12",
            "IPE_31",
            "IPE_34",
            "IPE_08_TIMING",
            "IPE_08_USAGE",
            "JDASH",
        ]

    # Normalize legacy aliases to catalog-backed IDs while preserving output aliases later.
    normalized_required_ipes: list[str] = []
    for item_id in required_ipes:
        if item_id == "DOC_VOUCHER_USAGE":
            normalized_required_ipes.append("IPE_08_USAGE")
        else:
            normalized_required_ipes.append(item_id)
    required_ipes = normalized_required_ipes
    
    data_store: Dict[str, pd.DataFrame] = {}
    evidence_store: Dict[str, Optional[str]] = {}
    source_store: Dict[str, str] = {}
    
    if uploaded_files is None:
        uploaded_files = {}
    
    # QA VERIFIED: Country code extraction prioritizes direct 'company' parameter
    # for multi-entity fixture loading, with fallback to id_companies_active
    # Extract context from params
    # Priority 1: Direct 'company' parameter
    # Priority 2: Extract from 'id_companies_active' SQL format
    if 'company' in params:
        country_code = params['company']
    else:
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
        
        # Priority 2: Try live SQL extraction (JDASH uses dedicated loader only)
        if df is None and item_id != "JDASH":
            try:
                df, zip_path = asyncio.run(
                    pipeline.run_extraction_with_evidence(item_id)
                )
                if pipeline.last_extraction_source == "live":
                    # Keep successful live extractions even when 0 rows are returned.
                    source = "Live Database"
                    logger.info(f"{item_id}: Loaded from {source} ({len(df)} rows)")
                elif pipeline.last_extraction_source == "fixture":
                    if not df.empty:
                        source = "Local Fixture"
                        logger.info(f"{item_id}: Loaded from {source} ({len(df)} rows)")
                    else:
                        df = None
                else:
                    df = None
            except Exception as e:
                logger.warning(f"Live extraction failed for {item_id}: {e}")
                df = None
                zip_path = None
        
        # Priority 3: Fallback to local fixture
        if df is None:
            # Special handling for JDASH - use dedicated loader with company parameter
            if item_id == "JDASH":
                df, jdash_source = load_jdash_data(company=country_code, fixture_fallback=True)
                if not df.empty:
                    source = f"Local Fixture - {jdash_source}"
                    logger.info(f"{item_id}: Loaded via jdash_loader ({len(df)} rows)")
                else:
                    source = "No Data"
                    df = pd.DataFrame()
            else:
                # Use standard fixture loading for other items
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

    # Backward/forward-compatible aliases for split IPE_08 package
    # Issuance alias: IPE_08 <-> IPE_08_ISSUANCE
    if "IPE_08" not in data_store and "IPE_08_ISSUANCE" in data_store:
        data_store["IPE_08"] = data_store["IPE_08_ISSUANCE"]
        evidence_store["IPE_08"] = evidence_store.get("IPE_08_ISSUANCE")
        source_store["IPE_08"] = source_store.get("IPE_08_ISSUANCE", "No Data")
    if "IPE_08_ISSUANCE" not in data_store and "IPE_08" in data_store:
        data_store["IPE_08_ISSUANCE"] = data_store["IPE_08"]
        evidence_store["IPE_08_ISSUANCE"] = evidence_store.get("IPE_08")
        source_store["IPE_08_ISSUANCE"] = source_store.get("IPE_08", "No Data")

    # Usage alias: DOC_VOUCHER_USAGE <-> IPE_08_USAGE
    if "DOC_VOUCHER_USAGE" not in data_store and "IPE_08_USAGE" in data_store:
        data_store["DOC_VOUCHER_USAGE"] = data_store["IPE_08_USAGE"]
        evidence_store["DOC_VOUCHER_USAGE"] = evidence_store.get("IPE_08_USAGE")
        source_store["DOC_VOUCHER_USAGE"] = source_store.get("IPE_08_USAGE", "No Data")
    if "IPE_08_USAGE" not in data_store and "DOC_VOUCHER_USAGE" in data_store:
        data_store["IPE_08_USAGE"] = data_store["DOC_VOUCHER_USAGE"]
        evidence_store["IPE_08_USAGE"] = evidence_store.get("DOC_VOUCHER_USAGE")
        source_store["IPE_08_USAGE"] = source_store.get("DOC_VOUCHER_USAGE", "No Data")
    
    return data_store, evidence_store, source_store


__all__ = [
    'ExtractionPipeline',
    'run_extraction_with_evidence',
    'load_all_data',
]
