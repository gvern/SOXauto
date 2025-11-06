"""
Temporal Workflow for C-PG-1 Reconciliation.

This module defines the main workflow that orchestrates the complete C-PG-1 
reconciliation process by calling activities in the correct sequence.
"""

import logging
from datetime import timedelta
from typing import Dict, Any, Optional
from temporalio import workflow
from src.utils.logging import setup_json_logging
from temporalio.common import RetryPolicy

# Import activity definitions (for type hints)
with workflow.unsafe.imports_passed_through():
    from src.orchestrators.cpg1_activities import (
        execute_ipe_query_activity,
        execute_cr_query_activity,
        calculate_timing_difference_bridge_activity,
        calculate_vtc_adjustment_activity,
        calculate_customer_posting_group_bridge_activity,
        save_evidence_activity,
        classify_bridges_activity,
    )

setup_json_logging()
logger = logging.getLogger(__name__)


# Standard Retry Policy for Database Activities
# This policy provides resilience against transient network or database failures
# (e.g., Teleport tunnel drops, DB timeouts) while avoiding retries on business logic errors
STANDARD_DB_RETRY_POLICY = RetryPolicy(
    maximum_attempts=5,
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(seconds=60),
    backoff_coefficient=2.0,
    non_retryable_error_types=[
        # Business logic and validation errors that should not be retried
        "IPEValidationError",
        "ValueError",
        "KeyError",
        "TypeError",
        # Data issues that indicate code/configuration bugs, not transient failures
        "AttributeError",
    ],
)


@workflow.defn(name="Cpg1Workflow")
class Cpg1Workflow:
    """
    Main workflow for C-PG-1 reconciliation process.
    
    This workflow orchestrates the entire reconciliation by:
    1. Fetching IPE data (customer accounts, collection accounts, etc.)
    2. Fetching CR data (NAV GL entries and balances)
    3. Calculating variance between IPE and CR
    4. Calling classifiers to identify bridges and adjustments
    5. Saving evidence for audit trail
    """
    
    @workflow.run
    async def run(self, workflow_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main workflow execution method.
        
        Args:
            workflow_input: Dictionary containing:
                - cutoff_date: Cutoff date for reconciliation (YYYY-MM-DD)
                - gl_accounts: List of GL accounts to reconcile
                - year_start: Start of year for GL entries (YYYY-MM-DD)
                - year_end: End of year for GL entries (YYYY-MM-DD)
                
        Returns:
            Dictionary with workflow execution results
        """
        workflow.logger.info(f"Starting C-PG-1 workflow with input: {workflow_input}")
        
        # Extract parameters
        cutoff_date = workflow_input.get("cutoff_date")
        gl_accounts = workflow_input.get("gl_accounts", [])
        year_start = workflow_input.get("year_start")
        year_end = workflow_input.get("year_end")
        
        # Results accumulator
        workflow_results = {
            "cutoff_date": cutoff_date,
            "status": "in_progress",
            "ipe_results": {},
            "cr_results": {},
            "bridge_calculations": {},
            "evidence_paths": [],
        }
        
        try:
            # ==============================================================
            # STEP 1: Fetch IPE Data
            # ==============================================================
            workflow.logger.info("STEP 1: Fetching IPE data")
            
            # Common retry policy for transient DB/network errors
            retry = workflow.RetryPolicy(
                initial_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=1),
                maximum_attempts=5,
                non_retryable_error_types=["IPEValidationError"],
            )

            # IPE_07: Customer Accounts
            ipe_07_result = await workflow.execute_activity(
                execute_ipe_query_activity,
                args=["IPE_07", cutoff_date],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["ipe_results"]["IPE_07"] = ipe_07_result
            workflow.logger.info(f"IPE_07 fetched: {ipe_07_result['rows_extracted']} rows")
            
            # IPE_31: Collection Accounts
            ipe_31_result = await workflow.execute_activity(
                execute_ipe_query_activity,
                args=["IPE_31", cutoff_date],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["ipe_results"]["IPE_31"] = ipe_31_result
            workflow.logger.info(f"IPE_31 fetched: {ipe_31_result['rows_extracted']} rows")
            
            # IPE_10: Customer Prepayments
            ipe_10_result = await workflow.execute_activity(
                execute_ipe_query_activity,
                args=["IPE_10", cutoff_date],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["ipe_results"]["IPE_10"] = ipe_10_result
            workflow.logger.info(f"IPE_10 fetched: {ipe_10_result['rows_extracted']} rows")
            
            # IPE_08: Voucher Liabilities
            ipe_08_result = await workflow.execute_activity(
                execute_ipe_query_activity,
                args=["IPE_08", cutoff_date],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["ipe_results"]["IPE_08"] = ipe_08_result
            workflow.logger.info(f"IPE_08 fetched: {ipe_08_result['rows_extracted']} rows")
            
            # ==============================================================
            # STEP 2: Fetch CR Data
            # ==============================================================
            workflow.logger.info("STEP 2: Fetching CR data")
            
            # CR_04: NAV GL Balances
            cr_04_result = await workflow.execute_activity(
                execute_cr_query_activity,
                args=[
                    "CR_04",
                    {
                        "cutoff_date": cutoff_date,
                        "gl_accounts": tuple(gl_accounts),
                    },
                ],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["cr_results"]["CR_04"] = cr_04_result
            workflow.logger.info(f"CR_04 fetched: {cr_04_result['rows_extracted']} rows")
            
            # CR_03: NAV GL Entries
            cr_03_result = await workflow.execute_activity(
                execute_cr_query_activity,
                args=[
                    "CR_03",
                    {
                        "year_start": year_start,
                        "year_end": year_end,
                        "gl_accounts": tuple(gl_accounts),
                    },
                ],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["cr_results"]["CR_03"] = cr_03_result
            workflow.logger.info(f"CR_03 fetched: {cr_03_result['rows_extracted']} rows")
            
            # DOC_VOUCHER_USAGE: Voucher Usage for Timing Bridge
            # Note: id_companies_active parameter needs to be configured based on active companies
            # For now, using empty tuple which may filter out all records.
            # TODO: Load active companies from configuration or environment
            doc_voucher_usage_result = await workflow.execute_activity(
                execute_cr_query_activity,
                args=[
                    "DOC_VOUCHER_USAGE",
                    {
                        "cutoff_date": cutoff_date,
                        "id_companies_active": tuple([]),  # Empty tuple - needs configuration
                    },
                ],
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=STANDARD_DB_RETRY_POLICY,
            )
            workflow_results["cr_results"]["DOC_VOUCHER_USAGE"] = doc_voucher_usage_result
            workflow.logger.info(
                f"DOC_VOUCHER_USAGE fetched: {doc_voucher_usage_result['rows_extracted']} rows"
            )
            
            # ==============================================================
            # STEP 3: Calculate Bridges and Adjustments
            # ==============================================================
            workflow.logger.info("STEP 3: Calculating bridges and adjustments")
            
            # Bridge 1: Customer Posting Group Bridge
            cpg_bridge_result = await workflow.execute_activity(
                calculate_customer_posting_group_bridge_activity,
                args=[ipe_07_result["data"]],
                start_to_close_timeout=timedelta(minutes=10),
            )
            workflow_results["bridge_calculations"]["customer_posting_group"] = cpg_bridge_result
            workflow.logger.info(
                f"Customer Posting Group Bridge: {cpg_bridge_result['problem_customers_count']} customers"
            )
            
            # Bridge 2: Timing Difference Bridge
            # Note: This bridge requires Jdash data which is not yet implemented as an activity.
            # Jdash data is typically exported manually or via a separate process.
            # Using placeholder empty data for now - this will result in no timing differences found.
            # TODO: Implement Jdash data loading activity or document manual export process
            timing_bridge_result = await workflow.execute_activity(
                calculate_timing_difference_bridge_activity,
                args=[
                    {"data": [], "columns": [], "dtypes": {}},  # Placeholder for Jdash data
                    doc_voucher_usage_result["data"],
                ],
                start_to_close_timeout=timedelta(minutes=10),
            )
            workflow_results["bridge_calculations"]["timing_difference"] = timing_bridge_result
            workflow.logger.info(
                f"Timing Difference Bridge: {timing_bridge_result['bridge_amount']}"
            )
            
            # Bridge 3: VTC Adjustment
            vtc_adjustment_result = await workflow.execute_activity(
                calculate_vtc_adjustment_activity,
                args=[
                    ipe_08_result["data"],
                    cr_03_result["data"],
                ],
                start_to_close_timeout=timedelta(minutes=10),
            )
            workflow_results["bridge_calculations"]["vtc_adjustment"] = vtc_adjustment_result
            workflow.logger.info(
                f"VTC Adjustment: {vtc_adjustment_result['adjustment_amount']}"
            )
            
            # ==============================================================
            # STEP 4: Classify Bridges
            # ==============================================================
            workflow.logger.info("STEP 4: Classifying bridges")
            
            # Classify IPE_31 (Collection Accounts) bridges
            classified_ipe_31_result = await workflow.execute_activity(
                classify_bridges_activity,
                args=[ipe_31_result["data"], None],
                start_to_close_timeout=timedelta(minutes=10),
            )
            workflow_results["bridge_calculations"]["classified_ipe_31"] = classified_ipe_31_result
            workflow.logger.info(
                f"IPE_31 Classification: {classified_ipe_31_result['total_rows']} rows classified"
            )
            
            # ==============================================================
            # STEP 5: Save Evidence
            # ==============================================================
            workflow.logger.info("STEP 5: Saving evidence")
            
            # Save bridge calculations evidence
            bridge_evidence_result = await workflow.execute_activity(
                save_evidence_activity,
                args=[
                    "bridge_calculations",
                    {
                        "customer_posting_group": cpg_bridge_result,
                        "timing_difference": timing_bridge_result,
                        "vtc_adjustment": vtc_adjustment_result,
                    },
                    {
                        "cutoff_date": cutoff_date,
                        "workflow_id": workflow.info().workflow_id,
                    },
                ],
                start_to_close_timeout=timedelta(minutes=5),
            )
            workflow_results["evidence_paths"].append(bridge_evidence_result["evidence_path"])
            workflow.logger.info(f"Bridge evidence saved: {bridge_evidence_result['evidence_id']}")
            
            # Save classification evidence
            classification_evidence_result = await workflow.execute_activity(
                save_evidence_activity,
                args=[
                    "bridge_classifications",
                    {
                        "ipe_31_classifications": classified_ipe_31_result["classification_counts"],
                    },
                    {
                        "cutoff_date": cutoff_date,
                        "workflow_id": workflow.info().workflow_id,
                    },
                ],
                start_to_close_timeout=timedelta(minutes=5),
            )
            workflow_results["evidence_paths"].append(
                classification_evidence_result["evidence_path"]
            )
            workflow.logger.info(
                f"Classification evidence saved: {classification_evidence_result['evidence_id']}"
            )
            
            # ==============================================================
            # STEP 6: Finalize Workflow
            # ==============================================================
            workflow_results["status"] = "completed"
            workflow.logger.info("C-PG-1 workflow completed successfully")
            
            return workflow_results
            
        except Exception as e:
            workflow.logger.error(f"Workflow failed with error: {e}")
            workflow_results["status"] = "failed"
            workflow_results["error"] = str(e)
            return workflow_results
