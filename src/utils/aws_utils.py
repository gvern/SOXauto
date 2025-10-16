# aws_utils.py
"""
Module dedicated to interactions with Amazon Web Services (AWS).
This module handles secure access to Secrets Manager, Redshift, Athena, and S3.
"""

import logging
import pandas as pd
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
from datetime import datetime
from typing import Optional, Dict, Any
import io

# Logging configuration
logger = logging.getLogger(__name__)


class AWSSecretsManager:
    """Manager for accessing secrets in AWS Secrets Manager."""
    
    def __init__(self, region_name: str = 'eu-west-1'):
        """
        Initializes the AWS Secrets Manager client.
        
        Args:
            region_name: AWS region (default 'eu-west-1')
        """
        self.region_name = region_name
        try:
            self.client = boto3.client('secretsmanager', region_name=region_name)
            logger.info(f"AWS Secrets Manager client initialized for region: {region_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure credentials properly.")
            raise
    
    def get_secret(self, secret_name: str) -> str:
        """
        Retrieves a secret from AWS Secrets Manager.
        
        Args:
            secret_name: The secret identifier
            
        Returns:
            The secret value as a string
            
        Raises:
            Exception: If the secret is not found or inaccessible
        """
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            
            # Secrets Manager returns either SecretString or SecretBinary
            if 'SecretString' in response:
                secret_value = response['SecretString']
            else:
                secret_value = response['SecretBinary'].decode('utf-8')
                
            logger.info(f"Secret '{secret_name}' retrieved successfully")
            return secret_value
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                logger.error(f"Secret '{secret_name}' not found in region {self.region_name}")
            elif error_code == 'InvalidRequestException':
                logger.error(f"Invalid request for secret '{secret_name}'")
            elif error_code == 'InvalidParameterException':
                logger.error(f"Invalid parameter for secret '{secret_name}'")
            else:
                logger.error(f"Error retrieving secret '{secret_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving secret '{secret_name}': {e}")
            raise

    def get_json_secret(self, secret_name: str) -> Dict[str, Any]:
        """
        Retrieves a JSON secret and returns it as a dictionary.
        
        Args:
            secret_name: The JSON secret identifier
            
        Returns:
            The parsed secret as a dictionary
        """
        try:
            secret_value = self.get_secret(secret_name)
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error for secret '{secret_name}': {e}")
            raise


class AWSRedshift:
    """Manager for Amazon Redshift interactions."""
    
    def __init__(self, cluster_endpoint: str, database: str, user: str, 
                 password: str, port: int = 5439):
        """
        Initializes the Redshift connection.
        
        Args:
            cluster_endpoint: Redshift cluster endpoint
            database: Database name
            user: Database user
            password: Database password
            port: Database port (default 5439)
        """
        self.cluster_endpoint = cluster_endpoint
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        
        try:
            import psycopg2
            self.connection = psycopg2.connect(
                host=cluster_endpoint,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"Connected to Redshift cluster: {cluster_endpoint}")
        except ImportError:
            logger.error("psycopg2 not installed. Install with: pip install psycopg2-binary")
            raise
        except Exception as e:
            logger.error(f"Error connecting to Redshift: {e}")
            raise
    
    def write_dataframe(self, dataframe: pd.DataFrame, schema: str, table: str,
                       write_mode: str = "replace") -> None:
        """
        Writes a Pandas DataFrame to a Redshift table.
        
        Args:
            dataframe: The DataFrame to write
            schema: The Redshift schema
            table: The table name
            write_mode: Write mode ('replace', 'append')
        """
        try:
            # Add traceability metadata
            timestamp = datetime.now().isoformat()
            dataframe_copy = dataframe.copy()
            dataframe_copy['_processing_timestamp'] = timestamp
            dataframe_copy['_source_system'] = 'SOXauto_PG01'
            
            # Use pandas to_sql with SQLAlchemy
            from sqlalchemy import create_engine
            
            connection_string = f"postgresql+psycopg2://{self.user}:{self.password}@{self.cluster_endpoint}:{self.port}/{self.database}"
            engine = create_engine(connection_string)
            
            if_exists_mode = 'replace' if write_mode == 'replace' else 'append'
            
            dataframe_copy.to_sql(
                name=table,
                schema=schema,
                con=engine,
                if_exists=if_exists_mode,
                index=False,
                method='multi'
            )
            
            logger.info(f"Data written successfully to Redshift: {schema}.{table} "
                       f"({len(dataframe)} rows)")
            
        except Exception as e:
            logger.error(f"Error writing to Redshift {schema}.{table}: {e}")
            raise
    
    def query_to_dataframe(self, query: str) -> pd.DataFrame:
        """
        Executes a Redshift query and returns results as a DataFrame.
        
        Args:
            query: The SQL query to execute
            
        Returns:
            DataFrame containing query results
        """
        try:
            df = pd.read_sql_query(query, self.connection)
            logger.info(f"Redshift query executed successfully ({len(df)} rows)")
            return df
        except Exception as e:
            logger.error(f"Error executing Redshift query: {e}")
            raise
    
    def close(self):
        """Closes the Redshift connection."""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Redshift connection closed")
        except Exception as e:
            logger.error(f"Error closing Redshift connection: {e}")


class AWSAthena:
    """Manager for Amazon Athena interactions."""
    
    def __init__(self, region_name: str = 'eu-west-1', 
                 s3_output_location: str = None):
        """
        Initializes the Athena client.
        
        Args:
            region_name: AWS region
            s3_output_location: S3 location for query results
        """
        self.region_name = region_name
        self.s3_output_location = s3_output_location
        
        try:
            self.client = boto3.client('athena', region_name=region_name)
            logger.info(f"AWS Athena client initialized for region: {region_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure credentials properly.")
            raise
    
    def query_to_dataframe(self, query: str, database: str) -> pd.DataFrame:
        """
        Executes an Athena query and returns results as a DataFrame.
        
        Args:
            query: The SQL query to execute
            database: The Athena database name
            
        Returns:
            DataFrame containing query results
        """
        try:
            # Start query execution
            response = self.client.start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database},
                ResultConfiguration={'OutputLocation': self.s3_output_location}
            )
            
            query_execution_id = response['QueryExecutionId']
            logger.info(f"Athena query started: {query_execution_id}")
            
            # Wait for query to complete
            import time
            while True:
                query_status = self.client.get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                status = query_status['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                    break
                    
                time.sleep(1)
            
            if status == 'SUCCEEDED':
                # Get results
                result = self.client.get_query_results(
                    QueryExecutionId=query_execution_id
                )
                
                # Parse results into DataFrame
                columns = [col['Label'] for col in result['ResultSet']['ResultSetMetadata']['ColumnInfo']]
                rows = []
                
                for row in result['ResultSet']['Rows'][1:]:  # Skip header row
                    rows.append([col.get('VarCharValue', '') for col in row['Data']])
                
                df = pd.DataFrame(rows, columns=columns)
                logger.info(f"Athena query executed successfully ({len(df)} rows)")
                return df
            else:
                error_message = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                logger.error(f"Athena query failed: {error_message}")
                raise Exception(f"Athena query failed: {error_message}")
                
        except Exception as e:
            logger.error(f"Error executing Athena query: {e}")
            raise


class AWSS3Manager:
    """Manager for Amazon S3 interactions."""
    
    def __init__(self, region_name: str = 'eu-west-1'):
        """
        Initializes the S3 client.
        
        Args:
            region_name: AWS region
        """
        self.region_name = region_name
        
        try:
            self.client = boto3.client('s3', region_name=region_name)
            self.resource = boto3.resource('s3', region_name=region_name)
            logger.info(f"AWS S3 client initialized for region: {region_name}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Configure credentials properly.")
            raise
    
    def upload_dataframe_as_csv(self, dataframe: pd.DataFrame, bucket: str, 
                                key: str) -> str:
        """
        Uploads a DataFrame to S3 as a CSV file.
        
        Args:
            dataframe: The DataFrame to upload
            bucket: S3 bucket name
            key: S3 object key (path)
            
        Returns:
            S3 URI of the uploaded file
        """
        try:
            csv_buffer = io.StringIO()
            dataframe.to_csv(csv_buffer, index=False)
            
            self.client.put_object(
                Bucket=bucket,
                Key=key,
                Body=csv_buffer.getvalue()
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"DataFrame uploaded to S3: {s3_uri} ({len(dataframe)} rows)")
            return s3_uri
            
        except Exception as e:
            logger.error(f"Error uploading DataFrame to S3 {bucket}/{key}: {e}")
            raise
    
    def upload_file(self, file_path: str, bucket: str, key: str) -> str:
        """
        Uploads a local file to S3.
        
        Args:
            file_path: Path to the local file
            bucket: S3 bucket name
            key: S3 object key (path)
            
        Returns:
            S3 URI of the uploaded file
        """
        try:
            self.client.upload_file(file_path, bucket, key)
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"File uploaded to S3: {s3_uri}")
            return s3_uri
            
        except Exception as e:
            logger.error(f"Error uploading file to S3 {bucket}/{key}: {e}")
            raise
    
    def download_file(self, bucket: str, key: str, local_path: str) -> str:
        """
        Downloads a file from S3 to local path.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            local_path: Local file path to save to
            
        Returns:
            Local file path
        """
        try:
            self.client.download_file(bucket, key, local_path)
            logger.info(f"File downloaded from S3: s3://{bucket}/{key} -> {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Error downloading file from S3 {bucket}/{key}: {e}")
            raise
    
    def list_objects(self, bucket: str, prefix: str = '') -> list:
        """
        Lists objects in an S3 bucket with optional prefix.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix to filter by
            
        Returns:
            List of object keys
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects = [obj['Key'] for obj in response['Contents']]
                logger.info(f"Listed {len(objects)} objects in s3://{bucket}/{prefix}")
                return objects
            else:
                logger.info(f"No objects found in s3://{bucket}/{prefix}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing objects in S3 {bucket}/{prefix}: {e}")
            raise


def initialize_aws_services(region_name: str = 'eu-west-1', 
                           s3_output_location: str = None) -> tuple:
    """
    Initializes all necessary AWS services.
    
    Args:
        region_name: AWS region
        s3_output_location: S3 location for Athena query results
        
    Returns:
        Tuple containing (secrets_manager, s3_manager, athena_client)
    """
    try:
        secrets_manager = AWSSecretsManager(region_name)
        s3_manager = AWSS3Manager(region_name)
        athena_client = AWSAthena(region_name, s3_output_location)
        
        logger.info(f"AWS services initialized for region: {region_name}")
        return secrets_manager, s3_manager, athena_client
        
    except Exception as e:
        logger.error(f"Error initializing AWS services: {e}")
        raise


def get_redshift_connection(secrets_manager: AWSSecretsManager, 
                           secret_name: str) -> AWSRedshift:
    """
    Initializes a Redshift connection using credentials from Secrets Manager.
    
    Args:
        secrets_manager: AWS Secrets Manager instance
        secret_name: Name of the secret containing Redshift credentials
        
    Returns:
        AWSRedshift instance
    """
    try:
        credentials = secrets_manager.get_json_secret(secret_name)
        
        return AWSRedshift(
            cluster_endpoint=credentials['host'],
            database=credentials['database'],
            user=credentials['username'],
            password=credentials['password'],
            port=credentials.get('port', 5439)
        )
    except Exception as e:
        logger.error(f"Error initializing Redshift connection: {e}")
        raise
