"""
Schema Validation Script for Voucher Classification.

This script validates that the voucher classification system produces
only schema-compliant values and combinations.

Usage:
    python scripts/validate_voucher_schema.py

Returns exit code 0 if all validations pass, non-zero otherwise.
"""

import sys
from typing import Set, Dict, List, Tuple

# Schema Definition
ALLOWED_VALUES = {
    "Manual/Integration": {"Manual", "Integration"},
    "Category": {"Issuance", "Cancellation", "Usage", "Expired", "VTC"},
    "Voucher Type": {"Refund", "Apology", "JForce", "Store Credit"},
}

# Valid combinations of (Category, Voucher Type)
VALID_COMBINATIONS = {
    "Issuance": {"Refund", "Apology", "JForce", "Store Credit"},
    "Cancellation": {"Apology", "Store Credit"},
    "Usage": {"Refund", "Apology", "JForce", "Store Credit"},
    "Expired": {"Apology", "JForce", "Refund", "Store Credit"},
    "VTC": {"Refund"},
}

# Integration type rule
INTEGRATION_USER_ID = "JUMIA/NAV31AFR.BATCH.SRVC"


def validate_schema_constants() -> Tuple[bool, List[str]]:
    """
    Validate that schema constants are correctly defined.
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Check that all categories have defined valid combinations
    for category in ALLOWED_VALUES["Category"]:
        if category not in VALID_COMBINATIONS:
            errors.append(f"Category '{category}' missing from VALID_COMBINATIONS")
    
    # Check that all voucher types in combinations are in allowed values
    for category, voucher_types in VALID_COMBINATIONS.items():
        for voucher_type in voucher_types:
            if voucher_type not in ALLOWED_VALUES["Voucher Type"]:
                errors.append(
                    f"Invalid voucher type '{voucher_type}' in combinations for {category}"
                )
    
    return len(errors) == 0, errors


def validate_code_produces_valid_values(
    integration_types: Set[str],
    categories: Set[str],
    voucher_types: Set[str],
) -> Tuple[bool, List[str]]:
    """
    Validate that observed values from code execution are schema-compliant.
    
    Args:
        integration_types: Set of Integration_Type values observed
        categories: Set of bridge_category values observed (excluding None)
        voucher_types: Set of voucher_type values observed (excluding None)
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    # Check Integration_Type values
    invalid_integration = integration_types - ALLOWED_VALUES["Manual/Integration"]
    if invalid_integration:
        errors.append(f"Invalid Integration_Type values: {invalid_integration}")
    
    # Check Category values
    invalid_categories = categories - ALLOWED_VALUES["Category"]
    if invalid_categories:
        errors.append(f"Invalid bridge_category values: {invalid_categories}")
    
    # Check Voucher Type values
    invalid_types = voucher_types - ALLOWED_VALUES["Voucher Type"]
    if invalid_types:
        errors.append(f"Invalid voucher_type values: {invalid_types}")
    
    return len(errors) == 0, errors


def validate_combinations(
    observed_combinations: Set[Tuple[str, str]]
) -> Tuple[bool, List[str]]:
    """
    Validate that observed (category, voucher_type) combinations are valid.
    
    Args:
        observed_combinations: Set of (bridge_category, voucher_type) tuples observed
    
    Returns:
        (is_valid, error_messages)
    """
    errors = []
    
    for category, voucher_type in observed_combinations:
        # Skip if category or type is None
        if category is None or voucher_type is None:
            continue
        
        # Check if category is valid
        if category not in VALID_COMBINATIONS:
            errors.append(f"Unknown category in combination: ({category}, {voucher_type})")
            continue
        
        # Check if combination is valid
        if voucher_type not in VALID_COMBINATIONS[category]:
            errors.append(
                f"Invalid combination: ({category}, {voucher_type}). "
                f"Expected voucher types for {category}: {VALID_COMBINATIONS[category]}"
            )
    
    return len(errors) == 0, errors


def print_schema_summary():
    """Print a summary of the schema definition."""
    print("=" * 80)
    print("VOUCHER CLASSIFICATION SCHEMA")
    print("=" * 80)
    print()
    
    print("Allowed Values:")
    print("-" * 40)
    for field, values in ALLOWED_VALUES.items():
        print(f"  {field}: {', '.join(sorted(values))}")
    print()
    
    print("Integration Type Rule:")
    print("-" * 40)
    print(f"  Integration if User ID == '{INTEGRATION_USER_ID}'")
    print(f"  Manual otherwise")
    print()
    
    print("Valid Category + Voucher Type Combinations:")
    print("-" * 40)
    for category in sorted(VALID_COMBINATIONS.keys()):
        voucher_types = sorted(VALID_COMBINATIONS[category])
        print(f"  {category}: {', '.join(voucher_types)}")
    print()


def main():
    """Main validation function."""
    print_schema_summary()
    
    # Validate schema constants
    print("Validating Schema Definition...")
    print("-" * 40)
    is_valid, errors = validate_schema_constants()
    
    if is_valid:
        print("✅ Schema definition is valid")
    else:
        print("❌ Schema definition has errors:")
        for error in errors:
            print(f"  - {error}")
        return 1
    
    print()
    print("=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)
    print()
    print("To validate code execution outputs, run tests with:")
    print("  pytest tests/test_voucher_schema_compliance.py -v")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
