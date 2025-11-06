"""
Temporal Activities for C-PG-1 Workflow.

This module wraps core business logic functions as Temporal activities.
Activities are the building blocks that workflows call to perform actual work.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from temporalio import activity

# Import core business logic
from src.core.runners.mssql_runner import IPERunner
from src.bridges.classifier import (
    calculate_timing_difference_bridge,
    calculate_vtc_adjustment,
    calculate_customer_posting_group_bridge,
)
from src.core.evidence.manager import DigitalEvidenceManager

logger = logging.getLogger(__name__)


# Data Serialization Helpers
def dataframe_to_dict(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Serialize a pandas DataFrame to a JSON-compatible dictionary.
    
    Args:
        df: DataFrame to serialize
        
    Returns:
        Dictionary with data and metadata
    """
    if df is None or df.empty:
        return {"data": [], "columns": [], "index": [], "dtypes": {}}
    
    return {
        "data": df.to_dict(orient="records"),
        "columns": df.columns.tolist(),
        "index": df.index.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


def dict_to_dataframe(data_dict: Dict[str, Any]) -> pd.DataFrame:
    """
    Deserialize a dictionary back to a pandas DataFrame.
    
    Args:
        data_dict: Dictionary containing DataFrame data
        
    Returns:
        Reconstructed DataFrame
    """
    if not data_dict or not data_dict.get("data"):
        return pd.DataFrame()
    
    df = pd.DataFrame(data_dict["data"])
    
    # Restore column order if available
    if data_dict.get("columns"):
        df = df[data_dict["columns"]]
    
    # Restore data types if available
    if data_dict.get("dtypes"):
        for col, dtype in data_dict["dtypes"].items():
            if col in df.columns:
                try:
                    df[col] = df[col].astype(dtype)
                except (ValueError, TypeError):
                    logger.warning(f"Could not restore dtype {dtype} for column {col}")
    
    return df


@activity.defn(name="execute_ipe_query")
async def execute_ipe_query_activity(
    ipe_id: str,
    cutoff_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute an IPE query using the IPERunner.
    
    Args:
        ipe_id: IPE identifier (e.g., "IPE_07", "IPE_31")
        cutoff_date: Optional cutoff date for the query (YYYY-MM-DD)
        
    Returns:
        Dictionary containing:
        - data: Serialized DataFrame
        - validation_results: Validation summary
        - evidence_path: Path to evidence package
    """
    activity_logger = activity.logger
    activity_logger.info(f"Executing IPE query for {ipe_id} with cutoff_date={cutoff_date}")
    
    try:
        # Import here to avoid circular dependencies
        from src.core.catalog.cpg1 import get_item_by_id
        from src.utils.aws_utils import AWSSecretsManager
        
        # Get IPE configuration
        ipe_config = get_item_by_id(ipe_id)
        if not ipe_config:
            raise ValueError(f"IPE {ipe_id} not found in catalog")
        
        # Convert CatalogItem to dict format expected by IPERunner
        # Note: IPERunner validation queries are not defined in the catalog yet.
        # For now, we disable validation checks by setting them to None.
        # When validation queries are added to the catalog, they should be passed here.
        ipe_config_dict = {
            "id": ipe_config.item_id,
            "description": ipe_config.title,
            "main_query": ipe_config.sql_query,
            "secret_name": "nav-db-connection",  # Default secret name
            "validation": {
                "completeness_query": None,  # TODO: Add to catalog when validation queries are defined
                "accuracy_positive_query": None,  # TODO: Add to catalog when validation queries are defined
                "accuracy_negative_query": None,  # TODO: Add to catalog when validation queries are defined
            }
        }
        
        # Initialize secrets manager (will use env var fallback if AWS not available)
        secrets_manager = AWSSecretsManager()
        
        # Initialize evidence manager
        evidence_manager = DigitalEvidenceManager("evidence")
        
        # Create and run IPE runner
        runner = IPERunner(
            ipe_config=ipe_config_dict,
            secret_manager=secrets_manager,
            cutoff_date=cutoff_date,
            evidence_manager=evidence_manager
        )
        
        # Execute query
        df = runner.run()
        
        # Serialize result
        result = {
            "data": dataframe_to_dict(df),
            "validation_results": runner.get_validation_summary(),
            "evidence_path": None,  # Evidence path is in validation_results
            "ipe_id": ipe_id,
            "rows_extracted": len(df),
        }
        
        activity_logger.info(f"Successfully executed {ipe_id}: {len(df)} rows")
        return result
        
    except Exception as e:
        activity_logger.error(f"Error executing IPE {ipe_id}: {e}")
        raise


@activity.defn(name="execute_cr_query")
async def execute_cr_query_activity(
    cr_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a CR (Custom Report) query.
    
    Args:
        cr_id: CR identifier (e.g., "CR_03", "CR_04")
        parameters: Query parameters (e.g., cutoff_date, gl_accounts)
        
    Returns:
        Dictionary containing serialized DataFrame
    """
    activity_logger = activity.logger
    activity_logger.info(f"Executing CR query for {cr_id} with parameters={parameters}")
    
    try:
        from src.core.catalog.cpg1 import get_item_by_id
        from src.utils.sql_template import render_sql
        import pyodbc
        import os
        
        # Get CR configuration
        cr_config = get_item_by_id(cr_id)
        if not cr_config:
            raise ValueError(f"CR {cr_id} not found in catalog")
        
        if not cr_config.sql_query:
            raise ValueError(f"CR {cr_id} has no SQL query defined")
        
        # Render SQL with parameters
        rendered_query = render_sql(cr_config.sql_query, parameters)
        
        # Get database connection
        connection_string = os.getenv("DB_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("DB_CONNECTION_STRING environment variable not set")
        
        # Execute query
        with pyodbc.connect(connection_string) as conn:
            df = pd.read_sql(rendered_query, conn)
        
        activity_logger.info(f"Successfully executed {cr_id}: {len(df)} rows")
        
        return {
            "data": dataframe_to_dict(df),
            "cr_id": cr_id,
            "rows_extracted": len(df),
        }
        
    except Exception as e:
        activity_logger.error(f"Error executing CR {cr_id}: {e}")
        raise


@activity.defn(name="calculate_timing_difference_bridge")
async def calculate_timing_difference_bridge_activity(
    jdash_data: Dict[str, Any],
    doc_voucher_usage_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate timing difference bridge between Jdash and DOC_VOUCHER_USAGE.
    
    Args:
        jdash_data: Serialized Jdash DataFrame
        doc_voucher_usage_data: Serialized DOC_VOUCHER_USAGE DataFrame
        
    Returns:
        Dictionary with bridge_amount and proof data
    """
    activity_logger = activity.logger
    activity_logger.info("Calculating timing difference bridge")
    
    try:
        # Deserialize inputs
        jdash_df = dict_to_dataframe(jdash_data)
        doc_voucher_usage_df = dict_to_dataframe(doc_voucher_usage_data)
        
        # Call core business logic
        bridge_amount, proof_df = calculate_timing_difference_bridge(
            jdash_df, doc_voucher_usage_df
        )
        
        activity_logger.info(f"Timing difference bridge calculated: {bridge_amount}")
        
        return {
            "bridge_amount": float(bridge_amount),
            "proof_data": dataframe_to_dict(proof_df),
            "variance_count": len(proof_df),
        }
        
    except Exception as e:
        activity_logger.error(f"Error calculating timing difference bridge: {e}")
        raise


@activity.defn(name="calculate_vtc_adjustment")
async def calculate_vtc_adjustment_activity(
    ipe_08_data: Dict[str, Any],
    categorized_cr_03_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate VTC (Voucher to Cash) adjustment.
    
    Args:
        ipe_08_data: Serialized IPE_08 DataFrame
        categorized_cr_03_data: Optional serialized categorized CR_03 DataFrame
        
    Returns:
        Dictionary with adjustment_amount and proof data
    """
    activity_logger = activity.logger
    activity_logger.info("Calculating VTC adjustment")
    
    try:
        # Deserialize inputs
        ipe_08_df = dict_to_dataframe(ipe_08_data)
        categorized_cr_03_df = (
            dict_to_dataframe(categorized_cr_03_data)
            if categorized_cr_03_data
            else None
        )
        
        # Call core business logic
        adjustment_amount, proof_df = calculate_vtc_adjustment(
            ipe_08_df, categorized_cr_03_df
        )
        
        activity_logger.info(f"VTC adjustment calculated: {adjustment_amount}")
        
        return {
            "adjustment_amount": float(adjustment_amount),
            "proof_data": dataframe_to_dict(proof_df),
            "unmatched_count": len(proof_df),
        }
        
    except Exception as e:
        activity_logger.error(f"Error calculating VTC adjustment: {e}")
        raise


@activity.defn(name="calculate_customer_posting_group_bridge")
async def calculate_customer_posting_group_bridge_activity(
    ipe_07_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate customer posting group bridge (identifies posting group inconsistencies).
    
    Args:
        ipe_07_data: Serialized IPE_07 DataFrame
        
    Returns:
        Dictionary with bridge_amount and proof data
    """
    activity_logger = activity.logger
    activity_logger.info("Calculating customer posting group bridge")
    
    try:
        # Deserialize input
        ipe_07_df = dict_to_dataframe(ipe_07_data)
        
        # Call core business logic
        bridge_amount, proof_df = calculate_customer_posting_group_bridge(ipe_07_df)
        
        activity_logger.info(
            f"Customer posting group bridge calculated: {bridge_amount}, "
            f"found {len(proof_df)} customers with multiple posting groups"
        )
        
        return {
            "bridge_amount": float(bridge_amount),
            "proof_data": dataframe_to_dict(proof_df),
            "problem_customers_count": len(proof_df),
        }
        
    except Exception as e:
        activity_logger.error(f"Error calculating customer posting group bridge: {e}")
        raise


@activity.defn(name="save_evidence")
async def save_evidence_activity(
    evidence_type: str,
    evidence_data: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Save evidence for audit trail.
    
    Args:
        evidence_type: Type of evidence (e.g., "bridge", "adjustment", "validation")
        evidence_data: Evidence data to save
        metadata: Additional metadata for the evidence
        
    Returns:
        Dictionary with evidence_path and confirmation
    """
    activity_logger = activity.logger
    activity_logger.info(f"Saving evidence: {evidence_type}")
    
    try:
        # Initialize evidence manager
        evidence_manager = DigitalEvidenceManager("evidence")
        
        # Create evidence package
        execution_metadata = {
            "evidence_type": evidence_type,
            "timestamp": datetime.now().isoformat(),
            **metadata,
        }
        
        evidence_id = f"{evidence_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        evidence_dir = evidence_manager.create_evidence_package(
            evidence_id, execution_metadata
        )
        
        # Save evidence data as JSON
        import json
        import os
        evidence_file = os.path.join(evidence_dir, "evidence_data.json")
        with open(evidence_file, "w") as f:
            json.dump(evidence_data, f, indent=2, default=str)
        
        activity_logger.info(f"Evidence saved to {evidence_dir}")
        
        return {
            "evidence_path": evidence_dir,
            "evidence_id": evidence_id,
            "status": "success",
        }
        
    except Exception as e:
        activity_logger.error(f"Error saving evidence: {e}")
        raise


@activity.defn(name="classify_bridges")
async def classify_bridges_activity(
    dataframe_data: Dict[str, Any],
    rules_config: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Apply bridge classification rules to data.
    
    Args:
        dataframe_data: Serialized DataFrame to classify
        rules_config: Optional bridge rules configuration
        
    Returns:
        Dictionary with classified data
    """
    activity_logger = activity.logger
    activity_logger.info("Classifying bridges")
    
    try:
        from src.bridges.classifier import classify_bridges
        from src.bridges.catalog import load_rules
        
        # Deserialize input
        df = dict_to_dataframe(dataframe_data)
        
        # Load rules
        rules = load_rules() if rules_config is None else rules_config
        
        # Apply classification
        classified_df = classify_bridges(df, rules)
        
        # Count classifications
        classification_counts = classified_df["bridge_key"].value_counts(dropna=False).to_dict()
        
        activity_logger.info(f"Classified {len(classified_df)} rows into {len(classification_counts)} bridge categories")
        
        return {
            "data": dataframe_to_dict(classified_df),
            "classification_counts": classification_counts,
            "total_rows": len(classified_df),
        }
        
    except Exception as e:
        activity_logger.error(f"Error classifying bridges: {e}")
        raise
