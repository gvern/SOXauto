"""
Unified IPE/CR catalog for Control C-PG-1.

Purpose
- Central, backend-agnostic registry of all C-PG-1 inputs (IPEs, CRs, and supporting docs)
- To be referenced by SQL Server and Athena configurations/runners
- Designed to attach descriptive Excel files later in IPE_FILES/

Notes
- This file does NOT contain SQL. It only captures metadata and mapping hints.
- Keep IDs stable: use e.g. IPE_07, IPE_08, CR_04, CR_05, and a DOC_* prefix for non-IPE working files.
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any


@dataclass
class CatalogSource:
    """Represents a single upstream source (table/view/file)."""
    type: str  # e.g., "SQLServer", "Athena", "Excel", "GoogleDrive"
    location: str  # e.g., "[db].[schema].[table]" or file/url hint
    system: Optional[str] = None  # e.g., NAV, OMS, BOB, Seller Center
    domain: Optional[str] = None  # e.g., NAVBI, FinRec


@dataclass
class CatalogItem:
    """Catalog entry describing an IPE/CR/DOC used by C-PG-1."""
    item_id: str  # e.g., IPE_07, CR_04, DOC_PG_BALANCES
    item_type: str  # one of: "IPE", "CR", "DOC"
    control: str  # e.g., "C-PG-1"
    title: str
    change_status: str  # e.g., "No changes", "Has changes", "New IPE"
    last_updated: str  # ISO date "YYYY-MM-DD"
    output_type: Optional[str] = None  # e.g., "Custom Report", "Query", "Excel file"
    tool: Optional[str] = None  # e.g., PowerBI, PowerPivot, Excel
    third_party: Optional[bool] = None
    status: Optional[str] = None  # e.g., Completed
    baseline_required: Optional[bool] = None
    cross_reference: Optional[str] = None  # e.g., "I.OMS-NAV", "I.SC-NAV"
    notes: Optional[str] = None
    evidence_ref: Optional[str] = None  # usually same as item_id for IPE/CR
    descriptor_excel: Optional[str] = None  # path placeholder under IPE_FILES/
    sources: Optional[List[CatalogSource]] = None
    # Optional backend-specific configs (start with Athena)
    athena_database: Optional[str] = None
    athena_query: Optional[str] = None
    athena_validation: Optional[Dict[str, Any]] = None


def _src_sql(location: str, system: Optional[str] = None, domain: Optional[str] = None) -> CatalogSource:
    return CatalogSource(type="SQLServer", location=location, system=system, domain=domain)


def _src_excel(location: str) -> CatalogSource:
    return CatalogSource(type="Excel", location=location)


def _src_gdrive(location: str) -> CatalogSource:
    return CatalogSource(type="GoogleDrive", location=location)


# Catalog entries populated from user's provided list
CPG1_CATALOG: List[CatalogItem] = [
    CatalogItem(
        item_id="DOC_PG_BALANCES",
        item_type="DOC",
        control="C-PG-1",
        title="Consolidated PG balances working file",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Excel file",
        tool="Excel",
        third_party=False,
        status=None,
        baseline_required=None,
        cross_reference=None,
        notes=None,
        evidence_ref=None,
        descriptor_excel=None,
        sources=[
            _src_excel("Excel file"),
            _src_gdrive("Google Drive"),
        ],
    ),
    CatalogItem(
        item_id="IPE_07",
        item_type="IPE",
        control="C-PG-1",
        title="Customer balances - Monthly balances at date (Ageing details)",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "Found in file '2. All Countries June-25 - IBSAR - Customer Accounts.xlsx', "
            "GLs = 13003, 13004, 13009. "
            "Baseline: IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx"
        ),
        evidence_ref="IPE_07",
        descriptor_excel="IPE_FILES/IPE_07a__IPE Baseline__Detailed customer ledger entries.xlsx",
        sources=[
            _src_sql("[AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]", system="NAV", domain="NAVBI"),
            _src_sql("[AIG_Nav_DW].[dbo].[Customer Ledger Entries]", system="NAV", domain="NAVBI"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="CR_05",
        item_type="CR",
        control="C-PG-1",
        title="FX rates",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "Multiple baseline files: CR_05_test.xlsx, "
            "CR_05a__IPE Baseline__FA table - FX rates.xlsx, "
            "CR_05b__IPE Baseline__Daily FX rates.xlsx. "
            "May require two separate Athena tables or one combined view."
        ),
        evidence_ref="CR_05",
        descriptor_excel="IPE_FILES/CR_05a__IPE Baseline__FA table - FX rates.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]", system="NAV", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_11",
        item_type="IPE",
        control="C-PG-1",
        title="Marketplace accrued revenues",
        change_status="Has changes",
        last_updated="2025-08-19",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference="I.SC-NAV",
        notes=(
            "GL = 18304. "
            "Baseline: IPE_11__IPE Baseline__Marketplace accrued revenues.xlsx"
        ),
        evidence_ref="IPE_11",
        descriptor_excel="IPE_FILES/IPE_11__IPE Baseline__Marketplace accrued revenues.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SC_TRANSCATIONS]", system="Seller Center", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SC_ACCOUNTSTATEMENTS]", system="Seller Center", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING]", system="NAV", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_10",
        item_type="IPE",
        control="C-PG-1",
        title="Customer prepayments TV (TV PBI report)",
        change_status="New IPE",
        last_updated="2025-10-01",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference="I.OMS-NAV",
        notes=(
            "Found in file '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx', GL=18350. "
            "Uses RPT_SOI filtered for prepayments. "
            "Baseline: IPE_10__IPE Baseline__Customer prepayments TV.xlsx"
        ),
        evidence_ref="IPE_10",
        descriptor_excel="IPE_FILES/IPE_10__IPE Baseline__Customer prepayments TV.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_08",
        item_type="IPE",
        control="C-PG-1",
        title="TV - Voucher liabilities",
        change_status="No changes",
        last_updated="2025-09-15",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "File '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx / Tab 18412' "
            "-> All Countries - Jun.25 - Voucher TV Extract.xlsx. GL = 18412. "
            "Test data: IPE_08_test.xlsx"
        ),
        evidence_ref="IPE_08",
        descriptor_excel="IPE_FILES/IPE_08_test.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]", system="BOB", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_31",
        item_type="IPE",
        control="C-PG-1",
        title="PG detailed TV extraction (from Collection Accounts TV support file)",
        change_status="No changes",
        last_updated="2025-10-06",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "Found in file 'Jun25 - ECL - CPMT detailed open balances - 08.07.2025.xlsx', "
            "support for the Collection accounts TV. GL = 13001, 13002. "
            "Complex 7-table join. Baseline: IPE_31.xlsx"
        ),
        evidence_ref="IPE_31",
        descriptor_excel="IPE_FILES/IPE_31.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING]", system="NAV", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_34",
        item_type="IPE",
        control="C-PG-1",
        title="Marketplace refund liability (Page: MPL)",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "File '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx / Tab 18317'. "
            "GL = 18317. Uses RPT_SOI filtered for refunds. "
            "Baseline: IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx"
        ),
        evidence_ref="IPE_34",
        descriptor_excel="IPE_FILES/IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="IPE_12",
        item_type="IPE",
        control="C-PG-1",
        title="TV - Packages delivered not reconciled",
        change_status="New IPE",
        last_updated="2025-10-02",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference="I.OMS-NAV",
        notes=(
            "Found in files: - 2. All Countries June-25 - IBSAR - Customer Accounts.xlsx - GL 13005; "
            "- 4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx - GL 13024. "
            "Uses RPT_SOI filtered for unreconciled packages. "
            "Baseline: IPE_12__IPE Baseline__TV - Packages delivered not reconciled.xlsx"
        ),
        evidence_ref="IPE_12",
        descriptor_excel="IPE_FILES/IPE_12__IPE Baseline__TV - Packages delivered not reconciled.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="CR_04",
        item_type="CR",
        control="C-PG-1",
        title="NAV GL Balances",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "V_Anaplan_BS_View (Anaplan is retired but the view is active and pulls data from NAVBI and FinRec). "
            "CRITICAL: This is the ACTUALS side of the reconciliation - all IPEs reconcile to this. "
            "Test data: CR_04_testing.xlsx"
        ),
        evidence_ref="CR_04",
        descriptor_excel="IPE_FILES/CR_04_testing.xlsx",
        sources=[
            _src_sql(
                "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]",
                system="NAV",
                domain="FinRec",
            ),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    CatalogItem(
        item_id="CR_03",
        item_type="CR",
        control="C-PG-1",
        title="NAV GL Entries",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "Detailed GL transaction entries supporting CR_04 GL Balances. "
            "Test data: CR_03_test.xlsx"
        ),
        evidence_ref="CR_03",
        descriptor_excel="IPE_FILES/CR_03_test.xlsx",
        sources=[
            _src_sql("[AIG_Nav_DW].[dbo].[G_L Entry]", system="NAV", domain="NAVBI"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
    ),
    # =================================================================
    # == 10. IPE-34: Marketplace Refund Liability
    # =================================================================
    CatalogItem(
        id='IPE_34',
        description="Marketplace refund liability (Page: MPL)",
        control="C-PG-1",
        title="Marketplace refund liability (Page: MPL)",
        change_status="No changes",
        last_updated="2025-03-11",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        notes=(
            "File '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx / Tab 18317'. "
            "GL = 18317. Uses RPT_SOI filtered for refunds. "
            "Baseline: IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx"
        ),
        evidence_ref="IPE_34",
        descriptor_excel="IPE_FILES/IPE_34__IPE Baseline__MPL refund liability - Target values.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        # Athena placeholders (to be confirmed)
        athena_database=None,
        athena_query=None,
        athena_validation=None,
        active=False
    ),

    # =================================================================
    # == JIRA TICKETS - AUDIT EXTRACTS
    # =================================================================
    # == DS-3900: GL Actuals (Auditor's View)
    # =================================================================
    CatalogItem(
        id='DS-3900',
        description="GL Actuals Extraction based on Auditor's View from ticket DS-3900",
        source_type='athena',
        owner='Finance',
        complexity='medium',
        recon_impact='critical',
        dependencies=['DS-3899'],
        tags=['gl', 'actuals', 'audit-extract'],
        athena_database='process_central_fin_dwh',
        athena_query="""
-- Placeholder for the SQL query from GL_VIEWS_2025Q3.sql
-- This query needs to be translated from the PDF attachment in Jira ticket DS-3900.
-- It should replicate the exact view used to generate GL data for auditors.
SELECT 1
        """,
        active=True
    ),

    # =================================================================
    # == DS-3899: Revenue Target Values (Auditor's View)
    # =================================================================
    CatalogItem(
        id='DS-3899',
        description="Revenue Target Value Extraction from RPT_SOI based on Auditor's query from ticket DS-3899",
        source_type='athena',
        owner='Finance',
        complexity='high',
        recon_impact='critical',
        dependencies=[],
        tags=['revenue', 'rpt_soi', 'target-values', 'audit-extract'],
        athena_database='process_central_fin_dwh',
        athena_query="""
-- Placeholder for the SQL query from RPT_SOI_Revenue Testing_Q3-2025_query.txt
-- This query needs to be translated from the PDF attachment in Jira ticket DS-3899.
SELECT 1
        """,
        active=True
    ),
]


def list_items(item_type: Optional[str] = None) -> List[CatalogItem]:
    """List all catalog items, optionally filtered by type (IPE|CR|DOC)."""
    if item_type is None:
        return CPG1_CATALOG.copy()
    t = item_type.upper()
    return [it for it in CPG1_CATALOG if it.item_type.upper() == t]


def get_item_by_id(item_id: str) -> Optional[CatalogItem]:
    """Retrieve a catalog item by its ID (returns None if not found)."""
    for it in CPG1_CATALOG:
        if it.item_id == item_id:
            return it
    return None


def to_dicts(items: Optional[List[CatalogItem]] = None) -> List[Dict[str, Any]]:
    """Serialize catalog items to simple dictionaries (useful for APIs)."""
    items = items if items is not None else CPG1_CATALOG
    result: List[Dict[str, Any]] = []
    for it in items:
        d = asdict(it)
        # Serialize nested dataclasses in sources
        if d.get("sources"):
            d["sources"] = [asdict(s) for s in it.sources or []]
        result.append(d)
    return result


# ---- Athena helpers (single source for Athena-based IPE configs) ----

def list_athena_ipes() -> List[str]:
    """Return IPE IDs that have Athena configuration in the catalog."""
    return [it.item_id for it in CPG1_CATALOG if it.athena_database and it.athena_query]


def get_athena_config(ipe_id: str) -> Dict[str, Any]:
    """Return a dict compatible with IPERunnerAthena for the given IPE ID.

    Raises ValueError if not found or not Athena-enabled.
    """
    it = get_item_by_id(ipe_id)
    if not it:
        raise ValueError(f"Unknown IPE: {ipe_id}")
    if not it.athena_database or not it.athena_query:
        raise ValueError(f"IPE {ipe_id} has no Athena configuration in the catalog")
    return {
        'id': it.item_id,
        'description': it.title,
        'athena_database': it.athena_database,
        'query': it.athena_query,
        'validation': it.athena_validation or {},
    }


if __name__ == "__main__":
    # Quick manual check
    from pprint import pprint
    print("C-PG-1 Catalog (summary):")
    for it in CPG1_CATALOG:
        print(f"- {it.item_id:7s} | {it.item_type:3s} | {it.title}")
    print("\nAs dicts (first 2):")
    pprint(to_dicts(CPG1_CATALOG[:2]))
