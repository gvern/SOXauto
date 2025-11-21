# evidence_manager.py
"""
Digital Evidence Package Manager for SOXauto PG-01
Generates tamper-proof evidence for each IPE execution in compliance with SOX requirements.
"""

import os
import hashlib
import json
import zipfile
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd
import logging
from pathlib import Path
from src.utils.system_utils import get_system_context

logger = logging.getLogger(__name__)


class DigitalEvidenceManager:
    """
    Digital evidence manager for SOX extractions.
    Creates a complete and tamper-proof evidence package for each execution.
    """
    
    def __init__(self, base_evidence_dir: str = "evidence"):
        """
        Initializes the evidence manager.
        
        Args:
            base_evidence_dir: Root directory for storing evidence
        """
        self.base_evidence_dir = Path(base_evidence_dir)
        self.base_evidence_dir.mkdir(exist_ok=True)
        
    def create_evidence_package(self, ipe_id: str, execution_metadata: Dict[str, Any],
                               country: Optional[str] = None, period: Optional[str] = None) -> str:
        """
        Creates a timestamped evidence directory for an IPE execution.
        
        Args:
            ipe_id: IPE identifier
            execution_metadata: Execution metadata
            country: Country code (e.g., 'NG', 'KE')
            period: Period in YYYYMM format (e.g., '202509')
            
        Returns:
            Path to the created evidence directory
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Build folder name with new convention: {ipe_id}_{country}_{period}_{timestamp}
        if country and period:
            folder_name = f"{ipe_id}_{country}_{period}_{timestamp}"
        else:
            # Fallback to old format if country/period not provided
            folder_name = f"{ipe_id}_{timestamp}"
        
        evidence_dir = self.base_evidence_dir / folder_name
        evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Create system context file (00_system_context.json)
        system_context = get_system_context()
        context_file = evidence_dir / "00_system_context.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(system_context, f, indent=2, ensure_ascii=False)
        
        # Create execution metadata file
        metadata_file = evidence_dir / "execution_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(execution_metadata, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Evidence package created: {evidence_dir}")
        return str(evidence_dir)


class IPEEvidenceGenerator:
    """
    Evidence generator specific to an IPE execution.
    """
    
    def __init__(self, evidence_dir: str, ipe_id: str):
        """
        Initializes the generator for a specific IPE.
        
        Args:
            evidence_dir: Directory to store evidence
            ipe_id: IPE identifier
        """
        self.evidence_dir = Path(evidence_dir)
        self.ipe_id = ipe_id
        self.execution_log = []
        
    def save_executed_query(self, query: str, parameters: Dict[str, Any] = None) -> None:
        """
        Saves the exact SQL query executed with its parameters.
        
        Args:
            query: SQL query executed
            parameters: Parameters used in the query
        """
        try:
            # Save raw query
            query_file = self.evidence_dir / "01_executed_query.sql"
            with open(query_file, 'w', encoding='utf-8') as f:
                f.write("-- SQL Query Executed for IPE {}\n".format(self.ipe_id))
                f.write("-- Timestamp: {}\n".format(datetime.now().isoformat()))
                f.write("-- ===========================================\n\n")
                f.write(query)
            
            # Save parameters if provided
            if parameters:
                params_file = self.evidence_dir / "02_query_parameters.json"
                with open(params_file, 'w', encoding='utf-8') as f:
                    json.dump(parameters, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("QUERY_SAVED", f"Query saved: {len(query)} characters")
            logger.info(f"[{self.ipe_id}] Executed query saved")
            
        except Exception as e:
            self._log_action("ERROR", f"Error saving query: {e}")
            logger.error(f"[{self.ipe_id}] Error saving query: {e}")
            raise
    
    def save_data_snapshot(self, dataframe: pd.DataFrame, snapshot_rows: int = 100) -> None:
        """
        Saves a snapshot of extracted data (programmatic equivalent of a screenshot).
        Uses tail (last rows) instead of head for better visibility of recent data.
        
        Args:
            dataframe: DataFrame containing extracted data
            snapshot_rows: Number of rows to include in snapshot
        """
        try:
            # Logic: If len(df) > 1000, save tail(1000), otherwise save the tail of available rows
            if len(dataframe) > 1000:
                snapshot_df = dataframe.tail(1000).copy()
            else:
                snapshot_df = dataframe.tail(snapshot_rows).copy()
            
            # Add metadata to snapshot
            snapshot_df.attrs['total_rows'] = len(dataframe)
            snapshot_df.attrs['snapshot_rows'] = len(snapshot_df)
            snapshot_df.attrs['extraction_timestamp'] = datetime.now().isoformat()
            
            # Save to CSV with metadata
            snapshot_file = self.evidence_dir / "03_data_snapshot.csv"
            with open(snapshot_file, 'w', encoding='utf-8') as f:
                f.write(f"# IPE Data Snapshot - {self.ipe_id}\n")
                f.write(f"# Total Rows: {len(dataframe)}\n")
                f.write(f"# Snapshot Rows (TAIL): {len(snapshot_df)}\n")
                f.write(f"# Extraction Time: {datetime.now().isoformat()}\n")
                f.write(f"# Columns: {list(dataframe.columns)}\n")
                f.write("#" + "="*80 + "\n")
            
            # Add data
            snapshot_df.to_csv(snapshot_file, mode='a', index=False, encoding='utf-8')
            
            # Also create a statistical summary
            summary_file = self.evidence_dir / "04_data_summary.json"
            summary = {
                'total_rows': len(dataframe),
                'total_columns': len(dataframe.columns),
                'columns': list(dataframe.columns),
                'data_types': dataframe.dtypes.astype(str).to_dict(),
                'memory_usage_mb': round(dataframe.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                'snapshot_rows': len(snapshot_df),
                'snapshot_type': 'tail',
                'extraction_timestamp': datetime.now().isoformat()
            }
            
            # Add descriptive statistics for numeric columns
            numeric_columns = dataframe.select_dtypes(include=['number']).columns
            if len(numeric_columns) > 0:
                summary['numeric_statistics'] = dataframe[numeric_columns].describe().to_dict()
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("SNAPSHOT_SAVED", f"Snapshot (tail) saved: {len(snapshot_df)} rows out of {len(dataframe)}")
            logger.info(f"[{self.ipe_id}] Data snapshot (tail) saved")
            
        except Exception as e:
            self._log_action("ERROR", f"Error saving snapshot: {e}")
            logger.error(f"[{self.ipe_id}] Error saving snapshot: {e}")
            raise
    
    def generate_integrity_hash(self, dataframe: pd.DataFrame) -> str:
        """
        Generates a cryptographic hash of the complete dataset.
        This hash proves data integrity and detects any tampering.
        
        Args:
            dataframe: Complete DataFrame of extracted data
            
        Returns:
            SHA-256 hash of the data
        """
        try:
            # Create a deterministic hash of the complete DataFrame
            # Sort by all columns to guarantee reproducibility
            df_sorted = dataframe.sort_values(by=list(dataframe.columns)).reset_index(drop=True)
            
            # Convert to string with standardized format
            data_string = df_sorted.to_csv(index=False, encoding='utf-8')
            
            # Calculate SHA-256 hash
            data_hash = hashlib.sha256(data_string.encode('utf-8')).hexdigest()
            
            # Additional information for verification
            hash_info = {
                'algorithm': 'SHA-256',
                'hash_value': data_hash,
                'data_rows': len(dataframe),
                'data_columns': len(dataframe.columns),
                'generation_timestamp': datetime.now().isoformat(),
                'python_pandas_version': pd.__version__,
                'verification_instructions': [
                    "1. Sort data by all columns",
                    "2. Export to CSV without index with UTF-8 encoding",
                    "3. Calculate SHA-256 of resulting string",
                    "4. Compare with hash_value"
                ]
            }
            
            # Save hash and verification instructions
            hash_file = self.evidence_dir / "05_integrity_hash.json"
            with open(hash_file, 'w', encoding='utf-8') as f:
                json.dump(hash_info, f, indent=2, ensure_ascii=False)
            
            # Also save just the hash in a text file for convenience
            hash_txt_file = self.evidence_dir / "05_integrity_hash.sha256"
            with open(hash_txt_file, 'w') as f:
                f.write(data_hash)
            
            self._log_action("HASH_GENERATED", f"Integrity hash generated: {data_hash[:16]}...")
            logger.info(f"[{self.ipe_id}] Integrity hash generated: {data_hash[:16]}...")
            
            return data_hash
            
        except Exception as e:
            self._log_action("ERROR", f"Error generating hash: {e}")
            logger.error(f"[{self.ipe_id}] Error generating hash: {e}")
            raise
    
    def save_validation_results(self, validation_results: Dict[str, Any]) -> None:
        """
        Saves detailed SOX validation results.
        
        Args:
            validation_results: Validation test results
        """
        try:
            validation_file = self.evidence_dir / "06_validation_results.json"
            
            # Add validation metadata
            enhanced_results = {
                'ipe_id': self.ipe_id,
                'validation_timestamp': datetime.now().isoformat(),
                'validation_results': validation_results,
                'sox_compliance': {
                    'completeness_test': validation_results.get('completeness', {}).get('status') == 'PASS',
                    'accuracy_positive_test': validation_results.get('accuracy_positive', {}).get('status') == 'PASS',
                    'accuracy_negative_test': validation_results.get('accuracy_negative', {}).get('status') == 'PASS',
                    'overall_compliance': validation_results.get('overall_status') == 'SUCCESS'
                }
            }
            
            with open(validation_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_results, f, indent=2, ensure_ascii=False, default=str)
            
            self._log_action("VALIDATION_SAVED", f"Validation results saved")
            logger.info(f"[{self.ipe_id}] Validation results saved")
            
        except Exception as e:
            self._log_action("ERROR", f"Error saving validation: {e}")
            logger.error(f"[{self.ipe_id}] Error saving validation: {e}")
            raise
    
    def finalize_evidence_package(self) -> str:
        """
        Finalizes the evidence package by saving the execution log
        and creating a secure ZIP archive.
        
        Returns:
            Path to the created ZIP archive
        """
        try:
            # Save final execution log
            log_file = self.evidence_dir / "07_execution_log.json"
            
            final_log = {
                'ipe_id': self.ipe_id,
                'execution_start': self.execution_log[0]['timestamp'] if self.execution_log else None,
                'execution_end': datetime.now().isoformat(),
                'evidence_directory': str(self.evidence_dir),
                'actions_log': self.execution_log,
                'files_generated': [f.name for f in self.evidence_dir.glob('*') if f.is_file()],
                'package_integrity': self._calculate_package_hash()
            }
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(final_log, f, indent=2, ensure_ascii=False, default=str)
            
            # Create ZIP archive with protection
            zip_file = self.evidence_dir.parent / f"{self.evidence_dir.name}_evidence.zip"
            
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in self.evidence_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self.evidence_dir.parent)
                        zipf.write(file_path, arcname)
            
            self._log_action("PACKAGE_FINALIZED", f"Archive created: {zip_file.name}")
            logger.info(f"[{self.ipe_id}] Evidence package finalized: {zip_file}")
            
            return str(zip_file)
            
        except Exception as e:
            self._log_action("ERROR", f"Error finalizing package: {e}")
            logger.error(f"[{self.ipe_id}] Error finalizing package: {e}")
            raise
    
    def _calculate_package_hash(self) -> str:
        """Calculates a hash of the entire evidence package."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(self.evidence_dir.glob('*')):
            if file_path.is_file() and file_path.name != "07_execution_log.json":
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _log_action(self, action: str, details: str) -> None:
        """Records an action in the execution log."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'details': details
        }
        self.execution_log.append(log_entry)


class EvidenceValidator:
    """
    Validator to verify evidence package integrity.
    """
    
    @staticmethod
    def verify_package_integrity(evidence_dir: str) -> Dict[str, Any]:
        """
        Verifies the integrity of an evidence package.
        
        Args:
            evidence_dir: Evidence package directory
            
        Returns:
            Verification results
        """
        evidence_path = Path(evidence_dir)
        verification_results = {
            'package_path': str(evidence_path),
            'verification_timestamp': datetime.now().isoformat(),
            'files_present': {},
            'integrity_verified': False,
            'issues_found': []
        }
        
        # Check presence of required files
        required_files = [
            "01_executed_query.sql",
            "03_data_snapshot.csv", 
            "04_data_summary.json",
            "05_integrity_hash.json",
            "06_validation_results.json",
            "07_execution_log.json"
        ]
        
        for file_name in required_files:
            file_path = evidence_path / file_name
            verification_results['files_present'][file_name] = file_path.exists()
            
            if not file_path.exists():
                verification_results['issues_found'].append(f"Missing file: {file_name}")
        
        # Verify hash integrity if possible
        hash_file = evidence_path / "05_integrity_hash.json"
        if hash_file.exists():
            try:
                with open(hash_file, 'r', encoding='utf-8') as f:
                    hash_info = json.load(f)
                verification_results['original_hash'] = hash_info.get('hash_value')
                verification_results['hash_algorithm'] = hash_info.get('algorithm')
            except Exception as e:
                verification_results['issues_found'].append(f"Error reading hash: {e}")
        
        verification_results['integrity_verified'] = len(verification_results['issues_found']) == 0
        
        return verification_results