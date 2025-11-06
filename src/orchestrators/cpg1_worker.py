#!/usr/bin/env python3
"""
Temporal Worker for C-PG-1 Workflows.

This script starts a Temporal worker that listens for workflow and activity tasks
from the Temporal server. It registers the Cpg1Workflow and all associated activities.

Usage:
    python src/orchestrators/cpg1_worker.py

Environment Variables:
    TEMPORAL_HOST: Temporal server host (default: localhost:7233)
    TEMPORAL_NAMESPACE: Temporal namespace (default: default)
    TEMPORAL_TASK_QUEUE: Task queue name (default: cpg1-task-queue)
"""

import asyncio
import logging
import os
import sys

# Add repo root to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from temporalio.client import Client
from temporalio.worker import Worker

# Import workflow and activities
from src.orchestrators.cpg1_workflow import Cpg1Workflow
from src.orchestrators.cpg1_activities import (
    execute_ipe_query_activity,
    execute_cr_query_activity,
    calculate_timing_difference_bridge_activity,
    calculate_vtc_adjustment_activity,
    calculate_customer_posting_group_bridge_activity,
    save_evidence_activity,
    classify_bridges_activity,
)

# Configure structured JSON logging
from src.core.logging_config import setup_logging

setup_logging(level=logging.INFO, format_as_json=True)
logger = logging.getLogger(__name__)


async def main():
    """
    Start the Temporal worker.
    """
    # Get configuration from environment
    temporal_host = os.getenv("TEMPORAL_HOST", "localhost:7233")
    temporal_namespace = os.getenv("TEMPORAL_NAMESPACE", "default")
    task_queue = os.getenv("TEMPORAL_TASK_QUEUE", "cpg1-task-queue")
    
    logger.info(f"Connecting to Temporal server at {temporal_host}")
    logger.info(f"Namespace: {temporal_namespace}")
    logger.info(f"Task queue: {task_queue}")
    
    try:
        # Connect to Temporal server
        client = await Client.connect(
            temporal_host,
            namespace=temporal_namespace,
        )
        
        logger.info("Connected to Temporal server")
        
        # Create worker
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[Cpg1Workflow],
            activities=[
                execute_ipe_query_activity,
                execute_cr_query_activity,
                calculate_timing_difference_bridge_activity,
                calculate_vtc_adjustment_activity,
                calculate_customer_posting_group_bridge_activity,
                save_evidence_activity,
                classify_bridges_activity,
            ],
        )
        
        logger.info("Worker created successfully")
        logger.info("Registered workflows: Cpg1Workflow")
        logger.info("Registered activities:")
        logger.info("  - execute_ipe_query")
        logger.info("  - execute_cr_query")
        logger.info("  - calculate_timing_difference_bridge")
        logger.info("  - calculate_vtc_adjustment")
        logger.info("  - calculate_customer_posting_group_bridge")
        logger.info("  - save_evidence")
        logger.info("  - classify_bridges")
        
        # Start worker (this blocks until interrupted)
        logger.info("Starting worker... (Press Ctrl+C to stop)")
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info("Worker stopped by user")
    except Exception as e:
        logger.error(f"Worker failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
