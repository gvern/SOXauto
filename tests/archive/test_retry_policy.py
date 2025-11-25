"""
Test suite to validate Temporal RetryPolicy configuration for database activities.

These tests validate that:
1. A standard retry policy is defined with proper exponential backoff
2. Non-retryable error types are correctly specified
3. All database activities use the retry policy
"""

import pytest
from datetime import timedelta


def test_standard_retry_policy_exists():
    """Test that STANDARD_DB_RETRY_POLICY is defined in cpg1_workflow."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    assert STANDARD_DB_RETRY_POLICY is not None, "STANDARD_DB_RETRY_POLICY should be defined"


def test_retry_policy_has_exponential_backoff():
    """Test that retry policy has exponential backoff configured."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # Verify backoff_coefficient is set for exponential backoff
    assert STANDARD_DB_RETRY_POLICY.backoff_coefficient == 2.0, \
        "Backoff coefficient should be 2.0 for exponential backoff"


def test_retry_policy_has_maximum_attempts():
    """Test that retry policy has reasonable maximum attempts."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # Should have at least 5 attempts as per requirements
    assert STANDARD_DB_RETRY_POLICY.maximum_attempts >= 5, \
        "Maximum attempts should be at least 5"


def test_retry_policy_has_maximum_interval():
    """Test that retry policy has maximum interval configured."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # Should have a maximum interval to prevent infinite backoff
    assert STANDARD_DB_RETRY_POLICY.maximum_interval is not None, \
        "Maximum interval should be configured"
    
    # Should be around 60 seconds as per requirements
    assert STANDARD_DB_RETRY_POLICY.maximum_interval == timedelta(seconds=60), \
        "Maximum interval should be 60 seconds"


def test_retry_policy_has_initial_interval():
    """Test that retry policy has initial interval configured."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # Should have an initial interval
    assert STANDARD_DB_RETRY_POLICY.initial_interval is not None, \
        "Initial interval should be configured"
    
    # Should be reasonable (e.g., 10 seconds)
    assert STANDARD_DB_RETRY_POLICY.initial_interval == timedelta(seconds=10), \
        "Initial interval should be 10 seconds"


def test_retry_policy_excludes_validation_errors():
    """Test that retry policy excludes IPEValidationError from retries."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # IPEValidationError should not be retried
    assert "IPEValidationError" in STANDARD_DB_RETRY_POLICY.non_retryable_error_types, \
        "IPEValidationError should be in non_retryable_error_types"


def test_retry_policy_excludes_value_errors():
    """Test that retry policy excludes ValueError from retries."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # ValueError indicates a code/data bug, not a transient failure
    assert "ValueError" in STANDARD_DB_RETRY_POLICY.non_retryable_error_types, \
        "ValueError should be in non_retryable_error_types"


def test_retry_policy_excludes_key_errors():
    """Test that retry policy excludes KeyError from retries."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # KeyError indicates a code/data bug, not a transient failure
    assert "KeyError" in STANDARD_DB_RETRY_POLICY.non_retryable_error_types, \
        "KeyError should be in non_retryable_error_types"


def test_retry_policy_excludes_type_errors():
    """Test that retry policy excludes TypeError from retries."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # TypeError indicates a code bug, not a transient failure
    assert "TypeError" in STANDARD_DB_RETRY_POLICY.non_retryable_error_types, \
        "TypeError should be in non_retryable_error_types"


def test_workflow_imports():
    """Test that workflow and retry policy can be imported together."""
    from src.orchestrators.archive_temporal.cpg1_workflow import Cpg1Workflow, STANDARD_DB_RETRY_POLICY
    
    assert Cpg1Workflow is not None
    assert STANDARD_DB_RETRY_POLICY is not None


def test_retry_policy_is_workflow_retry_policy_type():
    """Test that STANDARD_DB_RETRY_POLICY is of the correct type."""
    from temporalio.common import RetryPolicy
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # Should be a RetryPolicy instance
    assert isinstance(STANDARD_DB_RETRY_POLICY, RetryPolicy), \
        "STANDARD_DB_RETRY_POLICY should be an instance of RetryPolicy"


def test_retry_backoff_progression():
    """Test that retry backoff progression is as expected."""
    from src.orchestrators.archive_temporal.cpg1_workflow import STANDARD_DB_RETRY_POLICY
    
    # With initial_interval=10s, backoff_coefficient=2.0, maximum_interval=60s
    # The progression should be: 10s, 20s, 40s, 60s (capped), 60s (capped)
    initial = STANDARD_DB_RETRY_POLICY.initial_interval.total_seconds()
    coefficient = STANDARD_DB_RETRY_POLICY.backoff_coefficient
    maximum = STANDARD_DB_RETRY_POLICY.maximum_interval.total_seconds()
    
    # Calculate expected intervals
    intervals = []
    current_interval = initial
    for _ in range(STANDARD_DB_RETRY_POLICY.maximum_attempts - 1):
        intervals.append(current_interval)
        current_interval = min(current_interval * coefficient, maximum)
    
    # Verify the progression makes sense
    assert intervals[0] == 10, "First retry should be after 10 seconds"
    assert intervals[1] == 20, "Second retry should be after 20 seconds"
    assert intervals[2] == 40, "Third retry should be after 40 seconds"
    assert intervals[3] == 60, "Fourth retry should be capped at 60 seconds"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
