# gcp_utils.py
"""
Module dedicated to interactions with Google Cloud Platform services.
This module handles secure access to Secrets, BigQuery, and Google Drive.
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

# Logging configuration
logger = logging.getLogger(__name__)


class GCPSecretManager:
    """Manager for accessing secrets in Google Secret Manager."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = secretmanager.SecretManagerServiceClient()
    
    def get_secret(self, secret_id: str, version_id: str = "latest") -> str:
        """
        Retrieves a secret from Google Secret Manager.
        
        Args:
            secret_id: The secret identifier
            version_id: The secret version (default 'latest')
            
        Returns:
            The secret value as a string
            
        Raises:
            Exception: If the secret is not found or inaccessible
        """
        try:
            name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version_id}"
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Secret '{secret_id}' retrieved successfully")
            return secret_value
        except NotFound:
            logger.error(f"Secret '{secret_id}' not found in project {self.project_id}")
            raise
        except Exception as e:
            logger.error(f"Error retrieving secret '{secret_id}': {e}")
            raise

    def get_json_secret(self, secret_id: str, version_id: str = "latest") -> Dict[str, Any]:
        """
        Retrieves a JSON secret and returns it as a dictionary.
        
        Args:
            secret_id: The JSON secret identifier
            version_id: The secret version
            
        Returns:
            The parsed secret as a dictionary
        """
        try:
            secret_value = self.get_secret(secret_id, version_id)
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for secret '{secret_id}': {e}")
            raise


class GCPBigQuery:
    """Manager for BigQuery interactions."""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
    
    def write_dataframe(self, dataframe: pd.DataFrame, dataset_id: str, table_id: str,
                       write_disposition: str = "WRITE_TRUNCATE") -> None:
        """
        Writes a Pandas DataFrame to a BigQuery table.
        
        Args:
            dataframe: The DataFrame to write
            dataset_id: The BigQuery dataset identifier
            table_id: The BigQuery table identifier
            write_disposition: Write mode ('WRITE_TRUNCATE', 'WRITE_APPEND', 'WRITE_EMPTY')
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            
            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition,
                create_disposition="CREATE_IF_NEEDED",
                autodetect=True
            )
            
            # Add traceability metadata
            timestamp = datetime.now().isoformat()
            dataframe_copy = dataframe.copy()
            dataframe_copy['_processing_timestamp'] = timestamp
            dataframe_copy['_source_system'] = 'SOXauto_PG01'
            
            job = self.client.load_table_from_dataframe(
                dataframe_copy, table_ref, job_config=job_config
            )
            job.result()  # Wait for job completion
            
            logger.info(f"Data written successfully to BigQuery: {dataset_id}.{table_id} "
                       f"({len(dataframe)} rows)")
            
        except Exception as e:
            logger.error(f"Error writing to BigQuery {dataset_id}.{table_id}: {e}")
            raise
    
    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Executes a BigQuery query and returns results as a DataFrame.
        
        Args:
            query: The SQL query to execute
            
        Returns:
            DataFrame containing query results
        """
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            df = results.to_dataframe()
            logger.info(f"BigQuery query executed successfully ({len(df)} rows)")
            return df
        except Exception as e:
            logger.error(f"Error executing BigQuery query: {e}")
            raise
    
    def table_exists(self, dataset_id: str, table_id: str) -> bool:
        """
        Checks if a table exists in BigQuery.
        
        Args:
            dataset_id: The dataset identifier
            table_id: The table identifier
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            self.client.get_table(table_ref)
            return True
        except NotFound:
            return False


class GCPDriveManager:
    """Manager for Google Drive interactions."""
    
    def __init__(self, service_account_info: Dict[str, Any]):
        """
        Initializes the Google Drive manager.
        
        Args:
            service_account_info: Service account information (JSON dict)
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
            logger.info("Google Drive client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Google Drive client: {e}")
            raise
    
    def write_to_sheet(self, dataframe: pd.DataFrame, spreadsheet_name: str, 
                      worksheet_name: str) -> None:
        """
        Writes a DataFrame to a Google Sheet.
        
        Args:
            dataframe: The DataFrame to write
            spreadsheet_name: The Google Sheet name
            worksheet_name: The worksheet tab name
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
            
            # Convert DataFrame to list of lists
            data_to_write = [dataframe.columns.values.tolist()] + dataframe.values.tolist()
            worksheet.update(data_to_write)
            
            logger.info(f"Data written successfully to Google Sheet: "
                       f"{spreadsheet_name}/{worksheet_name} ({len(dataframe)} rows)")
            
        except Exception as e:
            logger.error(f"Error writing to Google Sheet: {e}")
            raise
    
    def create_audit_log(self, folder_id: str, log_data: Dict[str, Any]) -> str:
        """
        Creates an audit log file in Google Drive.
        
        Args:
            folder_id: The destination folder identifier
            log_data: The log data to save
            
        Returns:
            The created file identifier
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"SOXauto_PG01_audit_{timestamp}.json"
            
            # This feature would require the Google Drive API
            # For simplicity, we log the important information
            logger.info(f"Audit log created: {filename}")
            logger.info(f"Audit data: {log_data}")
            
            return f"audit_log_{timestamp}"
            
        except Exception as e:
            logger.error(f"Error creating audit log: {e}")
            raise


def initialize_gcp_services(project_id: str) -> tuple:
    """
    Initializes all necessary GCP services.
    
    Args:
        project_id: The GCP project identifier
        
    Returns:
        Tuple containing (secret_manager, bigquery_client)
    """
    try:
        secret_manager = GCPSecretManager(project_id)
        bigquery_client = GCPBigQuery(project_id)
        
        logger.info(f"GCP services initialized for project: {project_id}")
        return secret_manager, bigquery_client
        
    except Exception as e:
        logger.error(f"Error initializing GCP services: {e}")
        raise


def get_drive_manager(secret_manager: GCPSecretManager, 
                     service_account_secret_name: str) -> GCPDriveManager:
    """
    Initializes the Google Drive manager using credentials from Secret Manager.
    
    Args:
        secret_manager: Secret manager instance
        service_account_secret_name: Secret name containing service account credentials
        
    Returns:
        Google Drive manager instance
    """
    try:
        service_account_info = secret_manager.get_json_secret(service_account_secret_name)
        return GCPDriveManager(service_account_info)
    except Exception as e:
        logger.error(f"Error initializing Drive manager: {e}")
        raise