"""
Basic validation tests for Temporal.io orchestration setup.

These tests validate that:
1. Activities are correctly defined with @activity.defn
2. Workflow is correctly defined with @workflow.defn
3. Data serialization/deserialization works correctly
4. Import structure is correct
"""

import pytest
import pandas as pd
from typing import Dict, Any


def test_imports():
    """Test that all Temporal components can be imported."""
    # Test activity imports
    from src.orchestrators.cpg1_activities import (
        execute_ipe_query_activity,
        execute_cr_query_activity,
        calculate_timing_difference_bridge_activity,
        calculate_vtc_adjustment_activity,
        calculate_customer_posting_group_bridge_activity,
        save_evidence_activity,
        classify_bridges_activity,
        dataframe_to_dict,
        dict_to_dataframe,
    )
    
    # Test workflow imports
    from src.orchestrators.cpg1_workflow import Cpg1Workflow
    
    # Verify all imports succeeded
    assert execute_ipe_query_activity is not None
    assert execute_cr_query_activity is not None
    assert calculate_timing_difference_bridge_activity is not None
    assert calculate_vtc_adjustment_activity is not None
    assert calculate_customer_posting_group_bridge_activity is not None
    assert save_evidence_activity is not None
    assert classify_bridges_activity is not None
    assert dataframe_to_dict is not None
    assert dict_to_dataframe is not None
    assert Cpg1Workflow is not None


def test_dataframe_serialization():
    """Test DataFrame serialization and deserialization."""
    from src.orchestrators.cpg1_activities import dataframe_to_dict, dict_to_dataframe
    
    # Create a test DataFrame
    test_data = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"],
        "col3": [1.1, 2.2, 3.3],
    })
    
    # Serialize
    serialized = dataframe_to_dict(test_data)
    
    # Verify serialized structure
    assert isinstance(serialized, dict)
    assert "data" in serialized
    assert "columns" in serialized
    assert "index" in serialized
    assert "dtypes" in serialized
    assert len(serialized["data"]) == 3
    assert serialized["columns"] == ["col1", "col2", "col3"]
    
    # Deserialize
    deserialized = dict_to_dataframe(serialized)
    
    # Verify deserialized DataFrame
    assert isinstance(deserialized, pd.DataFrame)
    assert len(deserialized) == 3
    assert list(deserialized.columns) == ["col1", "col2", "col3"]
    assert deserialized["col1"].tolist() == [1, 2, 3]
    assert deserialized["col2"].tolist() == ["a", "b", "c"]


def test_empty_dataframe_serialization():
    """Test serialization of empty DataFrames."""
    from src.orchestrators.cpg1_activities import dataframe_to_dict, dict_to_dataframe
    
    # Empty DataFrame
    empty_df = pd.DataFrame()
    serialized = dataframe_to_dict(empty_df)
    deserialized = dict_to_dataframe(serialized)
    
    assert isinstance(deserialized, pd.DataFrame)
    assert len(deserialized) == 0
    
    # None DataFrame
    serialized_none = dataframe_to_dict(None)
    deserialized_none = dict_to_dataframe(serialized_none)
    
    assert isinstance(deserialized_none, pd.DataFrame)
    assert len(deserialized_none) == 0


def test_activity_decorators():
    """Test that activities have correct Temporal decorators."""
    from temporalio import activity
    from src.orchestrators.cpg1_activities import (
        execute_ipe_query_activity,
        calculate_timing_difference_bridge_activity,
    )
    
    # Check that activities are properly decorated
    # The @activity.defn decorator adds a __temporal_activity_definition attribute
    assert hasattr(execute_ipe_query_activity, "__temporal_activity_definition")
    assert hasattr(calculate_timing_difference_bridge_activity, "__temporal_activity_definition")


def test_workflow_decorator():
    """Test that workflow has correct Temporal decorator."""
    from temporalio import workflow
    from src.orchestrators.cpg1_workflow import Cpg1Workflow
    
    # Check that workflow class is properly decorated
    # The @workflow.defn decorator adds a __temporal_workflow_definition attribute
    assert hasattr(Cpg1Workflow, "__temporal_workflow_definition")


def test_workflow_run_method():
    """Test that workflow has a run method."""
    from src.orchestrators.cpg1_workflow import Cpg1Workflow
    
    # Verify run method exists
    assert hasattr(Cpg1Workflow, "run")
    assert callable(getattr(Cpg1Workflow, "run"))


def test_activity_signatures():
    """Test that activity functions have expected signatures."""
    import inspect
    from src.orchestrators.cpg1_activities import (
        execute_ipe_query_activity,
        calculate_timing_difference_bridge_activity,
        calculate_vtc_adjustment_activity,
    )
    
    # Check execute_ipe_query_activity signature
    sig1 = inspect.signature(execute_ipe_query_activity)
    assert "ipe_id" in sig1.parameters
    assert "cutoff_date" in sig1.parameters
    
    # Check calculate_timing_difference_bridge_activity signature
    sig2 = inspect.signature(calculate_timing_difference_bridge_activity)
    assert "ipe_08_data" in sig2.parameters
    assert "cutoff_date" in sig2.parameters
    
    # Check calculate_vtc_adjustment_activity signature
    sig3 = inspect.signature(calculate_vtc_adjustment_activity)
    assert "ipe_08_data" in sig3.parameters
    assert "categorized_cr_03_data" in sig3.parameters


def test_core_business_logic_imports():
    """Test that core business logic functions can be imported."""
    # These are the functions that activities wrap
    from src.bridges.classifier import (
        calculate_timing_difference_bridge,
        calculate_vtc_adjustment,
        calculate_customer_posting_group_bridge,
    )
    from src.core.evidence.manager import DigitalEvidenceManager
    
    assert calculate_timing_difference_bridge is not None
    assert calculate_vtc_adjustment is not None
    assert calculate_customer_posting_group_bridge is not None
    assert DigitalEvidenceManager is not None


def test_workflow_starter_imports():
    """Test that workflow starter script can import required modules."""
    # We can't run the full starter (needs Temporal server), but we can test imports
    import sys
    import os
    
    # Add repo root to path (same as starter script does)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    
    # Import what the starter needs
    from temporalio.client import Client
    
    assert Client is not None


def test_worker_script_imports():
    """Test that worker script can import required modules."""
    import sys
    import os
    
    # Add repo root to path (same as worker script does)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    
    # Import what the worker needs
    from temporalio.client import Client
    from temporalio.worker import Worker
    from src.orchestrators.cpg1_workflow import Cpg1Workflow
    
    assert Client is not None
    assert Worker is not None
    assert Cpg1Workflow is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
