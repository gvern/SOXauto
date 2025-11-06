"""
Test suite to audit orchestrator scripts for compliance with core architecture.

These tests validate that:
1. run_full_reconciliation.py uses validated catalog and classifier
2. run_demo.py uses validated catalog and classifier
3. No hardcoded SQL queries exist in orchestrator scripts
"""
import os
import sys
import ast
import importlib
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)


def get_script_ast(script_name):
    """Parse a script file and return its AST."""
    script_path = os.path.join(REPO_ROOT, "scripts", f"{script_name}.py")
    with open(script_path, "r") as f:
        content = f.read()
    return ast.parse(content, filename=script_name)


def get_imports_from_ast(tree):
    """Extract all imports from an AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append(f"{module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
    return imports


def has_string_literal_with_sql(tree):
    """Check if AST contains string literals that look like SQL queries."""
    sql_keywords = ["SELECT ", "INSERT ", "UPDATE ", "DELETE ", "FROM ["]
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value_upper = node.value.upper()
            # Check if it's a multi-line SQL-looking string
            if any(keyword in value_upper for keyword in sql_keywords):
                # Exclude comments or documentation
                if not node.value.strip().startswith("#") and not node.value.strip().startswith("--"):
                    return True
    return False


class TestRunFullReconciliation:
    """Tests for scripts/run_full_reconciliation.py"""

    def test_no_hardcoded_sql(self):
        """Verify no hardcoded SQL queries in run_full_reconciliation.py"""
        tree = get_script_ast("run_full_reconciliation")
        has_sql = has_string_literal_with_sql(tree)
        assert not has_sql, "run_full_reconciliation.py should not contain hardcoded SQL queries"

    def test_calls_compliant_subscripts(self):
        """Verify run_full_reconciliation.py calls scripts that use catalog"""
        # The scripts it calls should all use the catalog
        with open(os.path.join(REPO_ROOT, "scripts", "run_full_reconciliation.py"), "r") as f:
            content = f.read()
        
        # Verify it calls the expected subscripts
        assert "generate_customer_accounts.py" in content
        assert "generate_collection_accounts.py" in content
        assert "generate_other_ar.py" in content
        assert "classify_bridges.py" in content


class TestRunDemo:
    """Tests for scripts/run_demo.py"""

    def test_imports_mssql_runner(self):
        """Verify run_demo.py imports IPERunner (MSSQL runner)"""
        tree = get_script_ast("run_demo")
        imports = get_imports_from_ast(tree)
        
        has_runner = any("IPERunner" in imp for imp in imports)
        assert has_runner, "run_demo.py should import IPERunner from src.core.runners.mssql_runner"

    def test_imports_catalog(self):
        """Verify run_demo.py imports from catalog.cpg1"""
        tree = get_script_ast("run_demo")
        imports = get_imports_from_ast(tree)
        
        has_catalog = any("cpg1" in imp or "get_item_by_id" in imp for imp in imports)
        assert has_catalog, "run_demo.py should import get_item_by_id from src.core.catalog.cpg1"

    def test_imports_classifier(self):
        """Verify run_demo.py imports classifier functions"""
        tree = get_script_ast("run_demo")
        imports = get_imports_from_ast(tree)
        
        has_classifier = any("classifier" in imp or "classify_bridges" in imp for imp in imports)
        assert has_classifier, "run_demo.py should import classify_bridges from src.bridges.classifier"

    def test_loads_from_fixtures(self):
        """Verify run_demo.py loads data from tests/fixtures/"""
        with open(os.path.join(REPO_ROOT, "scripts", "run_demo.py"), "r") as f:
            content = f.read()
        
        assert ("tests/fixtures" in content or ("tests" in content and "fixtures" in content)), \
            "run_demo.py should load data from tests/fixtures/"

    def test_calls_classify_bridges(self):
        """Verify run_demo.py calls classify_bridges function"""
        with open(os.path.join(REPO_ROOT, "scripts", "run_demo.py"), "r") as f:
            content = f.read()
        
        assert "classify_bridges(" in content, \
            "run_demo.py should call classify_bridges function"

    def test_no_hardcoded_sql(self):
        """Verify no hardcoded SQL queries in run_demo.py"""
        tree = get_script_ast("run_demo")
        has_sql = has_string_literal_with_sql(tree)
        assert not has_sql, "run_demo.py should not contain hardcoded SQL queries"


class TestGenerationScripts:
    """Tests for individual IPE generation scripts"""

    @pytest.mark.parametrize("script_name", [
        "generate_customer_accounts",
        "generate_collection_accounts",
        "generate_other_ar",
    ])
    def test_imports_catalog(self, script_name):
        """Verify generation scripts import from catalog"""
        tree = get_script_ast(script_name)
        imports = get_imports_from_ast(tree)
        
        has_catalog = any("cpg1" in imp or "get_item_by_id" in imp for imp in imports)
        assert has_catalog, f"{script_name}.py should import get_item_by_id from src.core.catalog.cpg1"

    @pytest.mark.parametrize("script_name", [
        "generate_customer_accounts",
        "generate_collection_accounts",
        "generate_other_ar",
    ])
    def test_uses_get_item_by_id(self, script_name):
        """Verify generation scripts call get_item_by_id to fetch catalog items"""
        with open(os.path.join(REPO_ROOT, "scripts", f"{script_name}.py"), "r") as f:
            content = f.read()
        
        assert "get_item_by_id(" in content, \
            f"{script_name}.py should call get_item_by_id to fetch catalog items"

    @pytest.mark.parametrize("script_name", [
        "generate_customer_accounts",
        "generate_collection_accounts",
        "generate_other_ar",
    ])
    def test_fetches_sql_from_catalog(self, script_name):
        """Verify generation scripts fetch SQL from catalog item.sql_query"""
        with open(os.path.join(REPO_ROOT, "scripts", f"{script_name}.py"), "r") as f:
            content = f.read()
        
        # Check that script accesses .sql_query attribute or similar
        assert "sql_query" in content or "item.sql_query" in content, \
            f"{script_name}.py should fetch SQL from catalog item's sql_query attribute"

    @pytest.mark.parametrize("script_name", [
        "generate_customer_accounts",
        "generate_collection_accounts",
        "generate_other_ar",
    ])
    def test_no_hardcoded_sql(self, script_name):
        """Verify no hardcoded SQL queries in generation scripts"""
        tree = get_script_ast(script_name)
        has_sql = has_string_literal_with_sql(tree)
        assert not has_sql, f"{script_name}.py should not contain hardcoded SQL queries"


class TestClassifyBridges:
    """Tests for scripts/classify_bridges.py"""

    def test_imports_classifier(self):
        """Verify classify_bridges.py imports from src.bridges.classifier"""
        tree = get_script_ast("classify_bridges")
        imports = get_imports_from_ast(tree)
        
        has_classifier = any("classifier" in imp or "classify_bridges" in imp for imp in imports)
        assert has_classifier, "classify_bridges.py should import classify_bridges from src.bridges.classifier"

    def test_imports_rules_catalog(self):
        """Verify classify_bridges.py imports load_rules from bridges.catalog"""
        tree = get_script_ast("classify_bridges")
        imports = get_imports_from_ast(tree)
        
        has_rules = any("load_rules" in imp for imp in imports)
        assert has_rules, "classify_bridges.py should import load_rules from src.bridges.catalog"

    def test_calls_classify_bridges(self):
        """Verify classify_bridges.py calls classify_bridges function"""
        with open(os.path.join(REPO_ROOT, "scripts", "classify_bridges.py"), "r") as f:
            content = f.read()
        
        assert "classify_bridges(" in content, \
            "classify_bridges.py should call classify_bridges function"

    def test_calls_load_rules(self):
        """Verify classify_bridges.py calls load_rules function"""
        with open(os.path.join(REPO_ROOT, "scripts", "classify_bridges.py"), "r") as f:
            content = f.read()
        
        assert "load_rules(" in content, \
            "classify_bridges.py should call load_rules function"


class TestCatalogUsage:
    """Integration tests to verify catalog items are properly structured"""

    def test_ipe_07_has_sql_query(self):
        """Verify IPE_07 catalog item has sql_query"""
        from src.core.catalog.cpg1 import get_item_by_id
        
        item = get_item_by_id("IPE_07")
        assert item is not None, "IPE_07 should exist in catalog"
        assert item.sql_query is not None, "IPE_07 should have sql_query"
        assert len(item.sql_query.strip()) > 0, "IPE_07 sql_query should not be empty"

    def test_cr_04_has_sql_query(self):
        """Verify CR_04 catalog item has sql_query"""
        from src.core.catalog.cpg1 import get_item_by_id
        
        item = get_item_by_id("CR_04")
        assert item is not None, "CR_04 should exist in catalog"
        assert item.sql_query is not None, "CR_04 should have sql_query"
        assert len(item.sql_query.strip()) > 0, "CR_04 sql_query should not be empty"

    def test_ipe_31_has_sql_query(self):
        """Verify IPE_31 catalog item has sql_query"""
        from src.core.catalog.cpg1 import get_item_by_id
        
        item = get_item_by_id("IPE_31")
        assert item is not None, "IPE_31 should exist in catalog"
        assert item.sql_query is not None, "IPE_31 should have sql_query"
        assert len(item.sql_query.strip()) > 0, "IPE_31 sql_query should not be empty"


class TestClassifierFunctions:
    """Verify classifier functions are available and functional"""

    def test_calculate_vtc_adjustment_available(self):
        """Verify calculate_vtc_adjustment is importable"""
        from src.bridges.classifier import calculate_vtc_adjustment
        assert callable(calculate_vtc_adjustment)

    def test_classify_bridges_available(self):
        """Verify classify_bridges is importable"""
        from src.bridges.classifier import classify_bridges
        assert callable(classify_bridges)

    def test_calculate_customer_posting_group_bridge_available(self):
        """Verify calculate_customer_posting_group_bridge is importable"""
        from src.bridges.classifier import calculate_customer_posting_group_bridge
        assert callable(calculate_customer_posting_group_bridge)

    def test_calculate_timing_difference_bridge_available(self):
        """Verify calculate_timing_difference_bridge is importable"""
        from src.bridges.classifier import calculate_timing_difference_bridge
        assert callable(calculate_timing_difference_bridge)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
