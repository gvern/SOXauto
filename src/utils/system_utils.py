"""
System utility functions for SOXauto PG-01.
Provides system information like git version, hostname, etc.
"""

import subprocess
import socket
import sys
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_git_commit_hash() -> str:
    """
    Retrieves the current Git commit hash (short version).
    
    Returns:
        Short Git commit hash (7 characters) or 'unknown' if not in a git repository
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        commit_hash = result.stdout.strip()
        logger.debug(f"Git commit hash retrieved: {commit_hash}")
        return commit_hash
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.warning(f"Could not retrieve git commit hash: {e}")
        return "unknown"


def get_execution_host() -> str:
    """
    Retrieves the hostname of the machine running the script.
    
    Returns:
        Hostname of the execution machine
    """
    try:
        hostname = socket.gethostname()
        return hostname
    except Exception as e:
        logger.warning(f"Could not retrieve hostname: {e}")
        return "unknown"


def get_python_version() -> str:
    """
    Retrieves the Python version.
    
    Returns:
        Python version string
    """
    return sys.version


def get_system_context() -> Dict[str, Any]:
    """
    Retrieves comprehensive system context information.
    
    Returns:
        Dictionary containing git commit, hostname, Python version, and runner version
    """
    return {
        'git_commit_id': get_git_commit_hash(),
        'execution_host': get_execution_host(),
        'python_version': get_python_version(),
        'runner_version': 'SOXauto v1.0'
    }
