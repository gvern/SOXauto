# ipe_runner.py
"""
IPERunner class to encapsulate the extraction and validation logic for a single IPE.
This class manages the complete execution of an IPE, from database connection
to data validation and evidence generation.
"""

import logging
import os
import pandas as pd
import pyodbc
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, Callable
from functools import wraps
from src.utils.aws_utils import AWSSecretsManager
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator

# Logging configuration
logger = logging.getLogger(__name__)


def _sanitize_input(value: str, max_length: int = 255, allow_chars: str = None) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        value: Input string to sanitize
        max_length: Maximum allowed length (default: 255)
        allow_chars: Regex pattern of allowed characters (default: alphanumeric + common safe chars)
    
    Returns:
        Sanitized string
    """
    import re
    
    if not isinstance(value, str):
        value = str(value)
    
    # Truncate to max length
    value = value[:max_length]
    
    # Default safe character set: alphanumeric, spaces, hyphens, underscores, dots
    if allow_chars is None:
        allow_chars = r'[^a-zA-Z0-9\s\-_.:/]'
    
    # Remove potentially dangerous characters
    sanitized = re.sub(allow_chars, '', value)
    
    # Remove any SQL injection patterns
    dangerous_patterns = [
        r"('|(\-\-)|(;)|(\|\|)|(\*))",
        r"(\b(ALTER|CREATE|DELETE|DROP|EXEC(UTE)?|INSERT( +INTO)?|MERGE|SELECT|UPDATE|UNION( +ALL)?)\b)"
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    return sanitized.strip()


class IPEValidationError(Exception):
    """Exception raised when IPE validation fails."""
    pass


class IPEConnectionError(Exception):
    """Exception raised when database connection fails."""
    pass


def retry_on_network_error(max_retries: int = 3, backoff_factor: float = 2.0, initial_delay: float = 1.0):
    """
    Decorator to retry database operations on transient network errors.
    
    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except (pyodbc.Error, pyodbc.OperationalError, pyodbc.InterfaceError) as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if error is transient/retriable
                    transient_errors = [
                        'timeout', 'connection', 'network', 'broken pipe',
                        'lost connection', 'server has gone away', 'communication link failure',
                        'connection reset', 'connection refused', 'host unreachable'
                    ]
                    
                    is_transient = any(err in error_msg for err in transient_errors)
                    
                    if not is_transient or attempt == max_retries:
                        # Non-transient error or final attempt - raise immediately
                        logger.error(f"Database operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                        raise
                    
                    # Log retry attempt
                    logger.warning(
                        f"Transient network error detected (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    # Wait before retry with exponential backoff
                    time.sleep(delay)
                    delay *= backoff_factor
                    
                except Exception as e:
                    # Non-database errors - raise immediately without retry
                    logger.error(f"Non-retriable error in database operation: {e}")
                    raise
            
            # Should not reach here, but raise last exception if we do
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class IPERunner:
    """
    Class responsible for executing a single IPE.
    Manages data extraction, validation, and cleanup.
    """
    
    def __init__(self, ipe_config: Dict[str, Any], secret_manager: AWSSecretsManager,
                 cutoff_date: Optional[str] = None, evidence_manager: Optional[DigitalEvidenceManager] = None,
                 country: Optional[str] = None, period: Optional[str] = None, 
                 full_params: Optional[Dict[str, Any]] = None):
        """
        Initialize the runner for a specific IPE.
        
        Args:
            ipe_config: IPE configuration (from config.py)
            secret_manager: AWS Secrets Manager instance
            cutoff_date: Cutoff date for extractions (format: YYYY-MM-DD)
            evidence_manager: Digital evidence manager for SOX compliance
            country: Country code (e.g., 'NG', 'KE') for evidence naming
            period: Period in YYYYMM format (e.g., '202509') for evidence naming
            full_params: Full dictionary of all SQL parameters to be logged
        """
        self.config = ipe_config
        self.secret_manager = secret_manager
        self.ipe_id = ipe_config['id']
        self.description = ipe_config['description']
        
        # Default cutoff date: first day of current month
        if cutoff_date:
            # Validate cutoff_date format (YYYY-MM-DD) to prevent injection
            import re
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', cutoff_date):
                raise ValueError(f"Invalid cutoff_date format: {cutoff_date}. Expected YYYY-MM-DD")
            # Additional validation: ensure it's a valid date
            try:
                datetime.strptime(cutoff_date, '%Y-%m-%d')
            except ValueError as e:
                raise ValueError(f"Invalid cutoff_date value: {cutoff_date}. {e}")
            self.cutoff_date = cutoff_date
        else:
            today = datetime.now()
            first_day_of_month = today.replace(day=1)
            self.cutoff_date = first_day_of_month.strftime('%Y-%m-%d')
        
        self.connection = None
        self.extracted_data = None
        self.validation_results = {}
        
        # SOX evidence manager
        self.evidence_manager = evidence_manager or DigitalEvidenceManager()
        self.evidence_generator = None
        
        # Store metadata for evidence package - sanitize inputs
        import re
        if country:
            # Country should be 2-letter code (e.g., 'NG', 'KE')
            if not re.match(r'^[A-Z]{2}$', country):
                logger.warning("Invalid country code format, sanitizing")
                country = _sanitize_input(country, max_length=2, allow_chars=r'[^A-Z]')
        
        if period:
            # Period should be YYYYMM format (e.g., '202509')
            if not re.match(r'^\d{6}$', period):
                logger.warning("Invalid period format, sanitizing")
                period = _sanitize_input(period, max_length=6, allow_chars=r'[^0-9]')
        
        self.country = country
        self.period = period
        self.full_params = full_params or {}
        
        logger.info(f"IPERunner initialized for {self.ipe_id} - Cutoff date: {self.cutoff_date}")
    
    @retry_on_network_error(max_retries=3, backoff_factor=2.0, initial_delay=1.0)
    def _get_database_connection(self) -> pyodbc.Connection:
        """
        Establish database connection using credentials from Secret Manager or environment variable.
        Automatically retries on transient network errors with exponential backoff.
        
        Fallback order:
        1. DB_CONNECTION_STRING environment variable (if set)
        2. AWS Secrets Manager (using secret_name from config)
        
        Returns:
            pyodbc connection to the database
            
        Raises:
            IPEConnectionError: If connection fails after all retries
        """
        try:
            # Check for environment variable fallback first
            connection_string = os.getenv('DB_CONNECTION_STRING')
            
            if connection_string:
                logger.info(f"[{self.ipe_id}] Using DB_CONNECTION_STRING from environment variable")
            else:
                # Retrieve connection string from Secret Manager
                logger.info(f"[{self.ipe_id}] Retrieving connection string from Secrets Manager")
                connection_string = self.secret_manager.get_secret(self.config['secret_name'])
            
            # Establish connection
            connection = pyodbc.connect(connection_string)
            logger.info(f"[{self.ipe_id}] Database connection established")
            return connection
            
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Database connection error: {e}"
            logger.error(error_msg)
            raise IPEConnectionError(error_msg)
    
    @retry_on_network_error(max_retries=3, backoff_factor=2.0, initial_delay=1.0)
    def _execute_query_with_parameters(self, query: str, parameters: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Execute SQL query with secure parameterized values.
        Automatically retries on transient network errors with exponential backoff.
        
        Args:
            query: SQL query to execute
            parameters: Parameters to inject into the query
            
        Returns:
            DataFrame containing the query results
        """
        try:
            if parameters is None:
                # Count placeholders in the query
                placeholder_count = query.count('?')
                parameters = tuple([self.cutoff_date] * placeholder_count)
            
            logger.debug(f"[{self.ipe_id}] Executing query with parameters: {parameters}")
            df = pd.read_sql(query, self.connection, params=parameters)
            logger.info(f"[{self.ipe_id}] Query executed: {len(df)} rows returned")
            return df
            
        except Exception as e:
            logger.error(f"[{self.ipe_id}] Error executing query: {e}")
            raise
    
    def _validate_completeness(self, main_dataframe: pd.DataFrame) -> bool:
        """
        Completeness validation: verifies that all expected data is present.
        
        Args:
            main_dataframe: The main DataFrame to validate
            
        Returns:
            True if validation succeeds, False otherwise
            
        Raises:
            IPEValidationError: If validation fails
        """
        try:
            logger.info(f"[{self.ipe_id}] Starting completeness validation...")
            
            if 'completeness_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] No completeness query defined")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            completeness_query = self.config['validation']['completeness_query']
            
            # Execute validation
            validation_df = self._execute_query_with_parameters(completeness_query)
            expected_count = validation_df.iloc[0, 0]
            actual_count = len(main_dataframe)
            
            self.validation_results['completeness'] = {
                'expected_count': expected_count,
                'actual_count': actual_count,
                'status': 'PASS' if expected_count == actual_count else 'FAIL'
            }
            
            if expected_count != actual_count:
                error_msg = (f"[{self.ipe_id}] Completeness validation failed. "
                           f"Expected: {expected_count}, Got: {actual_count}")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Completeness validation: SUCCESS ({actual_count} rows)")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Error during completeness validation: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _validate_accuracy_positive(self) -> bool:
        """
        Positive accuracy validation: verifies that a witness transaction is present.
        
        Returns:
            True if validation succeeds, False otherwise
            
        Raises:
            IPEValidationError: If validation fails
        """
        try:
            logger.info(f"[{self.ipe_id}] Starting positive accuracy validation...")
            
            if 'accuracy_positive_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] No positive accuracy query defined")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            accuracy_query = self.config['validation']['accuracy_positive_query']
            
            # Execute validation
            validation_df = self._execute_query_with_parameters(accuracy_query)
            witness_count = validation_df.iloc[0, 0]
            
            self.validation_results['accuracy_positive'] = {
                'witness_count': witness_count,
                'status': 'PASS' if witness_count > 0 else 'FAIL'
            }
            
            if witness_count == 0:
                error_msg = (f"[{self.ipe_id}] Positive accuracy validation failed. "
                           f"No witness transaction found")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Positive accuracy validation: SUCCESS ({witness_count} witnesses)")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Error during positive accuracy validation: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _validate_accuracy_negative(self) -> bool:
        """
        Negative accuracy validation: verifies that no excluded transaction is present.
        
        Returns:
            True if validation succeeds, False otherwise
            
        Raises:
            IPEValidationError: If validation fails
        """
        try:
            logger.info(f"[{self.ipe_id}] Starting negative accuracy validation...")
            
            if 'accuracy_negative_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] No negative accuracy query defined")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            accuracy_query = self.config['validation']['accuracy_negative_query']
            
            # Execute validation
            validation_df = self._execute_query_with_parameters(accuracy_query)
            excluded_count = validation_df.iloc[0, 0]
            
            self.validation_results['accuracy_negative'] = {
                'excluded_count': excluded_count,
                'status': 'PASS' if excluded_count == 0 else 'FAIL'
            }
            
            if excluded_count > 0:
                error_msg = (f"[{self.ipe_id}] Negative accuracy validation failed. "
                           f"{excluded_count} excluded transactions found")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Negative accuracy validation: SUCCESS")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Error during negative accuracy validation: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _cleanup_connection(self):
        """Cleanly closes the database connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"[{self.ipe_id}] Connection closed")
            except Exception as e:
                logger.warning(f"[{self.ipe_id}] Error closing connection: {e}")
    
    def run(self) -> pd.DataFrame:
        """
        Execute complete IPE: extraction, validation and SOX evidence generation.
        
        Returns:
            DataFrame containing extracted and validated data
            
        Raises:
            IPEValidationError: If validation fails
            IPEConnectionError: If connection problem occurs
        """
        try:
            logger.info(f"[{self.ipe_id}] ==> STARTING IPE EXECUTION")
            
            # 1. Create SOX evidence package with enhanced metadata
            execution_metadata = {
                'ipe_id': self.ipe_id,
                'description': self.description,
                'cutoff_date': self.cutoff_date,
                'execution_start': datetime.now().isoformat(),
                'secret_name': self.config['secret_name'],
                'sox_compliance_required': True,
                'country': self.country,
                'period': self.period
            }
            
            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id, execution_metadata, country=self.country, period=self.period
            )
            self.evidence_generator = IPEEvidenceGenerator(evidence_dir, self.ipe_id)
            
            # 2. Establish connection
            self.connection = self._get_database_connection()
            
            # 3. Extract main data
            logger.info(f"[{self.ipe_id}] Extracting main data...")
            main_query = self.config['main_query']
            
            # Count placeholders and prepare parameters
            placeholder_count = main_query.count('?')
            parameters = [self.cutoff_date] * placeholder_count
            
            # Build full parameters dictionary for logging (ALL parameters)
            full_params_dict = {
                'cutoff_date': self.cutoff_date,
                'parameters': parameters,
            }
            
            # Add any additional parameters passed to the runner (sanitize for logging)
            if self.full_params:
                sanitized_params = {}
                for key, value in self.full_params.items():
                    # Sanitize keys and values for safe logging
                    safe_key = _sanitize_input(str(key), max_length=100)
                    if isinstance(value, str):
                        safe_value = _sanitize_input(value, max_length=500)
                    else:
                        safe_value = value  # Numbers, dates, etc. are safe
                    sanitized_params[safe_key] = safe_value
                full_params_dict.update(sanitized_params)
            
            # Save exact query with ALL parameters BEFORE execution
            self.evidence_generator.save_executed_query(
                main_query, 
                full_params_dict
            )
            
            # Execute query
            self.extracted_data = self._execute_query_with_parameters(main_query, tuple(parameters))
            
            # Add traceability metadata
            self.extracted_data['_ipe_id'] = self.ipe_id
            self.extracted_data['_extraction_date'] = datetime.now().isoformat()
            self.extracted_data['_cutoff_date'] = self.cutoff_date
            
            # 4. Generate evidence proofs immediately
            logger.info(f"[{self.ipe_id}] Generating evidence proofs...")
            self.evidence_generator.save_data_snapshot(self.extracted_data)
            integrity_hash = self.evidence_generator.generate_integrity_hash(self.extracted_data)
            
            logger.info(f"[{self.ipe_id}] Data extracted: {len(self.extracted_data)} rows, "
                       f"Hash: {integrity_hash[:16]}...")
            
            # 5. Execute SOX validations
            logger.info(f"[{self.ipe_id}] Starting SOX validations...")
            
            self._validate_completeness(self.extracted_data)
            self._validate_accuracy_positive()
            self._validate_accuracy_negative()
            
            # 6. Save validation results
            self.validation_results['overall_status'] = 'SUCCESS'
            self.validation_results['execution_time'] = datetime.now().isoformat()
            self.validation_results['data_integrity_hash'] = integrity_hash
            
            self.evidence_generator.save_validation_results(self.validation_results)
            
            # 7. Finalize evidence package
            evidence_zip = self.evidence_generator.finalize_evidence_package()
            
            logger.info(f"[{self.ipe_id}] ==> IPE EXECUTED SUCCESSFULLY - "
                       f"{len(self.extracted_data)} rows validated")
            logger.info(f"[{self.ipe_id}] SOX evidence package: {evidence_zip}")
            
            return self.extracted_data
            
        except (IPEValidationError, IPEConnectionError):
            self.validation_results['overall_status'] = 'FAILED'
            if self.evidence_generator:
                self.evidence_generator.save_validation_results(self.validation_results)
                self.evidence_generator.finalize_evidence_package()
            raise
        except Exception as e:
            self.validation_results['overall_status'] = 'ERROR'
            error_msg = f"[{self.ipe_id}] Unexpected error during execution: {e}"
            if self.evidence_generator:
                self.evidence_generator.save_validation_results(self.validation_results)
                self.evidence_generator.finalize_evidence_package()
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            # 8. Clean up resources
            self._cleanup_connection()


    def run_demo(self, demo_dataframe: pd.DataFrame, source_name: str) -> pd.DataFrame:
        """
        Demo execution path: uses a provided DataFrame instead of querying the DB
        and generates a complete evidence package.
        """
        try:
            logger.info(f"[{self.ipe_id}] ==> STARTING IPE DEMO EXECUTION")
            execution_metadata = {
                'ipe_id': self.ipe_id,
                'description': self.description,
                'cutoff_date': self.cutoff_date,
                'execution_start': datetime.now().isoformat(),
                'sox_compliance_required': False,
                'mode': 'DEMO',
                'demo_source': source_name,
                'country': self.country,
                'period': self.period
            }

            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id, execution_metadata, country=self.country, period=self.period
            )
            self.evidence_generator = IPEEvidenceGenerator(evidence_dir, self.ipe_id)

            # Sanitize source_name to prevent injection in evidence logs
            safe_source_name = _sanitize_input(source_name, max_length=200)
            pseudo_query = "-- DEMO MODE --\n-- Data loaded from: " + safe_source_name
            
            # Build full parameters for demo (sanitize for evidence package)
            demo_params = {
                'source': safe_source_name,  # Already sanitized above
                'cutoff_date': self.cutoff_date  # Validated in __init__
            }
            if self.full_params:
                # Sanitize additional parameters
                for key, value in self.full_params.items():
                    safe_key = _sanitize_input(str(key), max_length=100)
                    if isinstance(value, str):
                        safe_value = _sanitize_input(value, max_length=500)
                    else:
                        safe_value = value
                    demo_params[safe_key] = safe_value
            
            self.evidence_generator.save_executed_query(
                pseudo_query,
                parameters=demo_params
            )

            df = demo_dataframe.copy()
            df['_ipe_id'] = self.ipe_id
            df['_extraction_date'] = datetime.now().isoformat()
            df['_cutoff_date'] = self.cutoff_date
            self.extracted_data = df

            self.evidence_generator.save_data_snapshot(df)

            self.validation_results = {
                'completeness': {'status': 'SKIPPED', 'reason': 'Demo mode: DB validation not applicable'},
                'accuracy_positive': {'status': 'SKIPPED', 'reason': 'Demo mode'},
                'accuracy_negative': {'status': 'SKIPPED', 'reason': 'Demo mode'},
                'overall_status': 'SUCCESS',
                'execution_time': datetime.now().isoformat(),
            }

            self.evidence_generator.save_validation_results(self.validation_results)
            evidence_zip = self.evidence_generator.finalize_evidence_package()
            logger.info(f"[{self.ipe_id}] ==> DEMO EXECUTION COMPLETE - Evidence: {evidence_zip}")

            return df

        except Exception as e:
            logger.error(f"[{self.ipe_id}] Error during demo run: {e}")
            if self.evidence_generator:
                try:
                    self.validation_results['overall_status'] = 'ERROR'
                    self.evidence_generator.save_validation_results(self.validation_results)
                    self.evidence_generator.finalize_evidence_package()
                except Exception:
                    pass
            raise
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Returns a summary of validation results.
        
        Returns:
            Dictionary containing validation summary
        """
        return {
            'ipe_id': self.ipe_id,
            'description': self.description,
            'cutoff_date': self.cutoff_date,
            'extracted_rows': len(self.extracted_data) if self.extracted_data is not None else 0,
            'validation_results': self.validation_results
        }