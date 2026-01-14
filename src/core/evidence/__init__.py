"""
Evidence Package

SOX-compliant evidence generation and management for IPE extractions.
"""

from src.core.evidence.manager import (
    DigitalEvidenceManager,
    IPEEvidenceGenerator,
    EvidenceValidator,
)
from src.core.evidence.evidence_locator import (
    get_latest_evidence_zip,
    find_evidence_packages,
)

__all__ = [
    'DigitalEvidenceManager',
    'IPEEvidenceGenerator',
    'EvidenceValidator',
    'get_latest_evidence_zip',
    'find_evidence_packages',
]
