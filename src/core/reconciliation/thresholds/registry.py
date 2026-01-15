"""
Threshold Registry for SOXauto Threshold Catalog System.

This module handles loading, caching, and validating threshold contracts from YAML files.
It provides SHA256 hashing for evidence integrity and supports version pinning.

Key Functions:
    - load_contract: Load and validate a threshold contract from YAML
    - get_contract_hash: Calculate SHA256 hash of contract file
    - get_contract: Get contract with caching (preferred method)
"""

import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

from .models import (
    ThresholdContract,
    ThresholdRule,
    ThresholdScope,
    ThresholdType,
)

logger = logging.getLogger(__name__)


def get_contracts_dir() -> Path:
    """
    Get the path to the contracts directory.
    
    Returns:
        Path to contracts directory
    """
    # Get the directory containing this file
    this_file = Path(__file__).resolve()
    contracts_dir = this_file.parent / "contracts"
    
    if not contracts_dir.exists():
        raise FileNotFoundError(f"Contracts directory not found: {contracts_dir}")
    
    return contracts_dir


def get_contract_hash(contract_path: Path) -> str:
    """
    Calculate SHA256 hash of a contract file for evidence integrity.
    
    Args:
        contract_path: Path to the contract YAML file
    
    Returns:
        SHA256 hash as hexadecimal string
    """
    sha256_hash = hashlib.sha256()
    
    with open(contract_path, "rb") as f:
        # Read in chunks for memory efficiency
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def load_contract(country_code: str, version: Optional[int] = None) -> tuple[ThresholdContract, str]:
    """
    Load a threshold contract from YAML file.
    
    Supports version pinning via environment variables:
    - THRESHOLD_VERSION_<COUNTRY>: Pin specific country version (e.g., THRESHOLD_VERSION_EG=1)
    - THRESHOLD_VERSION_DEFAULT: Pin default version
    
    Args:
        country_code: Country code (e.g., "EG", "NG", "DEFAULT")
        version: Optional version number to load. If None, uses environment
                variable or defaults to version 1.
    
    Returns:
        Tuple of (ThresholdContract, contract_hash)
    
    Raises:
        FileNotFoundError: If contract file not found
        ValueError: If contract YAML is invalid
    """
    # Determine version to load
    if version is None:
        # Check environment variable for version pinning
        env_var = f"THRESHOLD_VERSION_{country_code.upper()}"
        env_version = os.environ.get(env_var)
        if env_version:
            try:
                version = int(env_version)
                logger.info(f"Using pinned version {version} for {country_code} from {env_var}")
            except ValueError:
                logger.warning(f"Invalid version in {env_var}={env_version}, using version 1")
                version = 1
        else:
            version = 1
    
    # Construct contract file path
    contracts_dir = get_contracts_dir()
    contract_file = contracts_dir / f"{country_code}.yaml"
    
    if not contract_file.exists():
        raise FileNotFoundError(
            f"Contract file not found for {country_code}: {contract_file}"
        )
    
    # Calculate hash before loading
    contract_hash = get_contract_hash(contract_file)
    
    # Load YAML
    try:
        with open(contract_file, "r") as f:
            data = yaml.safe_load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse YAML from {contract_file}: {e}")
    
    # Validate required fields
    required_fields = ["version", "effective_date", "description", "country_code", "rules"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"Missing required fields in {contract_file}: {missing_fields}")
    
    # Validate version matches
    file_version = data["version"]
    if file_version != version:
        logger.warning(
            f"Contract file {contract_file} has version {file_version}, "
            f"but version {version} was requested. Using file version."
        )
    
    # Parse rules
    rules = []
    for rule_data in data["rules"]:
        # Validate required rule fields
        required_rule_fields = ["threshold_type", "value_usd", "description"]
        missing_rule_fields = [f for f in required_rule_fields if f not in rule_data]
        if missing_rule_fields:
            raise ValueError(
                f"Missing required fields in rule: {missing_rule_fields}. "
                f"Rule data: {rule_data}"
            )
        
        # Parse scope (optional)
        scope_data = rule_data.get("scope", {})
        if scope_data is None:
            scope_data = {}
        
        scope = ThresholdScope(
            gl_accounts=scope_data.get("gl_accounts"),
            categories=scope_data.get("categories"),
            voucher_types=scope_data.get("voucher_types"),
        )
        
        # Create rule
        rule = ThresholdRule(
            threshold_type=ThresholdType(rule_data["threshold_type"]),
            value_usd=float(rule_data["value_usd"]),
            description=rule_data["description"],
            scope=scope,
        )
        rules.append(rule)
    
    # Create contract
    contract = ThresholdContract(
        version=file_version,
        effective_date=data["effective_date"],
        description=data["description"],
        country_code=data["country_code"],
        rules=rules,
    )
    
    logger.info(
        f"Loaded threshold contract: {country_code} v{contract.version} "
        f"({len(contract.rules)} rules, hash={contract_hash[:8]}...)"
    )
    
    return contract, contract_hash


@lru_cache(maxsize=32)
def get_contract(country_code: str, version: Optional[int] = None) -> tuple[ThresholdContract, str]:
    """
    Get a threshold contract with caching.
    
    This is the preferred way to load contracts as it uses LRU caching
    to avoid repeated file I/O and parsing.
    
    Args:
        country_code: Country code (e.g., "EG", "NG", "DEFAULT")
        version: Optional version number to load
    
    Returns:
        Tuple of (ThresholdContract, contract_hash)
    
    Raises:
        FileNotFoundError: If contract file not found
        ValueError: If contract YAML is invalid
    """
    return load_contract(country_code, version)


def get_available_countries() -> list[str]:
    """
    Get list of available country codes with contracts.
    
    Returns:
        List of country codes (excluding "DEFAULT")
    """
    contracts_dir = get_contracts_dir()
    countries = []
    
    for file in contracts_dir.glob("*.yaml"):
        country_code = file.stem
        if country_code != "DEFAULT":
            countries.append(country_code)
    
    return sorted(countries)


def clear_cache():
    """Clear the contract cache. Useful for testing or reloading contracts."""
    get_contract.cache_clear()
    logger.info("Cleared threshold contract cache")


__all__ = [
    "load_contract",
    "get_contract",
    "get_contract_hash",
    "get_available_countries",
    "clear_cache",
]
