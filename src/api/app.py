"""
API layer for SOX PG-01 automation process.
Compatible with AWS Lambda (via handler) and ECS (as a Flask app).
"""

import logging
import os
from datetime import datetime
from flask import Flask, request

from src.core.catalog.cpg1 import list_items
from src.orchestrators.workflow import execute_ipe_workflow

# Configuration from environment
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask initialization
app = Flask(__name__)


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
        country = request_data.get('country')
        
        # Execute workflow
        results, status_code = execute_ipe_workflow(cutoff_date, country)
        
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
        'configured_ipes': [
            {
                'id': ipe['id'],
                'description': ipe['description']
            }
            for ipe in list_items()
        ],
        'total_ipes': len(list_items())
    }
    return config_info, 200
