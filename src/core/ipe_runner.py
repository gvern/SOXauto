# ipe_runner.py
"""
IPERunner class to encapsulate the extraction and validation logic for a single IPE.
This class manages the complete execution of an IPE, from database connection
to data validation and evidence generation.
"""

import logging
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from src.utils.gcp_utils import GCPSecretManager
from src.core.evidence_manager import DigitalEvidenceManager, IPEEvidenceGenerator

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
    
    def __init__(self, ipe_config: Dict[str, Any], secret_manager: GCPSecretManager,
                 cutoff_date: Optional[str] = None, evidence_manager: Optional[DigitalEvidenceManager] = None):
        """
        Initialize the runner for a specific IPE.
        
        Args:
            ipe_config: IPE configuration (from config.py)
            secret_manager: GCP secret manager instance
            cutoff_date: Cutoff date for extractions (format: YYYY-MM-DD)
            evidence_manager: Digital evidence manager for SOX compliance
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
        
        logger.info(f"IPERunner initialized for {self.ipe_id} - Cutoff date: {self.cutoff_date}")
    
    def _get_database_connection(self) -> pyodbc.Connection:
        """
        Establish database connection using credentials from Secret Manager.
        
        Returns:
            pyodbc connection to the database
            
        Raises:
            IPEConnectionError: If connection fails
        """
        try:
            # Retrieve connection string from Secret Manager
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
                # Compter le nombre de placeholders dans la requête
                placeholder_count = query.count('?')
                parameters = tuple([self.cutoff_date] * placeholder_count)
            
            logger.debug(f"[{self.ipe_id}] Exécution de la requête avec paramètres: {parameters}")
            df = pd.read_sql(query, self.connection, params=parameters)
            logger.info(f"[{self.ipe_id}] Requête exécutée: {len(df)} lignes retournées")
            return df
            
        except Exception as e:
            logger.error(f"[{self.ipe_id}] Erreur lors de l'exécution de la requête: {e}")
            raise
    
    def _validate_completeness(self, main_dataframe: pd.DataFrame) -> bool:
        """
        Validation de complétude: vérifie que toutes les données attendues sont présentes.
        
        Args:
            main_dataframe: Le DataFrame principal à valider
            
        Returns:
            True si la validation réussit, False sinon
            
        Raises:
            IPEValidationError: En cas d'échec de validation
        """
        try:
            logger.info(f"[{self.ipe_id}] Démarrage de la validation de complétude...")
            
            if 'completeness_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] Pas de requête de complétude définie")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            completeness_query = self.config['validation']['completeness_query']
            
            # Exécuter la validation
            validation_df = self._execute_query_with_parameters(completeness_query)
            expected_count = validation_df.iloc[0, 0]
            actual_count = len(main_dataframe)
            
            self.validation_results['completeness'] = {
                'expected_count': expected_count,
                'actual_count': actual_count,
                'status': 'PASS' if expected_count == actual_count else 'FAIL'
            }
            
            if expected_count != actual_count:
                error_msg = (f"[{self.ipe_id}] Échec de validation de complétude. "
                           f"Attendu: {expected_count}, Obtenu: {actual_count}")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Validation de complétude: SUCCÈS ({actual_count} lignes)")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Erreur lors de la validation de complétude: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _validate_accuracy_positive(self) -> bool:
        """
        Validation d'exactitude positive: vérifie qu'une transaction témoin est présente.
        
        Returns:
            True si la validation réussit, False sinon
            
        Raises:
            IPEValidationError: En cas d'échec de validation
        """
        try:
            logger.info(f"[{self.ipe_id}] Démarrage de la validation d'exactitude positive...")
            
            if 'accuracy_positive_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] Pas de requête d'exactitude positive définie")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            accuracy_query = self.config['validation']['accuracy_positive_query']
            
            # Exécuter la validation
            validation_df = self._execute_query_with_parameters(accuracy_query)
            witness_count = validation_df.iloc[0, 0]
            
            self.validation_results['accuracy_positive'] = {
                'witness_count': witness_count,
                'status': 'PASS' if witness_count > 0 else 'FAIL'
            }
            
            if witness_count == 0:
                error_msg = (f"[{self.ipe_id}] Échec de validation d'exactitude positive. "
                           f"Aucune transaction témoin trouvée")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Validation d'exactitude positive: SUCCÈS ({witness_count} témoins)")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Erreur lors de la validation d'exactitude positive: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _validate_accuracy_negative(self) -> bool:
        """
        Validation d'exactitude négative: vérifie qu'aucune transaction exclue n'est présente.
        
        Returns:
            True si la validation réussit, False sinon
            
        Raises:
            IPEValidationError: En cas d'échec de validation
        """
        try:
            logger.info(f"[{self.ipe_id}] Démarrage de la validation d'exactitude négative...")
            
            if 'accuracy_negative_query' not in self.config['validation']:
                logger.warning(f"[{self.ipe_id}] Pas de requête d'exactitude négative définie")
                return True
            
            # Security: CTEs are now self-contained and don't require .format()
            # Execute the validation query directly with parameters
            accuracy_query = self.config['validation']['accuracy_negative_query']
            
            # Exécuter la validation
            validation_df = self._execute_query_with_parameters(accuracy_query)
            excluded_count = validation_df.iloc[0, 0]
            
            self.validation_results['accuracy_negative'] = {
                'excluded_count': excluded_count,
                'status': 'PASS' if excluded_count == 0 else 'FAIL'
            }
            
            if excluded_count > 0:
                error_msg = (f"[{self.ipe_id}] Échec de validation d'exactitude négative. "
                           f"{excluded_count} transactions exclues trouvées")
                logger.error(error_msg)
                raise IPEValidationError(error_msg)
            
            logger.info(f"[{self.ipe_id}] Validation d'exactitude négative: SUCCÈS")
            return True
            
        except IPEValidationError:
            raise
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Erreur lors de la validation d'exactitude négative: {e}"
            logger.error(error_msg)
            raise IPEValidationError(error_msg)
    
    def _cleanup_connection(self):
        """Ferme proprement la connexion à la base de données."""
        if self.connection:
            try:
                self.connection.close()
                logger.info(f"[{self.ipe_id}] Connexion fermée")
            except Exception as e:
                logger.warning(f"[{self.ipe_id}] Erreur lors de la fermeture de connexion: {e}")
    
    def run(self) -> pd.DataFrame:
        """
        Exécute l'IPE complet: extraction, validation et génération d'évidence SOX.
        
        Returns:
            DataFrame contenant les données extraites et validées
            
        Raises:
            IPEValidationError: En cas d'échec de validation
            IPEConnectionError: En cas de problème de connexion
        """
        try:
            logger.info(f"[{self.ipe_id}] ==> DÉBUT DE L'EXÉCUTION DE L'IPE")
            
            # 1. Créer le package d'évidence SOX
            execution_metadata = {
                'ipe_id': self.ipe_id,
                'description': self.description,
                'cutoff_date': self.cutoff_date,
                'execution_start': datetime.now().isoformat(),
                'secret_name': self.config['secret_name'],
                'sox_compliance_required': True
            }
            
            evidence_dir = self.evidence_manager.create_evidence_package(
                self.ipe_id, execution_metadata
            )
            self.evidence_generator = IPEEvidenceGenerator(evidence_dir, self.ipe_id)
            
            # 2. Établir la connexion
            self.connection = self._get_database_connection()
            
            # 3. Extraire les données principales
            logger.info(f"[{self.ipe_id}] Extraction des données principales...")
            main_query = self.config['main_query']
            
            # Compter le nombre de placeholders et préparer les paramètres
            placeholder_count = main_query.count('?')
            parameters = [self.cutoff_date] * placeholder_count
            
            # Sauvegarder la requête exacte avec paramètres AVANT l'exécution
            self.evidence_generator.save_executed_query(
                main_query, 
                {'cutoff_date': self.cutoff_date, 'parameters': parameters}
            )
            
            # Exécuter la requête
            self.extracted_data = self._execute_query_with_parameters(main_query, tuple(parameters))
            
            # Ajouter des métadonnées de traçabilité
            self.extracted_data['_ipe_id'] = self.ipe_id
            self.extracted_data['_extraction_date'] = datetime.now().isoformat()
            self.extracted_data['_cutoff_date'] = self.cutoff_date
            
            # 4. Générer immédiatement les preuves des données extraites
            logger.info(f"[{self.ipe_id}] Génération des preuves d'évidence...")
            self.evidence_generator.save_data_snapshot(self.extracted_data)
            integrity_hash = self.evidence_generator.generate_integrity_hash(self.extracted_data)
            
            logger.info(f"[{self.ipe_id}] Données extraites: {len(self.extracted_data)} lignes, "
                       f"Hash: {integrity_hash[:16]}...")
            
            # 5. Exécuter les validations SOX
            logger.info(f"[{self.ipe_id}] Démarrage des validations SOX...")
            
            self._validate_completeness(self.extracted_data)
            self._validate_accuracy_positive()
            self._validate_accuracy_negative()
            
            # 6. Sauvegarder les résultats de validation
            self.validation_results['overall_status'] = 'SUCCESS'
            self.validation_results['execution_time'] = datetime.now().isoformat()
            self.validation_results['data_integrity_hash'] = integrity_hash
            
            self.evidence_generator.save_validation_results(self.validation_results)
            
            # 7. Finaliser le package d'évidence
            evidence_zip = self.evidence_generator.finalize_evidence_package()
            
            logger.info(f"[{self.ipe_id}] ==> IPE EXÉCUTÉ AVEC SUCCÈS - "
                       f"{len(self.extracted_data)} lignes validées")
            logger.info(f"[{self.ipe_id}] Package d'évidence SOX: {evidence_zip}")
            
            return self.extracted_data
            
        except (IPEValidationError, IPEConnectionError):
            self.validation_results['overall_status'] = 'FAILED'
            if self.evidence_generator:
                self.evidence_generator.save_validation_results(self.validation_results)
                self.evidence_generator.finalize_evidence_package()
            raise
        except Exception as e:
            self.validation_results['overall_status'] = 'ERROR'
            error_msg = f"[{self.ipe_id}] Erreur inattendue lors de l'exécution: {e}"
            if self.evidence_generator:
                self.evidence_generator.save_validation_results(self.validation_results)
                self.evidence_generator.finalize_evidence_package()
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            # 8. Nettoyer les ressources
            self._cleanup_connection()
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé des résultats de validation.
        
        Returns:
            Dictionnaire contenant le résumé des validations
        """
        return {
            'ipe_id': self.ipe_id,
            'description': self.description,
            'cutoff_date': self.cutoff_date,
            'extracted_rows': len(self.extracted_data) if self.extracted_data is not None else 0,
            'validation_results': self.validation_results
        }