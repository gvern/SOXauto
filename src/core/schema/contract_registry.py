"""
Schema Contract Registry

Loads and manages schema contracts from YAML files with caching and version management.
Supports multiple contract versions for audit reproducibility while enforcing single
active version at runtime.
"""

import hashlib
import logging
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from src.core.schema.models import (
    CoercionRules,
    FillPolicy,
    SchemaContract,
    SchemaField,
    SemanticTag,
)

logger = logging.getLogger(__name__)


class ContractRegistry:
    """
    Central registry for schema contracts.
    
    Loads contracts from YAML files, caches them, and manages version selection.
    """
    
    def __init__(self, contracts_dir: Optional[Path] = None):
        """
        Initialize the contract registry.
        
        Args:
            contracts_dir: Path to directory containing contract YAML files.
                          Defaults to src/core/schema/contracts/
        """
        if contracts_dir is None:
            # Default to contracts/ subdirectory relative to this file
            contracts_dir = Path(__file__).parent / "contracts"
        
        self.contracts_dir = Path(contracts_dir)
        self._contracts_cache: Dict[str, Dict[int, SchemaContract]] = {}
        
        if not self.contracts_dir.exists():
            logger.warning(f"Contracts directory not found: {self.contracts_dir}")
    
    def _compute_contract_hash(self, contract_dict: dict) -> str:
        """
        Compute SHA-256 hash of contract content for traceability.
        
        Args:
            contract_dict: Raw contract dictionary from YAML
        
        Returns:
            Hexadecimal SHA-256 hash string
        """
        # Sort keys for deterministic hashing
        import json
        contract_json = json.dumps(contract_dict, sort_keys=True)
        return hashlib.sha256(contract_json.encode()).hexdigest()
    
    def _validate_no_alias_collisions(
        self,
        fields: List[SchemaField],
        filepath: Path
    ) -> None:
        """
        Validate that no alias appears in multiple field definitions.
        
        Rules:
        1. An alias can only map to ONE canonical field
        2. A field CAN list its own canonical name in aliases (self-reference OK)
        3. A field CANNOT use another field's canonical name as an alias
        
        Args:
            fields: List of parsed SchemaField objects
            filepath: Path to contract file (for error messages)
        
        Raises:
            ValueError: If alias collisions are detected
        """
        # Build map of all canonical names and aliases to their owning field
        name_to_field: Dict[str, str] = {}
        collisions = []
        
        # First pass: register all canonical names
        for field in fields:
            name_to_field[field.name] = field.name
        
        # Second pass: check aliases don't conflict
        for field in fields:
            for alias in field.aliases:
                # Skip if alias equals THIS field's canonical name (self-reference OK)
                if alias == field.name:
                    continue
                
                # Check if this alias conflicts with any existing mapping
                if alias in name_to_field:
                    collisions.append(
                        f"Alias '{alias}' in field '{field.name}' conflicts with "
                        f"field '{name_to_field[alias]}'"
                    )
                else:
                    name_to_field[alias] = field.name
        
        if collisions:
            raise ValueError(
                f"Alias collisions detected in {filepath}:\n" +
                "\n".join(collisions) +
                "\n\nEach alias must map to exactly one canonical field."
            )
    
    def _parse_field(self, field_dict: dict) -> SchemaField:
        """
        Parse a field definition from YAML dict to SchemaField object.
        
        Args:
            field_dict: Field definition from YAML
        
        Returns:
            SchemaField instance
        """
        # Parse semantic tag
        semantic_tag = SemanticTag.OTHER
        if "semantic_tag" in field_dict:
            try:
                semantic_tag = SemanticTag(field_dict["semantic_tag"])
            except ValueError:
                logger.warning(f"Unknown semantic tag: {field_dict['semantic_tag']}, using OTHER")
        
        # Parse fill policy
        fill_policy = FillPolicy.KEEP_NAN
        if "fill_policy" in field_dict:
            try:
                fill_policy = FillPolicy(field_dict["fill_policy"])
            except ValueError:
                logger.warning(f"Unknown fill policy: {field_dict['fill_policy']}, using KEEP_NAN")
        
        # Parse coercion rules
        coercion_rules = None
        if "coercion_rules" in field_dict:
            cr = field_dict["coercion_rules"]
            coercion_rules = CoercionRules(
                strip_whitespace=cr.get("strip_whitespace", True),
                remove_commas=cr.get("remove_commas", True),
                remove_spaces=cr.get("remove_spaces", True),
                remove_currency_symbols=cr.get("remove_currency_symbols", True),
                date_formats=cr.get("date_formats", [])
            )
        
        return SchemaField(
            name=field_dict["name"],
            required=field_dict.get("required", False),
            aliases=field_dict.get("aliases", []),
            dtype=field_dict.get("dtype", "string"),
            semantic_tag=semantic_tag,
            coercion_rules=coercion_rules,
            fill_policy=fill_policy,
            description=field_dict.get("description"),
            reconciliation_critical=field_dict.get("reconciliation_critical", False),
            validation_rules=field_dict.get("validation_rules", {})
        )
    
    def _load_contract_from_file(self, filepath: Path) -> SchemaContract:
        """
        Load a single contract from YAML file.
        
        Args:
            filepath: Path to YAML contract file
        
        Returns:
            SchemaContract instance
        
        Raises:
            ValueError: If contract is malformed
        """
        logger.debug(f"Loading contract from {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            contract_dict = yaml.safe_load(f)
        
        # Validate required fields
        if "dataset_id" not in contract_dict:
            raise ValueError(f"Contract missing 'dataset_id': {filepath}")
        if "version" not in contract_dict:
            raise ValueError(f"Contract missing 'version': {filepath}")
        if "fields" not in contract_dict:
            raise ValueError(f"Contract missing 'fields': {filepath}")
        
        # Parse fields
        fields = [self._parse_field(f) for f in contract_dict["fields"]]
        
        # Validate no alias collisions (same alias in multiple fields)
        self._validate_no_alias_collisions(fields, filepath)
        
        # Compute contract hash
        contract_hash = self._compute_contract_hash(contract_dict)
        
        # Build SchemaContract
        contract = SchemaContract(
            dataset_id=contract_dict["dataset_id"],
            version=int(contract_dict["version"]),
            fields=fields,
            primary_keys=contract_dict.get("primary_keys", []),
            description=contract_dict.get("description"),
            source_system=contract_dict.get("source_system"),
            created_at=datetime.now(),  # Could parse from YAML if present
            deprecated=contract_dict.get("deprecated", False),
            contract_hash=contract_hash
        )
        
        logger.info(
            f"Loaded contract: {contract.dataset_id} v{contract.version} "
            f"({len(contract.fields)} fields, hash={contract_hash[:8]}...)"
        )
        
        return contract
    
    def discover_contracts(self) -> Dict[str, List[int]]:
        """
        Discover all available contracts in the contracts directory.
        
        Returns:
            Dictionary mapping dataset_id to list of available versions
        """
        discovered: Dict[str, List[int]] = {}
        
        if not self.contracts_dir.exists():
            logger.warning(f"Contracts directory does not exist: {self.contracts_dir}")
            return discovered
        
        # Find all YAML files
        for filepath in self.contracts_dir.glob("*.yaml"):
            try:
                contract = self._load_contract_from_file(filepath)
                if contract.dataset_id not in discovered:
                    discovered[contract.dataset_id] = []
                discovered[contract.dataset_id].append(contract.version)
                
                # Cache it
                if contract.dataset_id not in self._contracts_cache:
                    self._contracts_cache[contract.dataset_id] = {}
                self._contracts_cache[contract.dataset_id][contract.version] = contract
                
            except Exception as e:
                logger.error(f"Failed to load contract from {filepath}: {e}")
        
        return discovered
    
    def load_contract(
        self,
        dataset_id: str,
        version: Optional[int] = None
    ) -> SchemaContract:
        """
        Load a specific contract version.
        
        Args:
            dataset_id: Dataset identifier (e.g., "IPE_07")
            version: Specific version to load (None = latest)
        
        Returns:
            SchemaContract instance
        
        Raises:
            ValueError: If contract not found
        """
        # Ensure contracts are discovered
        if not self._contracts_cache:
            self.discover_contracts()
        
        if dataset_id not in self._contracts_cache:
            raise ValueError(f"No contracts found for dataset: {dataset_id}")
        
        versions = self._contracts_cache[dataset_id]
        
        if version is None:
            # Get latest version
            version = max(versions.keys())
            logger.debug(f"Using latest version for {dataset_id}: v{version}")
        
        if version not in versions:
            available = sorted(versions.keys())
            raise ValueError(
                f"Contract version {version} not found for {dataset_id}. "
                f"Available versions: {available}"
            )
        
        return versions[version]
    
    def get_active_contract(self, dataset_id: str) -> SchemaContract:
        """
        Get the active contract for a dataset based on configuration.
        
        Checks for environment variable SCHEMA_VERSION_{dataset_id} to pin
        a specific version, otherwise returns latest.
        
        Args:
            dataset_id: Dataset identifier
        
        Returns:
            Active SchemaContract instance
        
        Example:
            Set SCHEMA_VERSION_IPE_07=1 to pin IPE_07 to version 1
        """
        # Check for version pinning via environment variable
        env_var = f"SCHEMA_VERSION_{dataset_id}"
        pinned_version = os.environ.get(env_var)
        
        if pinned_version:
            try:
                version = int(pinned_version)
                logger.info(f"Using pinned version for {dataset_id}: v{version} (from {env_var})")
                return self.load_contract(dataset_id, version=version)
            except ValueError:
                logger.warning(
                    f"Invalid version in {env_var}={pinned_version}, using latest"
                )
        
        # Use latest version
        return self.load_contract(dataset_id, version=None)
    
    def list_contracts(self) -> Dict[str, Dict[int, str]]:
        """
        List all available contracts with metadata.
        
        Returns:
            Dictionary mapping dataset_id -> version -> description
        """
        if not self._contracts_cache:
            self.discover_contracts()
        
        result = {}
        for dataset_id, versions in self._contracts_cache.items():
            result[dataset_id] = {}
            for version, contract in versions.items():
                desc = contract.description or "No description"
                result[dataset_id][version] = desc
        
        return result


# Global registry instance with caching
_global_registry: Optional[ContractRegistry] = None


@lru_cache(maxsize=128)
def load_contract(dataset_id: str, version: Optional[int] = None) -> SchemaContract:
    """
    Load a schema contract with caching.
    
    This is the primary API for loading contracts. Results are cached
    to avoid repeated YAML parsing.
    
    Args:
        dataset_id: Dataset identifier (e.g., "IPE_07")
        version: Specific version (None = latest)
    
    Returns:
        SchemaContract instance
    
    Example:
        >>> contract = load_contract("IPE_07")
        >>> contract = load_contract("IPE_07", version=1)
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ContractRegistry()
    
    return _global_registry.load_contract(dataset_id, version)


def get_active_contract(dataset_id: str) -> SchemaContract:
    """
    Get the active contract for a dataset.
    
    Respects SCHEMA_VERSION_{dataset_id} environment variable for version pinning.
    
    Args:
        dataset_id: Dataset identifier
    
    Returns:
        Active SchemaContract instance
    
    Example:
        >>> contract = get_active_contract("IPE_07")
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ContractRegistry()
    
    return _global_registry.get_active_contract(dataset_id)


def list_available_contracts() -> Dict[str, Dict[int, str]]:
    """
    List all available contracts.
    
    Returns:
        Dictionary mapping dataset_id -> version -> description
    """
    global _global_registry
    
    if _global_registry is None:
        _global_registry = ContractRegistry()
    
    return _global_registry.list_contracts()


def clear_cache():
    """Clear the contract cache (useful for testing)."""
    load_contract.cache_clear()
