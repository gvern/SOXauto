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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from src.utils.aws_utils import AWSSecretsManager
from src.core.evidence.manager import DigitalEvidenceManager, IPEEvidenceGenerator

# Logging configuration
logger = logging.getLogger(__name__)


class IPEValidationError(Exception):
    """Exception raised when IPE validation fails."""
    pass


class IPEConnectionError(Exception):
    """Exception raised when database connection fails."""
    pass


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
        
        # Store metadata for evidence package
        self.country = country
        self.period = period
        self.full_params = full_params or {}
        
        logger.info(f"IPERunner initialized for {self.ipe_id} - Cutoff date: {self.cutoff_date}")
    
    def _get_database_connection(self) -> pyodbc.Connection:
        """
        Establish database connection using credentials from Secret Manager or environment variable.
        
        Fallback order:
        1. DB_CONNECTION_STRING environment variable (if set)
        2. AWS Secrets Manager (using secret_name from config)
        
        Returns:
            pyodbc connection to the database
            
        Raises:
            IPEConnectionError: If connection fails
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
    
    def _execute_query_with_parameters(self, query: str, parameters: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Execute SQL query with secure parameterized values.
        
        Args:
            query: SQL query to execute
            parameters: Parameters to inject into the query
            
        Returns:
            DataFrame contenant les résultats de la requête
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
        Validation de complétude: vérifie que toutes les données attendues sont présentes.
        
        Args:
            main_dataframe: Le DataFrame principal à valider
            
        Returns:
            True si la validation réussit, False sinon
            
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
            
            # Add any additional parameters passed to the runner
            if self.full_params:
                full_params_dict.update(self.full_params)
            
            # Extract common parameters from full_params if available
            
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

            pseudo_query = f"-- DEMO MODE --\n-- Data loaded from: {source_name}"
            
            # Build full parameters for demo
            demo_params = {
                'source': source_name, 
                'cutoff_date': self.cutoff_date
            }
            if self.full_params:
                demo_params.update(self.full_params)
            
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
            raise        """
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
                'demo_source': source_name
            }

            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id, execution_metadata
            )
            self.evidence_generator = IPEEvidenceGenerator(evidence_dir, self.ipe_id)

            pseudo_query = f"-- DEMO MODE --\n-- Data loaded from: {source_name}"
            self.evidence_generator.save_executed_query(
                pseudo_query,
                parameters={'source': source_name, 'cutoff_date': self.cutoff_date}
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
            # Attempt to finalize evidence package even on error for debugging
            if self.evidence_generator:
                try:
                    self.validation_results['overall_status'] = 'ERROR'
                    self.evidence_generator.save_validation_results(self.validation_results)
                    self.evidence_generator.finalize_evidence_package()
                except Exception:
                    pass
            raise        """
        Demo execution path: load data from a local file instead of querying the DB,
        and generate a near-complete evidence package (without integrity hash by default).

        Args:
            demo_file_path: Path to a CSV/Excel file containing sample data for this IPE
            include_hash: When True, also generate the integrity hash (default False for demo)

        Returns:
            DataFrame loaded from the demo file
        """
        try:
            logger.info(f"[{self.ipe_id}] ==> STARTING IPE DEMO EXECUTION")

            # 1) Create SOX evidence package (mark demo mode in metadata)
            execution_metadata = {
                'ipe_id': self.ipe_id,
                'description': self.description,
                'cutoff_date': self.cutoff_date,
                'execution_start': datetime.now().isoformat(),
                'sox_compliance_required': False,
                'mode': 'DEMO',
                'demo_file_path': os.path.abspath(demo_file_path)
            }

            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id, execution_metadata
            )
            self.evidence_generator = IPEEvidenceGenerator(evidence_dir, self.ipe_id)

            # 2) Save a pseudo-query as provenance
            pseudo_query = f"-- DEMO LOAD FROM FILE\n-- IPE: {self.ipe_id}\nLOAD DATA FROM '{os.path.basename(demo_file_path)}'"
            self.evidence_generator.save_executed_query(
                pseudo_query,
                parameters={'file_path': os.path.abspath(demo_file_path), 'cutoff_date': self.cutoff_date}
            )

            # 3) Load data from file (CSV or Excel)
            if not os.path.exists(demo_file_path):
                raise FileNotFoundError(f"Demo file not found: {demo_file_path}")

            ext = os.path.splitext(demo_file_path)[1].lower()
            if ext in [".csv", ".txt"]:
                df = pd.read_csv(demo_file_path)
            elif ext in [".xlsx", ".xlsm", ".xls"]:
                # Try first sheet by default
                df = pd.read_excel(demo_file_path)
            else:
                # Fallback: try CSV
                df = pd.read_csv(demo_file_path)

            # Add traceability metadata
            df['_ipe_id'] = self.ipe_id
            df['_extraction_date'] = datetime.now().isoformat()
            df['_cutoff_date'] = self.cutoff_date
            self.extracted_data = df

            # 4) Save snapshot and summary
            self.evidence_generator.save_data_snapshot(df)

            # 5) Demo validations: mark as PASS with demo context
            self.validation_results = {
                'completeness': {'status': 'SKIPPED', 'reason': 'Demo mode: DB validation queries not executed'},
                'accuracy_positive': {'status': 'SKIPPED', 'reason': 'Demo mode'},
                'accuracy_negative': {'status': 'SKIPPED', 'reason': 'Demo mode'},
                'overall_status': 'SUCCESS',
                'execution_time': datetime.now().isoformat(),
            }

            # Optionally include integrity hash for demo
            if include_hash:
                try:
                    integrity_hash = self.evidence_generator.generate_integrity_hash(df)
                    self.validation_results['data_integrity_hash'] = integrity_hash
                except Exception as e:
                    logger.warning(f"[{self.ipe_id}] Demo hash generation failed: {e}")

            self.evidence_generator.save_validation_results(self.validation_results)

            # 6) Finalize evidence package to include execution log and ZIP
            evidence_zip = self.evidence_generator.finalize_evidence_package()
            logger.info(f"[{self.ipe_id}] ==> DEMO EXECUTION COMPLETE - Evidence: {evidence_zip}")

            return df

        except Exception as e:
            self.validation_results['overall_status'] = 'ERROR'
            if self.evidence_generator:
                try:
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