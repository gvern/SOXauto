# main.py
"""
Main orchestrator for SOX PG-01 automation process.
Entry point compatible with AWS Lambda and ECS.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Tuple
from flask import Flask, request

from src.core.legacy.config import (
    AWS_REGION,
    IPE_CONFIGS, 
    ATHENA_DATABASE,
    ATHENA_OUTPUT_LOCATION,
    S3_RESULTS_BUCKET,
    S3_RESULTS_PREFIX
)
from src.utils.aws_utils import initialize_aws_services
from src.core.runners import IPERunnerMSSQL as IPERunner, IPEValidationError, IPEConnectionError
from src.core.evidence import DigitalEvidenceManager

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask initialization for Cloud Run
app = Flask(__name__)


class WorkflowExecutionError(Exception):
    """Exception raised when the global workflow fails."""
    pass


def execute_ipe_workflow(cutoff_date: str = None) -> Tuple[Dict[str, Any], int]:
    """
    Executes the complete IPE extraction and validation workflow.
    
    Args:
        cutoff_date: Optional cutoff date (format YYYY-MM-DD)
        
    Returns:
        Tuple containing (results, HTTP_status_code)
    """
    workflow_start_time = datetime.now()
    logger.info("===== STARTING SOX PG-01 AUTOMATION WORKFLOW =====")
    
    # Global workflow results
    workflow_results = {
        'workflow_id': f"SOXauto_PG01_{workflow_start_time.strftime('%Y%m%d_%H%M%S')}",
        'start_time': workflow_start_time.isoformat(),
        'cutoff_date': cutoff_date,
        'ipe_results': {},
        'summary': {
            'total_ipes': len(IPE_CONFIGS),
            'successful_ipes': 0,
            'failed_ipes': 0,
            'total_rows_processed': 0
        }
    }
    
    try:
        # 1. Initialize AWS services and evidence manager
        logger.info("Initializing AWS services...")
        secrets_manager, s3_client, athena_client = initialize_aws_services(AWS_REGION)
        
        # Create SOX evidence manager
        evidence_manager = DigitalEvidenceManager("evidence_sox_pg01")
        
        # 2. Process each IPE
        for ipe_config in IPE_CONFIGS:
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
                
                # Create and execute IPE runner with SOX evidence
                runner = IPERunner(
                    ipe_config=ipe_config,
                    secret_manager=secrets_manager,
                    cutoff_date=cutoff_date,
                    evidence_manager=evidence_manager
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


@app.route('/', methods=['POST'])
def lambda_handler():
    """
    Entry point for AWS Lambda and ECS.
    Accepts HTTP POST requests with optional parameters.
    """
    try:
        # Retrieve request parameters
        request_data = request.get_json() or {}
        cutoff_date = request_data.get('cutoff_date')
        
        # Execute workflow
        results, status_code = execute_ipe_workflow(cutoff_date)
        
        return results, status_code
        
    except Exception as e:
        error_response = {
            'error': 'Internal server error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }
        logger.error(f"Lambda handler error: {e}")
        return error_response, 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for AWS ECS/Lambda."""
    return {
        'status': 'healthy',
        'service': 'SOXauto-PG01',
        'timestamp': datetime.now().isoformat()
    }, 200


@app.route('/config', methods=['GET'])
def get_configuration():
    """Returns current configuration (without secrets)."""
    config_info = {
        'aws_region': AWS_REGION,
        'athena_database': ATHENA_DATABASE,
        'configured_ipes': [
            {
                'id': ipe['id'],
                'description': ipe['description']
            }
            for ipe in IPE_CONFIGS
        ],
        'total_ipes': len(IPE_CONFIGS)
    }
    return config_info, 200


def main_workflow_local(cutoff_date: str = None):
    """
    Entry point for local execution (development/test).
    
    Args:
        cutoff_date: Optional cutoff date
    """
    results, status = execute_ipe_workflow(cutoff_date)
    
    print("\n" + "="*60)
    print("SOX PG-01 WORKFLOW RESULTS")
    print("="*60)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    print("="*60)
    
    return results


if __name__ == "__main__":
    # Local execution for development
    import sys
    
    cutoff_date_param = None
    if len(sys.argv) > 1:
        cutoff_date_param = sys.argv[1]
    
    try:
        main_workflow_local(cutoff_date_param)
    except KeyboardInterrupt:
        logger.info("Workflow interrupted by user")
    except Exception as e:
        logger.error(f"Error during local execution: {e}")
        sys.exit(1)