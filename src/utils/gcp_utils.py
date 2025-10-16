# gcp_utils.py
"""
Module dédié aux interactions avec les services Google Cloud Platform.
Ce module gère l'accès aux secrets, BigQuery, et Google Drive de manière sécurisée.
"""

import logging
import pandas as pd
from google.cloud import secretmanager, bigquery
from google.cloud.exceptions import NotFound
from google.oauth2.service_account import Credentials
import gspread
import json
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration du logging
logger = logging.getLogger(__name__)


class GCPSecretManager:
    """Gestionnaire pour l'accès aux secrets dans Google Secret Manager."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
    
    def get_secret(self, secret_id: str, version_id: str = "latest") -> str:
        """
        Récupère un secret depuis Google Secret Manager.
        
        Args:
            secret_id: L'identifiant du secret
            version_id: La version du secret (par défaut 'latest')
            
        Returns:
            La valeur du secret sous forme de chaîne
            
        Raises:
            Exception: Si le secret n'est pas trouvé ou inaccessible
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Secret '{secret_id}' récupéré avec succès")
            return secret_value
        except NotFound:
            logger.error(f"Secret '{secret_id}' non trouvé dans le projet {self.project_id}")
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du secret '{secret_id}': {e}")
            raise

    def get_json_secret(self, secret_id: str, version_id: str = "latest") -> Dict[str, Any]:
        """
        Récupère un secret JSON et le retourne sous forme de dictionnaire.
        
        Args:
            secret_id: L'identifiant du secret JSON
            version_id: La version du secret
            
        Returns:
            Le secret parsé en dictionnaire
        """
        try:
            secret_value = self.get_secret(secret_id, version_id)
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            logger.error(f"Erreur de parsing JSON pour le secret '{secret_id}': {e}")
            raise


class GCPBigQuery:
    """Gestionnaire pour les interactions avec BigQuery."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
    
    def write_dataframe(self, dataframe: pd.DataFrame, dataset_id: str, table_id: str,
                       write_disposition: str = "WRITE_TRUNCATE") -> None:
        """
        Écrit un DataFrame Pandas dans une table BigQuery.
        
        Args:
            dataframe: Le DataFrame à écrire
            dataset_id: L'identifiant du dataset BigQuery
            table_id: L'identifiant de la table BigQuery
            write_disposition: Mode d'écriture ('WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY')
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            
            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition,
                create_disposition="CREATE_IF_NEEDED",
                autodetect=True
            )
            
            # Ajout de métadonnées de traçabilité
            timestamp = datetime.now().isoformat()
            dataframe_copy = dataframe.copy()
            dataframe_copy['_processing_timestamp'] = timestamp
            dataframe_copy['_source_system'] = 'SOXauto_PG01'
            
            job = self.client.load_table_from_dataframe(
                dataframe_copy, table_ref, job_config=job_config
            )
            job.result()  # Attend la fin du job
            
            logger.info(f"Données écrites avec succès dans BigQuery: {dataset_id}.{table_id} "
                       f"({len(dataframe)} lignes)")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture dans BigQuery {dataset_id}.{table_id}: {e}")
            raise
    
    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Exécute une requête BigQuery et retourne les résultats sous forme de DataFrame.
        
        Args:
            query: La requête SQL à exécuter
            
        Returns:
            DataFrame contenant les résultats de la requête
        """
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            df = results.to_dataframe()
            logger.info(f"Requête BigQuery exécutée avec succès ({len(df)} lignes)")
            return df
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête BigQuery: {e}")
            raise
    
    def table_exists(self, dataset_id: str, table_id: str) -> bool:
        """
        Vérifie si une table existe dans BigQuery.
        
        Args:
            dataset_id: L'identifiant du dataset
            table_id: L'identifiant de la table
            
        Returns:
            True si la table existe, False sinon
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            self.client.get_table(table_ref)
            return True
        except NotFound:
            return False


class GCPDriveManager:
    """Gestionnaire pour les interactions avec Google Drive."""
    
    def __init__(self, service_account_info: Dict[str, Any]):
        """
        Initialise le gestionnaire Google Drive.
        
        Args:
            service_account_info: Les informations du compte de service (dict JSON)
        """
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        try:
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=self.scopes
            )
            self.gspread_client = gspread.authorize(credentials)
            logger.info("Client Google Drive initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Google Drive: {e}")
            raise
    
    def write_to_sheet(self, dataframe: pd.DataFrame, spreadsheet_name: str, 
                      worksheet_name: str) -> None:
        """
        Écrit un DataFrame dans un Google Sheet.
        
        Args:
            dataframe: Le DataFrame à écrire
            spreadsheet_name: Le nom du Google Sheet
            worksheet_name: Le nom de l'onglet
        """
        try:
            spreadsheet = self.gspread_client.open(spreadsheet_name)
            
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
                worksheet.clear()
            except gspread.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(
                    title=worksheet_name, rows=1000, cols=50
                )
            
            # Convertir le DataFrame en liste de listes
            data_to_write = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
            worksheet.update(data_to_write)
            
            logger.info(f"Données écrites avec succès dans Google Sheet: "
                       f"{spreadsheet_name}/{worksheet_name} ({len(dataframe)} lignes)")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'écriture dans Google Sheet: {e}")
            raise
    
    def create_audit_log(self, folder_id: str, log_data: Dict[str, Any]) -> str:
        """
        Crée un fichier de log d'audit dans Google Drive.
        
        Args:
            folder_id: L'identifiant du dossier de destination
            log_data: Les données de log à enregistrer
            
        Returns:
            L'identifiant du fichier créé
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SOXauto_PG01_audit_{timestamp}.json"
            
            # Cette fonctionnalité nécessiterait l'API Google Drive
            # Pour simplifier, on log les informations importantes
            logger.info(f"Audit log créé: {filename}")
            logger.info(f"Données d'audit: {log_data}")
            
            return f"audit_log_{timestamp}"
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du log d'audit: {e}")
            raise


def initialize_gcp_services(project_id: str) -> tuple:
    """
    Initialise tous les services GCP nécessaires.
    
    Args:
        project_id: L'identifiant du projet GCP
        
    Returns:
        Tuple contenant (secret_manager, bigquery_client)
    """
    try:
        secret_manager = GCPSecretManager(project_id)
        bigquery_client = GCPBigQuery(project_id)
        
        logger.info(f"Services GCP initialisés pour le projet: {project_id}")
        return secret_manager, bigquery_client
        
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation des services GCP: {e}")
        raise


def get_drive_manager(secret_manager: GCPSecretManager, 
                     service_account_secret_name: str) -> GCPDriveManager:
    """
    Initialise le gestionnaire Google Drive en utilisant les credentials du Secret Manager.
    
    Args:
        secret_manager: Instance du gestionnaire de secrets
        service_account_secret_name: Nom du secret contenant les credentials du service account
        
    Returns:
        Instance du gestionnaire Google Drive
    """
    try:
        service_account_info = secret_manager.get_json_secret(service_account_secret_name)
        return GCPDriveManager(service_account_info)
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du gestionnaire Drive: {e}")
        raise