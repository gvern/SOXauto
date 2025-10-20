# ipe_runner_athena.py
"""
REFACTORED IPERunner for AWS Athena (V2)

This version replaces the SQL Server connection with AWS Athena queries.
Uses awswrangler for simplified Athena interaction.

Key Changes from V1:
- Removed pyodbc dependency
- Removed DB_CONNECTION_STRING fallback
- Added awswrangler for Athena queries
- Updated query execution to use S3-based approach
"""

import logging
import os
import pandas as pd
import awswrangler as wr
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator

# Logging configuration
logger = logging.getLogger(__name__)


class IPEValidationError(Exception):
    """Exception raised when IPE validation fails."""
    pass


class IPEConnectionError(Exception):
    """Exception raised when Athena query fails."""
    pass


class IPERunnerAthena:
    """
    IPE Runner using AWS Athena instead of direct SQL Server connection.
    
    This class manages data extraction from S3 via Athena, validation, and evidence generation.
    """
    
    def __init__(self, ipe_config: Dict[str, Any],
                 cutoff_date: Optional[str] = None,
                 evidence_manager: Optional[DigitalEvidenceManager] = None,
                 aws_region: Optional[str] = None,
                 athena_s3_output: Optional[str] = None):
        """
        Initialize the runner for a specific IPE.
        
        Args:
            ipe_config: IPE configuration with athena_database and query
            cutoff_date: Cutoff date for extractions (format: YYYY-MM-DD)
            evidence_manager: Digital evidence manager for SOX compliance
            aws_region: AWS region (default: from AWS_REGION env var)
            athena_s3_output: S3 location for Athena query results (default: from ATHENA_S3_OUTPUT env var)
        """
        self.config = ipe_config
        self.ipe_id = ipe_config['id']
        self.description = ipe_config['description']
        
        # Athena configuration
        self.athena_database = ipe_config.get('athena_database')
        self.aws_region = aws_region or os.getenv('AWS_REGION', 'eu-west-1')
        self.athena_s3_output = athena_s3_output or os.getenv(
            'ATHENA_S3_OUTPUT',
            's3://athena-query-results-s3-ew1-production-jdata/'
        )
        
        # Validate Athena configuration
        if not self.athena_database:
            raise ValueError(f"[{self.ipe_id}] Missing 'athena_database' in IPE configuration")
        
        # Default cutoff date: first day of current month
        if cutoff_date:
            self.cutoff_date = cutoff_date
        else:
            today = datetime.now()
            first_day_of_month = today.replace(day=1)
            self.cutoff_date = first_day_of_month.strftime('%Y-%m-%d')
        
        self.extracted_data = None
        self.validation_results = {}
        
        # SOX evidence manager
        self.evidence_manager = evidence_manager or DigitalEvidenceManager()
        self.evidence_generator = None
        
        logger.info(f"IPERunnerAthena initialized for {self.ipe_id}")
        logger.info(f"  Database: {self.athena_database}")
        logger.info(f"  Region: {self.aws_region}")
        logger.info(f"  S3 Output: {self.athena_s3_output}")
        logger.info(f"  Cutoff date: {self.cutoff_date}")

    @classmethod
    def from_catalog(
        cls,
        ipe_id: str,
        cutoff_date: Optional[str] = None,
        evidence_manager: Optional[DigitalEvidenceManager] = None,
        aws_region: Optional[str] = None,
        athena_s3_output: Optional[str] = None,
    ) -> "IPERunnerAthena":
        """
        Factory: build an IPERunnerAthena using the unified catalog as single source of truth.

        Args:
            ipe_id: IPE identifier present in the catalog with Athena configuration
            cutoff_date: Optional cutoff date
            evidence_manager: Evidence manager
            aws_region: AWS region
            athena_s3_output: S3 output for Athena results

        Returns:
            IPERunnerAthena instance ready to run
        """
        try:
            from src.core.catalog import get_athena_config
        except Exception as e:
            raise ValueError(
                f"Unified catalog not available to load IPE '{ipe_id}': {e}"
            )

        ipe_config = get_athena_config(ipe_id)
        return cls(
            ipe_config=ipe_config,
            cutoff_date=cutoff_date,
            evidence_manager=evidence_manager,
            aws_region=aws_region,
            athena_s3_output=athena_s3_output,
        )
    
    def _execute_athena_query(self, query: str) -> pd.DataFrame:
        """
        Execute SQL query on AWS Athena and return results as DataFrame.
        
        awswrangler handles query submission, polling for completion, and result retrieval
        automatically, eliminating the need for manual polling loops.
        
        Args:
            query: SQL query to execute (Athena SQL syntax)
            
        Returns:
            DataFrame containing query results
            
        Raises:
            IPEConnectionError: If query execution fails
        """
        try:
            import boto3
            
            logger.info(f"[{self.ipe_id}] Executing Athena query...")
            logger.debug(f"[{self.ipe_id}] Query: {query[:200]}...")  # Log first 200 chars
            
            # Create boto3 session with region
            session = boto3.Session(region_name=self.aws_region)
            
            # Execute query using awswrangler - it handles polling internally
            # Note: awswrangler.athena.read_sql_query waits for query completion automatically
            df = wr.athena.read_sql_query(
                sql=query,
                database=self.athena_database,
                s3_output=self.athena_s3_output,
                boto3_session=session,
                ctas_approach=False,      # No temp Glue tables (requires Glue:CreateTable)
                unload_approach=False,    # No UNLOAD (requires additional S3 permissions)
                keep_files=True           # Don't delete results (requires S3:DeleteObject)
            )
            
            logger.info(f"[{self.ipe_id}] Query successful - {len(df)} rows retrieved")
            return df
            
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Athena query error: {e}"
            logger.error(error_msg)
            raise IPEConnectionError(error_msg)
    
    def _prepare_query(self) -> str:
        """
        Prepare the SQL query with parameter substitution.
        
        Replaces placeholders with actual values:
        - {cutoff_date} → self.cutoff_date
        
        Returns:
            Query string with substituted parameters
        """
        query = self.config['query']
        
        # Parameter substitution
        query = query.replace('{cutoff_date}', f"DATE('{self.cutoff_date}')")
        
        logger.debug(f"[{self.ipe_id}] Prepared query: {query[:300]}...")
        return query
    
    def _validate_completeness(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data completeness (no nulls in critical columns).
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = self.config.get('validation', {})
        critical_columns = validation.get('critical_columns', [])
        
        results = {
            'test_name': 'completeness',
            'status': 'PASS',
            'issues': []
        }
        
        if not critical_columns:
            results['status'] = 'SKIPPED'
            results['message'] = 'No critical columns defined'
            return results
        
        for col in critical_columns:
            if col not in df.columns:
                results['issues'].append(f"Column '{col}' not found in data")
                results['status'] = 'FAIL'
                continue
            
            null_count = df[col].isnull().sum()
            if null_count > 0:
                results['issues'].append(f"Column '{col}' has {null_count} null values")
                results['status'] = 'FAIL'
        
        if results['status'] == 'PASS':
            results['message'] = f"All {len(critical_columns)} critical columns are complete"
        
        return results
    
    def _validate_accuracy_positive(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate positive accuracy rules (expected patterns).
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = self.config.get('validation', {})
        positive_rules = validation.get('accuracy_positive', [])
        
        results = {
            'test_name': 'accuracy_positive',
            'status': 'PASS',
            'rules_passed': 0,
            'rules_failed': 0,
            'issues': []
        }
        
        if not positive_rules:
            results['status'] = 'SKIPPED'
            results['message'] = 'No positive rules defined'
            return results
        
        for rule in positive_rules:
            rule_name = rule.get('name', 'unnamed_rule')
            condition = rule.get('condition', '')
            
            try:
                # Evaluate condition on DataFrame
                matching_rows = df.query(condition)
                if len(matching_rows) > 0:
                    results['rules_passed'] += 1
                else:
                    results['rules_failed'] += 1
                    results['issues'].append(f"Rule '{rule_name}' matched 0 rows (expected > 0)")
                    results['status'] = 'FAIL'
            except Exception as e:
                results['rules_failed'] += 1
                results['issues'].append(f"Rule '{rule_name}' evaluation error: {e}")
                results['status'] = 'FAIL'
        
        if results['status'] == 'PASS':
            results['message'] = f"{results['rules_passed']} positive rules passed"
        
        return results
    
    def _validate_accuracy_negative(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate negative accuracy rules (forbidden patterns).
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with validation results
        """
        validation = self.config.get('validation', {})
        negative_rules = validation.get('accuracy_negative', [])
        
        results = {
            'test_name': 'accuracy_negative',
            'status': 'PASS',
            'rules_passed': 0,
            'rules_failed': 0,
            'issues': []
        }
        
        if not negative_rules:
            results['status'] = 'SKIPPED'
            results['message'] = 'No negative rules defined'
            return results
        
        for rule in negative_rules:
            rule_name = rule.get('name', 'unnamed_rule')
            condition = rule.get('condition', '')
            
            try:
                # Evaluate condition on DataFrame
                matching_rows = df.query(condition)
                if len(matching_rows) == 0:
                    results['rules_passed'] += 1
                else:
                    results['rules_failed'] += 1
                    results['issues'].append(
                        f"Rule '{rule_name}' matched {len(matching_rows)} rows (expected 0)"
                    )
                    results['status'] = 'FAIL'
            except Exception as e:
                results['rules_failed'] += 1
                results['issues'].append(f"Rule '{rule_name}' evaluation error: {e}")
                results['status'] = 'FAIL'
        
        if results['status'] == 'PASS':
            results['message'] = f"{results['rules_passed']} negative rules passed"
        
        return results
    
    def _validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run all validation tests on extracted data.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with all validation results
        """
        logger.info(f"[{self.ipe_id}] Running validation tests...")
        
        validations = {
            'completeness': self._validate_completeness(df),
            'accuracy_positive': self._validate_accuracy_positive(df),
            'accuracy_negative': self._validate_accuracy_negative(df)
        }
        
        # Overall status
        overall_status = 'PASS'
        for test_name, result in validations.items():
            if result['status'] == 'FAIL':
                overall_status = 'FAIL'
                break
        
        validations['overall_status'] = overall_status
        
        logger.info(f"[{self.ipe_id}] Validation complete - Overall: {overall_status}")
        return validations
    
    def run(self) -> pd.DataFrame:
        """
        Execute the complete IPE extraction and validation flow.
        
        Returns:
            DataFrame with extracted data
            
        Raises:
            IPEConnectionError: If query fails
            IPEValidationError: If validation fails
        """
        try:
            # Create evidence package
            execution_metadata = {
                'ipe_id': self.ipe_id,
                'description': self.description,
                'cutoff_date': self.cutoff_date,
                'athena_database': self.athena_database,
                'timestamp': datetime.now().isoformat()
            }
            
            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id,
                execution_metadata
            )
            
            # Initialize evidence generator
            self.evidence_generator = IPEEvidenceGenerator(
                evidence_dir=evidence_dir,
                ipe_id=self.ipe_id
            )
            
            # Prepare and execute query
            query = self._prepare_query()
            self.evidence_generator.save_executed_query(query)
            
            # Execute Athena query
            df = self._execute_athena_query(query)
            self.extracted_data = df
            
            # Save data snapshot
            self.evidence_generator.save_data_snapshot(df)
            
            # Validate data
            validation_results = self._validate_data(df)
            self.validation_results = validation_results
            
            # Save validation results
            self.evidence_generator.save_validation_results(validation_results)
            
            logger.info(f"[{self.ipe_id}] Evidence package saved: {evidence_dir}")
            
            # Check if validation passed
            if validation_results['overall_status'] != 'PASS':
                raise IPEValidationError(
                    f"[{self.ipe_id}] Validation failed - see evidence package for details"
                )
            
            logger.info(f"[{self.ipe_id}] IPE extraction successful")
            return df
            
        except IPEConnectionError:
            raise
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Unexpected error during extraction: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
