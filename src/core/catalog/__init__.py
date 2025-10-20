"""
C-PG-1 Catalog Package

Unified source of truth for IPE/CR definitions and backend configurations.
"""

from src.core.catalog.pg1_catalog import (
    CatalogItem,
    CatalogSource,
    CPG1_CATALOG,
    list_items,
    get_item_by_id,
    to_dicts,
    list_athena_ipes,
    get_athena_config,
)

__all__ = [
    'CatalogItem',
    'CatalogSource',
    'CPG1_CATALOG',
    'list_items',
    'get_item_by_id',
    'to_dicts',
    'list_athena_ipes',
    'get_athena_config',
]
