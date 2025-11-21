"""
Workflow orchestrator for SOX PG-01 automation process.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple

from src.core.catalog.cpg1 import list_items
from src.utils.aws_utils import initialize_aws_services
from src.core.runners import IPERunnerMSSQL as IPERunner, IPEValidationError, IPEConnectionError
from src.core.evidence import DigitalEvidenceManager

# Configuration from environment
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
S3_RESULTS_BUCKET = os.getenv("S3_RESULTS_BUCKET", "sox-pg01-results")
S3_RESULTS_PREFIX = os.getenv("S3_RESULTS_PREFIX", "extractions/")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Exception raised when the global workflow fails."""
    pass


def execute_ipe_workflow(cutoff_date: str = None, country: str = None) -> Tuple[Dict[str, Any], int]:
    """
    Executes the complete IPE extraction and validation workflow.
    
    Args:
        cutoff_date: Optional cutoff date (format YYYY-MM-DD)
        country: Optional country code (e.g., 'NG', 'KE') for evidence folder naming
        
    Returns:
        Tuple containing (results, HTTP_status_code)
    """
    workflow_start_time = datetime.now()
    logger.info("===== STARTING SOX PG-01 AUTOMATION WORKFLOW =====")
    
    # Global workflow results
    ipe_configs = list_items()
    workflow_results = {
        'workflow_id': f"SOXauto_PG01_{workflow_start_time.strftime('%Y%m%d_%H%M%S')}",
        'start_time': workflow_start_time.isoformat(),
        'cutoff_date': cutoff_date,
        'ipe_results': {},
        'summary': {
            'total_ipes': len(ipe_configs),
            'successful_ipes': 0,
            'failed_ipes': 0,
            'total_rows_processed': 0
        }
    }
    
    try:
        # 1. Initialize AWS services and evidence manager
        logger.info("Initializing AWS services...")
        secrets_manager, s3_client = initialize_aws_services(AWS_REGION)
        
        # Create SOX evidence manager
        evidence_manager = DigitalEvidenceManager("evidence_sox_pg01")
        
        # 2. Process each IPE
        for ipe_config in ipe_configs:
            ipe_id = ipe_config['id']
            ipe_result = {
                'status': 'PENDING',
                'start_time': datetime.now().isoformat(),
                'rows_extracted': 0,
                'validation_summary': {},
                'error_message': None
            }
            
            try:
                logger.info(f"--- Processing IPE: {ipe_id} ---")
                
                # Extract country and period from cutoff_date if available
                # Try to get country from parameter, environment variable, or leave as None
                ipe_country = country or os.getenv('COUNTRY_CODE')
                period = None
                if cutoff_date:
                    try:
                        dt = datetime.strptime(cutoff_date, '%Y-%m-%d')
                        period = dt.strftime('%Y%m')
                    except ValueError:
                        logger.warning(f"Invalid cutoff_date format for IPE {ipe_id}: '{cutoff_date}'. Expected 'YYYY-MM-DD'. Setting period to None.")
                
                # Create and execute IPE runner with SOX evidence
                runner = IPERunner(
                    ipe_config=ipe_config,
                    secret_manager=secrets_manager,
                    cutoff_date=cutoff_date,
                    evidence_manager=evidence_manager,
                    country=ipe_country,
                    period=period,
                    full_params={
                        'cutoff_date': cutoff_date
                    }
                )
                
                # Execute extraction and validation
                validated_data = runner.run()
                
                # Store results in S3 as parquet
                s3_key = f"{S3_RESULTS_PREFIX}/{ipe_id.lower()}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                s3_client.write_dataframe_to_s3(
                    dataframe=validated_data,
                    bucket=S3_RESULTS_BUCKET,
                    key=s3_key
                )
                
                # Update results
                ipe_result.update({
                    'status': 'SUCCESS',
                    'end_time': datetime.now().isoformat(),
                    'rows_extracted': len(validated_data),
                    'validation_summary': runner.get_validation_summary(),
                    's3_location': f"s3://{S3_RESULTS_BUCKET}/{s3_key}"
                })
                
                workflow_results['summary']['successful_ipes'] += 1
                workflow_results['summary']['total_rows_processed'] += len(validated_data)
                
                logger.info(f"IPE {ipe_id} processed successfully - {len(validated_data)} rows")
                
            except (IPEValidationError, IPEConnectionError) as e:
                ipe_result.update({
                    'status': 'FAILED',
                    'end_time': datetime.now().isoformat(),
                    'error_message': str(e)
                })
                workflow_results['summary']['failed_ipes'] += 1
                
                logger.error(f"IPE {ipe_id} processing failed: {e}")
                
                # In case of critical failure, stop workflow
                workflow_results['end_time'] = datetime.now().isoformat()
                workflow_results['overall_status'] = 'FAILED'
                workflow_results['failure_reason'] = f"Critical failure on IPE {ipe_id}"
                
                # Send alert (to be implemented according to your needs)
                _send_failure_alert(workflow_results)
                
                return workflow_results, 500
                
            except Exception as e:
                ipe_result.update({
                    'status': 'ERROR',
                    'end_time': datetime.now().isoformat(),
                    'error_message': f"Unexpected error: {str(e)}"
                })
                workflow_results['summary']['failed_ipes'] += 1
                
                logger.error(f"Unexpected error processing IPE {ipe_id}: {e}")
                
                # Continue with other IPEs in case of non-critical error
                
            finally:
                workflow_results['ipe_results'][ipe_id] = ipe_result
        
        # 3. Finalize workflow
        workflow_results['end_time'] = datetime.now().isoformat()
        
        if workflow_results['summary']['failed_ipes'] == 0:
            workflow_results['overall_status'] = 'SUCCESS'
            logger.info("===== WORKFLOW COMPLETED SUCCESSFULLY =====")
            
            # Create complete audit log
            _create_audit_log(secrets_manager, s3_client, workflow_results)
            
            return workflow_results, 200
        else:
            workflow_results['overall_status'] = 'PARTIAL_SUCCESS'
            logger.warning("===== WORKFLOW COMPLETED WITH PARTIAL FAILURES =====")
            return workflow_results, 206  # Partial Content
            
    except Exception as e:
        workflow_results.update({
            'end_time': datetime.now().isoformat(),
            'overall_status': 'ERROR',
            'error_message': f"Fatal workflow error: {str(e)}"
        })
        
        logger.error(f"Fatal workflow error: {e}")
        _send_failure_alert(workflow_results)
        
        return workflow_results, 500


def _send_failure_alert(workflow_results: Dict[str, Any]) -> None:
    """
    Sends an alert in case of workflow failure.
    To be adapted according to your needs (email, Slack, etc.)
    """
    try:
        # Placeholder for alert sending
        # You can implement email sending, Slack notifications, etc. here
        logger.critical("ALERT: SOX PG-01 workflow failure")
        logger.critical(f"Details: {json.dumps(workflow_results, indent=2)}")
        
        # Example of future implementation:
        # send_email_alert(workflow_results)
        # send_slack_notification(workflow_results)
        
    except Exception as e:
        logger.error(f"Error sending alert: {e}")


def _create_audit_log(secrets_manager, s3_client, workflow_results: Dict[str, Any]) -> None:
    """
    Creates a complete audit log of the workflow and stores it in S3.
    """
    try:
        # Store audit log in S3
        audit_log_key = f"audit-logs/{workflow_results['workflow_id']}.json"
        s3_client.upload_json_to_s3(
            data=workflow_results,
            bucket=S3_RESULTS_BUCKET,
            key=audit_log_key
        )
        logger.info(f"Audit log stored in S3: s3://{S3_RESULTS_BUCKET}/{audit_log_key}")
        
        # Local log as backup
        logger.info(f"Workflow summary: {json.dumps(workflow_results['summary'], indent=2)}")
        
    except Exception as e:
        logger.error(f"Error creating audit log: {e}")
