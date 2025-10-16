#!/usr/bin/env python3
"""
IPE Configuration Validation Script

This script validates the security and correctness of IPE configurations
without requiring database connections. It performs static analysis to ensure:
- All queries use parameterized placeholders (?)
- No SQL injection risks (no .format() or string concatenation)
- CTE patterns are correctly implemented
- Configuration structure is valid

Usage:
    python scripts/validate_ipe_config.py
"""

import sys
import os
import re
from typing import List, Dict, Tuple

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.config import IPE_CONFIGS, AWS_REGION


class IPEConfigValidator:
    """Validates IPE configurations for security and correctness."""
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passed_tests = 0
        self.total_tests = 0
        
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("=" * 70)
        print("IPE CONFIGURATION VALIDATION")
        print("=" * 70)
        print()
        
        # Check environment variables
        self._check_environment_config()
        
        # Validate each IPE configuration
        for ipe_config in IPE_CONFIGS:
            print(f"\nValidating IPE: {ipe_config['id']}")
            print("-" * 70)
            self._validate_ipe(ipe_config)
        
        # Print summary
        self._print_summary()
        
        return len(self.errors) == 0
    
    def _check_environment_config(self):
        """Check that AWS_REGION uses environment variable."""
        print("\n🔍 Checking Environment Configuration...")
        print("-" * 70)
        
        self.total_tests += 1
        
        # Read the source code to check if os.getenv() is used
        config_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'core', 'config.py')
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                
            if 'os.getenv("AWS_REGION"' in content or 'os.getenv(\'AWS_REGION\'' in content:
                print("✅ AWS_REGION: Using os.getenv() for environment variable")
                self.passed_tests += 1
            else:
                error = "❌ AWS_REGION: Not using os.getenv() (should read from environment)"
                print(error)
                self.errors.append(error)
        except FileNotFoundError:
            warning = "⚠️  Could not read config.py to verify AWS_REGION"
            print(warning)
            self.warnings.append(warning)
    
    def _validate_ipe(self, ipe_config: Dict):
        """Validate a single IPE configuration."""
        ipe_id = ipe_config['id']
        
        # Required fields check
        self._check_required_fields(ipe_id, ipe_config)
        
        # Main query validation
        self._check_main_query_security(ipe_id, ipe_config.get('main_query', ''))
        
        # Validation queries check
        if 'validation' in ipe_config:
            validation = ipe_config['validation']
            
            if 'completeness_query' in validation:
                self._check_validation_query_security(
                    ipe_id, 'completeness', validation['completeness_query']
                )
            
            if 'accuracy_positive_query' in validation:
                self._check_validation_query_security(
                    ipe_id, 'accuracy_positive', validation['accuracy_positive_query']
                )
            
            if 'accuracy_negative_query' in validation:
                self._check_validation_query_security(
                    ipe_id, 'accuracy_negative', validation['accuracy_negative_query']
                )
    
    def _check_required_fields(self, ipe_id: str, config: Dict):
        """Check that all required fields are present."""
        self.total_tests += 1
        required_fields = ['id', 'description', 'secret_name', 'main_query']
        missing = [f for f in required_fields if f not in config]
        
        if not missing:
            print(f"✅ Required fields: All present")
            self.passed_tests += 1
        else:
            error = f"❌ Required fields: Missing {missing}"
            print(error)
            self.errors.append(f"{ipe_id}: {error}")
    
    def _check_main_query_security(self, ipe_id: str, query: str):
        """Check main query for security issues."""
        self.total_tests += 1
        
        # Check for parameterized placeholders
        has_placeholders = '?' in query
        
        # Check for SQL injection risks
        has_format = '.format(' in query or '%s' in query or '%d' in query
        has_concat = ' + ' in query and 'SELECT' in query  # Simple heuristic
        
        if has_placeholders and not has_format and not has_concat:
            print(f"✅ Main query: Secure (uses ? placeholders)")
            self.passed_tests += 1
        else:
            issues = []
            if not has_placeholders:
                issues.append("no ? placeholders")
            if has_format:
                issues.append("uses .format() or %s/%d")
            if has_concat:
                issues.append("possible string concatenation")
            
            error = f"❌ Main query: Security issues - {', '.join(issues)}"
            print(error)
            self.errors.append(f"{ipe_id}: {error}")
    
    def _check_validation_query_security(self, ipe_id: str, query_type: str, query: str):
        """Check validation query for CTE pattern and security."""
        self.total_tests += 1
        
        # Check for CTE pattern
        has_cte = 'WITH main_data AS' in query or 'WITH' in query.upper()
        
        # Check for SQL injection risks
        has_format = '.format(' in query
        has_placeholder_injection = '{main_query}' in query
        
        # Check for parameterized placeholders
        has_placeholders = '?' in query
        
        if has_cte and not has_format and not has_placeholder_injection and has_placeholders:
            print(f"✅ {query_type.capitalize()} query: Secure CTE pattern")
            self.passed_tests += 1
        else:
            issues = []
            if not has_cte:
                issues.append("missing CTE pattern")
            if has_format:
                issues.append("uses .format()")
            if has_placeholder_injection:
                issues.append("has {{main_query}} injection point")
            if not has_placeholders:
                issues.append("no ? placeholders")
            
            error = f"❌ {query_type.capitalize()} query: Security issues - {', '.join(issues)}"
            print(error)
            self.errors.append(f"{ipe_id}: {error}")
    
    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        
        print(f"\nTests Run: {self.total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ ALL CHECKS PASSED - Configuration is secure!")
        elif not self.errors:
            print("\n✅ ALL CRITICAL CHECKS PASSED - Review warnings")
        else:
            print("\n❌ VALIDATION FAILED - Fix errors before production")
        
        print("=" * 70)


def main():
    """Main execution function."""
    validator = IPEConfigValidator()
    success = validator.validate_all()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
