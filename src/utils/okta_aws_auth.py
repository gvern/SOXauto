# okta_aws_auth.py
"""
Okta AWS Authentication Module
Handles AWS authentication through Okta SSO for secure credential management.
"""

import os
import logging
import boto3
import json
import configparser
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import subprocess

logger = logging.getLogger(__name__)


class OktaAWSAuth:
    """
    Manages AWS authentication through Okta SSO.
    
    Supports multiple authentication methods:
    1. AWS SSO (preferred for Okta integration)
    2. Okta AWS CLI tool
    3. Session token caching for efficiency
    """
    
    def __init__(
        self,
        profile_name: Optional[str] = None,
        region_name: str = 'eu-west-1',
        sso_start_url: Optional[str] = None,
        sso_region: Optional[str] = None,
        sso_account_id: Optional[str] = None,
        sso_role_name: Optional[str] = None
    ):
        """
        Initialize Okta AWS authentication.
        
        Args:
            profile_name: AWS CLI profile name (e.g., 'jumia-sox-dev')
            region_name: AWS region (default: 'eu-west-1')
            sso_start_url: Okta SSO start URL
            sso_region: SSO region (usually 'eu-west-1')
            sso_account_id: AWS account ID
            sso_role_name: AWS role name to assume
        """
        self.profile_name = profile_name or os.getenv('AWS_PROFILE', 'default')
        self.region_name = region_name
        self.sso_start_url = sso_start_url or os.getenv('AWS_SSO_START_URL')
        self.sso_region = sso_region or os.getenv('AWS_SSO_REGION', region_name)
        self.sso_account_id = sso_account_id or os.getenv('AWS_SSO_ACCOUNT_ID')
        self.sso_role_name = sso_role_name or os.getenv('AWS_SSO_ROLE_NAME')
        
        self._session = None
        self._credentials_cache = {}
        
        logger.info(f"Initialized Okta AWS Auth with profile: {self.profile_name}")
    
    def get_session(self, force_refresh: bool = False) -> boto3.Session:
        """
        Get an authenticated boto3 session.
        
        Args:
            force_refresh: Force credential refresh even if cached
            
        Returns:
            Authenticated boto3.Session
        """
        if self._session and not force_refresh and self._are_credentials_valid():
            logger.debug("Using cached session")
            return self._session
        
        logger.info("Creating new authenticated session...")
        
        # Try different authentication methods in order of preference
        try:
            # Method 1: Use AWS SSO profile
            if self._is_sso_configured():
                self._session = self._authenticate_via_sso()
            # Method 2: Use standard AWS profile with Okta
            elif self._is_profile_configured():
                self._session = self._authenticate_via_profile()
            # Method 3: Use environment variables
            else:
                self._session = self._authenticate_via_env()
            
            logger.info("✅ AWS session created successfully")
            return self._session
            
        except Exception as e:
            logger.error(f"❌ Failed to create AWS session: {e}")
            raise
    
    def _authenticate_via_sso(self) -> boto3.Session:
        """Authenticate using AWS SSO (preferred for Okta)."""
        logger.info("Authenticating via AWS SSO...")
        
        # Check if SSO login is needed
        try:
            session = boto3.Session(
                profile_name=self.profile_name,
                region_name=self.region_name
            )
            
            # Test credentials
            sts = session.client('sts')
            sts.get_caller_identity()
            
            logger.info("✅ SSO credentials are valid")
            return session
            
        except Exception as e:
            logger.warning(f"SSO login required or expired: {e}")
            logger.info("Initiating SSO login...")
            
            # Trigger SSO login
            self._initiate_sso_login()
            
            # Retry session creation
            session = boto3.Session(
                profile_name=self.profile_name,
                region_name=self.region_name
            )
            
            return session
    
    def _authenticate_via_profile(self) -> boto3.Session:
        """Authenticate using AWS CLI profile."""
        logger.info(f"Authenticating via profile: {self.profile_name}")
        
        session = boto3.Session(
            profile_name=self.profile_name,
            region_name=self.region_name
        )
        
        # Validate credentials
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"✅ Authenticated as: {identity['Arn']}")
        
        return session
    
    def _authenticate_via_env(self) -> boto3.Session:
        """Authenticate using environment variables."""
        logger.info("Authenticating via environment variables...")
        
        # Check for required environment variables
        if not all([
            os.getenv('AWS_ACCESS_KEY_ID'),
            os.getenv('AWS_SECRET_ACCESS_KEY')
        ]):
            raise ValueError(
                "AWS credentials not found. Please configure AWS SSO or set environment variables."
            )
        
        session = boto3.Session(region_name=self.region_name)
        
        # Validate credentials
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"✅ Authenticated as: {identity['Arn']}")
        
        return session
    
    def _initiate_sso_login(self):
        """Initiate AWS SSO login flow."""
        try:
            logger.info("Opening browser for SSO login...")
            
            cmd = ['aws', 'sso', 'login', '--profile', self.profile_name]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                raise Exception(f"SSO login failed: {result.stderr}")
            
            logger.info("✅ SSO login completed")
            
        except subprocess.TimeoutExpired:
            raise Exception("SSO login timed out. Please try again.")
        except FileNotFoundError:
            raise Exception("AWS CLI not found. Please install AWS CLI v2.")
    
    def _is_sso_configured(self) -> bool:
        """Check if AWS SSO is configured."""
        try:
            config_path = Path.home() / '.aws' / 'config'
            if not config_path.exists():
                return False
            
            config = configparser.ConfigParser()
            config.read(config_path)
            
            section = f'profile {self.profile_name}' if self.profile_name != 'default' else 'default'
            
            if section in config and 'sso_start_url' in config[section]:
                logger.debug(f"SSO configured for profile: {self.profile_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking SSO configuration: {e}")
            return False
    
    def _is_profile_configured(self) -> bool:
        """Check if AWS profile is configured."""
        try:
            credentials_path = Path.home() / '.aws' / 'credentials'
            if not credentials_path.exists():
                return False
            
            config = configparser.ConfigParser()
            config.read(credentials_path)
            
            return self.profile_name in config
            
        except Exception as e:
            logger.debug(f"Error checking profile configuration: {e}")
            return False
    
    def _are_credentials_valid(self) -> bool:
        """Check if current credentials are still valid."""
        if not self._session:
            return False
        
        try:
            sts = self._session.client('sts')
            sts.get_caller_identity()
            return True
        except Exception:
            logger.debug("Cached credentials are no longer valid")
            return False
    
    def get_client(self, service_name: str, **kwargs):
        """
        Get an authenticated boto3 client.
        
        Args:
            service_name: AWS service name (e.g., 's3', 'secretsmanager')
            **kwargs: Additional arguments for client creation
            
        Returns:
            Authenticated boto3 client
        """
        session = self.get_session()
        return session.client(service_name, **kwargs)
    
    def get_credentials(self) -> Dict[str, str]:
        """
        Get AWS credentials as a dictionary.
        
        Returns:
            Dictionary with AWS credentials
        """
        session = self.get_session()
        credentials = session.get_credentials()
        
        return {
            'aws_access_key_id': credentials.access_key,
            'aws_secret_access_key': credentials.secret_key,
            'aws_session_token': credentials.token,
            'region': self.region_name
        }
    
    def assume_role(self, role_arn: str, session_name: Optional[str] = None) -> boto3.Session:
        """
        Assume an AWS IAM role.
        
        Args:
            role_arn: ARN of the role to assume
            session_name: Optional session name
            
        Returns:
            New boto3.Session with assumed role credentials
        """
        session = self.get_session()
        sts = session.client('sts')
        
        session_name = session_name or f"okta-session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        logger.info(f"Assuming role: {role_arn}")
        
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName=session_name,
            DurationSeconds=3600  # 1 hour
        )
        
        credentials = response['Credentials']
        
        # Create new session with assumed role credentials
        assumed_session = boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name=self.region_name
        )
        
        logger.info("✅ Role assumed successfully")
        
        return assumed_session


def setup_okta_profile(
    profile_name: str,
    sso_start_url: str,
    sso_region: str,
    account_id: str,
    role_name: str
):
    """
    Helper function to set up AWS SSO profile for Okta.
    
    Args:
        profile_name: Profile name (e.g., 'jumia-sox-prod')
        sso_start_url: Okta SSO URL
        sso_region: AWS region for SSO
        account_id: AWS account ID
        role_name: IAM role name
    """
    config_path = Path.home() / '.aws' / 'config'
    config_path.parent.mkdir(exist_ok=True)
    
    config = configparser.ConfigParser()
    if config_path.exists():
        config.read(config_path)
    
    section = f'profile {profile_name}'
    if section not in config:
        config[section] = {}
    
    config[section]['sso_start_url'] = sso_start_url
    config[section]['sso_region'] = sso_region
    config[section]['sso_account_id'] = account_id
    config[section]['sso_role_name'] = role_name
    config[section]['region'] = sso_region
    config[section]['output'] = 'json'
    
    with open(config_path, 'w') as f:
        config.write(f)
    
    logger.info(f"✅ AWS SSO profile '{profile_name}' configured successfully")
    print(f"\n✅ Profile '{profile_name}' created successfully!")
    print(f"\nTo login, run:")
    print(f"  aws sso login --profile {profile_name}")
