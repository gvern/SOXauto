"""
Evidence Package

SOX-compliant evidence generation and management for IPE extractions.
"""

from src.core.evidence.manager import (
    DigitalEvidenceManager,
    IPEEvidenceGenerator,
    EvidenceValidator,
)

__all__ = [
    'DigitalEvidenceManager',
    'IPEEvidenceGenerator',
    'EvidenceValidator',
]
