# ipe_runner.py
"""
Classe IPERunner pour encapsuler la logique d'extraction et de validation d'un seul IPE.
Cette classe gère l'exécution complète d'un IPE, de la connexion à la base de données
jusqu'à la validation des données extraites.
"""

import logging
import pandas as pd
import pyodbc
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from gcp_utils import GCPSecretManager
from evidence_manager import DigitalEvidenceManager, IPEEvidenceGenerator

# Configuration du logging
logger = logging.getLogger(__name__)


class IPEValidationError(Exception):
    """Exception levée en cas d'échec de validation d'un IPE."""
    pass


class IPEConnectionError(Exception):
    """Exception levée en cas de problème de connexion à la base de données."""
    pass


class IPERunner:
    """
    Classe responsable de l'exécution d'un seul IPE.
    Gère l'extraction, la validation et le nettoyage des données.
    """
    
    def __init__(self, ipe_config: Dict[str, Any], secret_manager: GCPSecretManager,
                 cutoff_date: Optional[str] = None, evidence_manager: Optional[DigitalEvidenceManager] = None):
        """
        Initialise le runner pour un IPE spécifique.
        
        Args:
            ipe_config: Configuration de l'IPE (depuis config.py)
            secret_manager: Instance du gestionnaire de secrets GCP
            cutoff_date: Date de coupure pour les extractions (format: YYYY-MM-DD)
            evidence_manager: Gestionnaire d'évidence digitale pour SOX
        """
        self.config = ipe_config
        self.secret_manager = secret_manager
        self.ipe_id = ipe_config['id']
        self.description = ipe_config['description']
        
        # Date de coupure par défaut: premier jour du mois courant
        if cutoff_date:
            self.cutoff_date = cutoff_date
        else:
            today = datetime.now()
            first_day_of_month = today.replace(day=1)
            self.cutoff_date = first_day_of_month.strftime('%Y-%m-%d')
        
        self.connection = None
        self.extracted_data = None
        self.validation_results = {}
        
        # Gestionnaire d'évidence SOX
        self.evidence_manager = evidence_manager or DigitalEvidenceManager()
        self.evidence_generator = None
        
        logger.info(f"IPERunner initialisé pour {self.ipe_id} - Date de coupure: {self.cutoff_date}")
    
    def _get_database_connection(self) -> pyodbc.Connection:
        """
        Établit la connexion à la base de données en utilisant les credentials du Secret Manager.
        
        Returns:
            Connexion pyodbc à la base de données
            
        Raises:
            IPEConnectionError: En cas d'échec de connexion
        """
        try:
            # Récupérer la chaîne de connexion depuis le Secret Manager
            connection_string = self.secret_manager.get_secret(self.config['secret_name'])
            
            # Établir la connexion
            connection = pyodbc.connect(connection_string)
            logger.info(f"[{self.ipe_id}] Connexion à la base de données établie")
            return connection
            
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Erreur de connexion à la base de données: {e}"
            logger.error(error_msg)
            raise IPEConnectionError(error_msg)
    
    def _execute_query_with_parameters(self, query: str, parameters: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Exécute une requête SQL avec des paramètres sécurisés.
        
        Args:
            query: La requête SQL à exécuter
            parameters: Les paramètres à injecter dans la requête
            
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
            
            # Construire la requête de validation
            main_query = self.config['main_query']
            completeness_query = self.config['validation']['completeness_query'].format(
                main_query=f"({main_query})"
            )
            
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
            
            # Construire la requête de validation
            main_query = self.config['main_query']
            accuracy_query = self.config['validation']['accuracy_positive_query'].format(
                main_query=f"({main_query})"
            )
            
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
            
            # Créer une version modifiée de la requête principale pour le test négatif
            main_query = self.config['main_query']
            
            # Logique spécifique pour modifier la requête selon l'IPE
            if self.ipe_id == "IPE_07":
                # Exemple de modification pour IPE_07
                main_query_modified = main_query.replace(
                    "in ('13010','13009','13006','13005','13004','13003')",
                    "in ('13010','13006','13005','13004','13003')"
                )
            else:
                # Pour les autres IPE, utiliser la requête originale
                main_query_modified = main_query
            
            # Construire la requête de validation
            accuracy_query = self.config['validation']['accuracy_negative_query'].format(
                main_query_modified=f"({main_query_modified})"
            )
            
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
    
    def _extract_main_data(self) -> pd.DataFrame:
        """
        Extrait les données principales selon la configuration de l'IPE.
        
        Returns:
            DataFrame contenant les données extraites
        """
        try:
            logger.info(f"[{self.ipe_id}] Démarrage de l'extraction des données principales...")
            
            main_query = self.config['main_query']
            dataframe = self._execute_query_with_parameters(main_query)
            
            # Ajout de métadonnées
            dataframe['_ipe_id'] = self.ipe_id
            dataframe['_extraction_date'] = datetime.now().isoformat()
            dataframe['_cutoff_date'] = self.cutoff_date
            
            logger.info(f"[{self.ipe_id}] Extraction terminée: {len(dataframe)} lignes extraites")
            return dataframe
            
        except Exception as e:
            error_msg = f"[{self.ipe_id}] Erreur lors de l'extraction des données: {e}"
            logger.error(error_msg)
            raise
    
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
        Exécute l'IPE complet: extraction et validation.
        
        Returns:
            DataFrame contenant les données extraites et validées
            
        Raises:
            IPEValidationError: En cas d'échec de validation
            IPEConnectionError: En cas de problème de connexion
        """
        try:
            logger.info(f"[{self.ipe_id}] ==> DÉBUT DE L'EXÉCUTION DE L'IPE")
            
            # 1. Établir la connexion
            self.connection = self._get_database_connection()
            
            # 2. Extraire les données principales
            self.extracted_data = self._extract_main_data()
            
            # 3. Exécuter les validations
            logger.info(f"[{self.ipe_id}] Démarrage des validations...")
            
            self._validate_completeness(self.extracted_data)
            self._validate_accuracy_positive()
            self._validate_accuracy_negative()
            
            # 4. Marquer le succès
            self.validation_results['overall_status'] = 'SUCCESS'
            self.validation_results['execution_time'] = datetime.now().isoformat()
            
            logger.info(f"[{self.ipe_id}] ==> IPE EXÉCUTÉ AVEC SUCCÈS - "
                       f"{len(self.extracted_data)} lignes validées")
            
            return self.extracted_data
            
        except (IPEValidationError, IPEConnectionError):
            self.validation_results['overall_status'] = 'FAILED'
            raise
        except Exception as e:
            self.validation_results['overall_status'] = 'ERROR'
            error_msg = f"[{self.ipe_id}] Erreur inattendue lors de l'exécution: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
        finally:
            # 5. Nettoyer les ressources
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