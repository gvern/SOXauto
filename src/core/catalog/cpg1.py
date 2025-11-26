"""
Unified IPE/CR catalog for Control C-PG-1.

Purpose
- Central, backend-agnostic registry of all C-PG-1 inputs (IPEs, CRs, and supporting docs)
- To be referenced by SQL Server-based runners and tooling
- Designed to attach descriptive Excel files later in IPE_FILES/

Notes
- This file now captures metadata and (when applicable) the canonical SQL Server query used to generate the IPE/CR.
- Keep IDs stable: use e.g. IPE_07, IPE_08, CR_04, CR_05, and a DOC_* prefix for non-IPE working files.
"""

from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from src.core.quality_checker import QualityRule

from src.core.quality_checker import RowCountCheck, ColumnExistsCheck, NoNullsCheck


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
    # SQL Server support (preferred going forward)
    sql_query: Optional[str] = None
    description: Optional[str] = None
    # Data quality rules for automated validation
    quality_rules: List['QualityRule'] = field(default_factory=list)


def _src_sql(location: str, system: Optional[str] = None, domain: Optional[str] = None) -> CatalogSource:
    return CatalogSource(type="SQLServer", location=location, system=system, domain=domain)


def _src_excel(location: str) -> CatalogSource:
    return CatalogSource(type="Excel", location=location)


def _src_gdrive(location: str) -> CatalogSource:
    return CatalogSource(type="GoogleDrive", location=location)


def _load_sql(item_id: str) -> str:
    """Load SQL query from external .sql file in queries/ subdirectory."""
    queries_dir = os.path.join(os.path.dirname(__file__), "queries")
    sql_file = os.path.join(queries_dir, f"{item_id}.sql")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"SQL query file not found for item '{item_id}'. "
            f"Expected file: {sql_file}"
        )
    except IOError as e:
        raise IOError(
            f"Error reading SQL query file for item '{item_id}': {e}"
        )


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
        last_updated="2025-10-22",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""This is a pre-defined query, used to pull the detailed customer ledger entries, as of the period when the control (for instance C-FSC-43) is being executed.""",
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
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Busline]", system="NAV", domain="FinRec"),
            _src_sql("[AAN_Nav_Jumia_Reconciliation].[dbo].[Customers]", system="NAV", domain="NAVBI"),
        ],
        sql_query=_load_sql("IPE_07"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("Customer No_"),
            ColumnExistsCheck("Customer Posting Group"),
        ],
    ),
    CatalogItem(
        item_id="CR_05",
        item_type="CR",
        control="C-PG-1",
        title="FX rates",
        change_status="No changes",
        last_updated="2025-10-22",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""This is a pre-defined query, used to pull the FX amounts to be used in the FX reasonableness test of prepayments, as of the period when the control (for instance C-FSC-43) is being executed.""",
        notes=(
            "Correct baseline from '1. All Countries May-25 - IBSAR - Consolidation.xlsx'. "
            "3-table join: Dim_Company, RPT_FX_RATES, Dim_Country. "
            "Includes CASE WHEN logic for USA and Germany special FX rate handling."
        ),
        evidence_ref="CR_05",
        descriptor_excel=None,
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country]", system="NAV", domain="FinRec"),
        ],
        sql_query=_load_sql("CR_05"),
    ),
    CatalogItem(
        item_id="CR_05a",
        item_type="CR",
        control="C-FA-12",
        title="FA table - FX rates",
        change_status="No changes",
        last_updated="2025-10-22",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""This is a pre-defined query, used to pull the FX amounts to be used in the country FA reconciliations, as of the period when the control (for instance C-FA-12) is being executed.""",
        notes=("From CR_05a__IPE Baseline__FA table - FX rates.xlsx"),
        evidence_ref="CR_05a",
        descriptor_excel="IPE_FILES/CR_05a__IPE Baseline__FA table - FX rates.xlsx",
        sources=[
            _src_sql("[D365BC14_DZ].[dbo].[Jade DZ$Currency Exchange Rate]", system="NAV", domain="FinRec"),
        ],
        sql_query=_load_sql("CR_05a"),
        
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
        
    ),
    CatalogItem(
        item_id="IPE_10",
        item_type="IPE",
        control="C-PG-1",
        title="Customer prepayments TV (TV PBI report)",
        change_status="New IPE",
        last_updated="2025-10-22",
        output_type="Custom Report",
        tool="PowerBI",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference="I.OMS-NAV",
        description="""Report Title or Identifier:
TV - Customer Prepayments Report As used in Control PG-1 Control - "4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx".

During the financial closing week, accounting excellence manager compares the expected balance figures (target values) from source systems (OMS) against NAV accounts balances with the following nature:
- customer AR
- collections AR
- vouchers liability
- prepayments liability
- marketplace refund liability
Variance (by account balance) are investigated and bridges & adjustments identified & explained.
The control output is reviewed by the accounting excellence team which makes sure documentation is sufficient, accurate and that all combined there are no unjustified variances higher than established threshold.
On a monthly basis the group head of shared accounting formalizes the outcome of the control by email including any journals posted and reviewed""",
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
        sql_query=_load_sql("IPE_10"),
        
    ),
    CatalogItem(
        item_id="IPE_08",
        item_type="IPE",
        control="C-PG-1",
        title="TV - Voucher liabilities",
        change_status="No changes",
        last_updated="2025-11-26",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""This query extracts voucher issuance data with row-level order dates from RPT_SOI. 
It includes voucher details from V_STORECREDITVOUCHER_CLOSING joined with RPT_SOI to obtain critical 
timing information: Order_Creation_Date, Order_Delivery_Date, Order_Cancellation_Date, and Order_Item_Status.
These dates enable timing difference bridge analysis to identify vouchers used in Month N but finalized in Month N+1.
This provides the complete voucher liability picture for reconciliation purposes.""",
        notes=(
            "File '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx / Tab 18412' "
            "-> All Countries - Jun.25 - Voucher TV Extract.xlsx. GL = 18412. "
            "Test data: IPE_08_test.xlsx. "
            "Updated 2025-11-26 to include row-level order dates for Timing Bridge analysis."
        ),
        evidence_ref="IPE_08",
        descriptor_excel="IPE_FILES/IPE_08_test.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]", system="BOB", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        sql_query=_load_sql("IPE_08"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("remaining_amount"),
            ColumnExistsCheck("id"),
            ColumnExistsCheck("Order_Creation_Date"),
            ColumnExistsCheck("Order_Delivery_Date"),
        ],
    ),
    # =================================================================
    # == DOC_VOUCHER_USAGE: Data for Timing Difference Bridge
    # =================================================================
    # Baseline: "Usage May 2025 Query" from IPE_08 documentation
    # Purpose: Provides the "Usage" side for the Task 1 Timing Diff bridge.
    # =================================================================
    CatalogItem(
        item_id="DOC_VOUCHER_USAGE",
        item_type="DOC",
        control="C-PG-1",
        title="Voucher Usage TV Extract (for Timing Bridge)",
        status="Completed",
        baseline_required=True,
        change_status="New DOC",
        last_updated="2025-11-06",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        cross_reference=None,
        notes=(
            "Baseline: 'Usage May 2025 Query' from IPE_08 documentation (corrected). "
            "This extract provides the Usage side for Task 1 (Timing Difference Bridge). "
            "It queries RPT_SOI with joins to V_STORECREDITVOUCHER_CLOSING and "
            "RPT_TRANSACTIONS_SELLER for enriched voucher usage data."
        ),
        evidence_ref="DOC_VOUCHER_USAGE",
        descriptor_excel=None,
        description="""This query extracts voucher usage data from RPT_SOI for the Timing \
Difference Bridge reconciliation.
It provides the "Usage TV Extract" side that reconciles with the Jdash extract in Task 1.
The query joins with V_STORECREDITVOUCHER_CLOSING to obtain business_use and creation year, \
and with RPT_TRANSACTIONS_SELLER to get transaction numbers.
It aggregates shipping store credits and marketplace/retail store credits by company, \
voucher id, transaction number, voucher type, business use, creation year, and delivery month.""",
        sources=[
            _src_sql(
                "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]",
                system="OMS",
                domain="FinRec",
            ),
            _src_sql(
                "[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]",
                system="OMS",
                domain="FinRec",
            ),
            _src_sql(
                "[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER]",
                system="OMS",
                domain="FinRec",
            ),
        ],
        sql_query=_load_sql("DOC_VOUCHER_USAGE"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("TotalAmountUsed"),
        ],
    ),
    CatalogItem(
        item_id="IPE_31",
        item_type="IPE",
        control="C-PG-1",
        title="PG detailed TV extraction (from Collection Accounts TV support file)",
        change_status="No changes",
        last_updated="2025-10-22",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""IPE for TV - Collection Accounts, PG detailed TV Reconciliation used for the control PG-1 for July - 2025

During the financial closing week, accounting excellence manager compares the expected balance figures (target values) from source systems (OMS) against NAV accounts balances with the following nature:
- customer AR
- collections AR
- vouchers liability
- prepayments liability
- marketplace refund liability
Variance (by account balance) are investigated and bridges & adjustments identified & explained.
The control output is reviewed by the accounting excellence team which makes sure documentation is sufficient, accurate and that all combined there are no unjustified variances higher than established threshold.
On a monthly basis the group head of shared accounting formalizes the outcome of the control by email including any journals posted and reviewed (under FSC-7).""",
        notes=(
            "Found in file 'Jun25 - ECL - CPMT detailed open balances - 08.07.2025.xlsx', "
            "support for the Collection accounts TV. GL = 13001, 13002. "
            "Complex 7-table join. Baseline: IPE_31.xlsx"
        ),
        evidence_ref="IPE_31",
        descriptor_excel="IPE_FILES/IPE_31.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONPARTNERS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_DW].[dbo].[Bank Accounts]", system="NAV", domain="NAVBI"),
            _src_sql("[AIG_Nav_DW].[dbo].[Bank Account Posting Group]", system="NAV", domain="NAVBI"),
        ],
        sql_query=_load_sql("IPE_31"),
        
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
        
    ),
    # =================================================================
    # == CR_04: NAV GL Balances
    # =================================================================
    # IA BASELINE VALIDATION (2025-11-05):
    # [✓] Source Table: [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]
    # [✓] Logic: Aligned with "Query 2" from CR_03_04 mapping.
    # [✓] Filters: Uses parameterized {cutoff_date} and {gl_accounts}.
    # =================================================================
    CatalogItem(
        item_id="CR_04",
        item_type="CR",
        control="C-PG-1",
        title="NAV GL Balances",
        change_status="No changes",
        last_updated="2025-10-22",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""Procedures:
1) Obtain the query as of last IPE testing (Dec 2024) and (July 2025).
2.1) Using AI, compared the two scrips obtain from the files mention above
2.2) Confirmed if there were any changes to the script except the date and period of extraction
Conclusion: Using the AI output Internal Audit confirmed that:
a) there was no change to the table used in the extraction
b) Except for the date and period of extraction, there were no differences between the 2024 and 2025 queries.
Given the above, and that the period and date of extraction are validated in every control execution, we conclude that the query remained unchanged between the two execution.""",
        notes=(
            "V_Anaplan_BS_View (Anaplan is retired but the view is active and pulls data from NAVBI and FinRec). "
            "CRITICAL: This is the ACTUALS side of the reconciliation - all IPEs reconcile to this. "
            "Test data: CR_04_testing.xlsx. "
            "2024 Query: SELECT * FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT] where CLOSING_DATE between '2024-01-01' and '2024-12-31' and (GROUP_COA_ACCOUNT_NO like '145%' OR GROUP_COA_ACCOUNT_NO like '15%' OR GROUP_COA_ACCOUNT_NO in ('18650','18397'))"
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
        sql_query=_load_sql("CR_04"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("BALANCE_AT_DATE"),
            ColumnExistsCheck("GROUP_COA_ACCOUNT_NO"),
        ],
        
    ),
    # =================================================================
    # == CR_03: NAV GL Entries
    # =================================================================
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
            _src_sql("[AIG_Nav_DW].[dbo].[G_L Entries]", system="NAV", domain="NAVBI"),
            _src_sql("[AIG_Nav_DW].[dbo].[Detailed G_L Entry]", system="NAV", domain="NAVBI"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping]", system="NAV", domain="FinRec"),
        ],
        sql_query=_load_sql("CR_03"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("Amount"),
            ColumnExistsCheck("[Voucher No_]"),
        ],
    ),
    # =================================================================
    # == CR_05: FX Rates (Monthly Closing Rates for USD Conversion)
    # =================================================================
    CatalogItem(
        item_id="CR_05",
        item_type="CR",
        control="C-PG-1",
        title="FX Rates - Monthly Closing Rates",
        change_status="No changes",
        last_updated="2025-11-24",
        output_type="Query",
        tool="PowerPivot",
        third_party=False,
        status="Completed",
        baseline_required=True,
        cross_reference=None,
        description="""Monthly FX closing rates for converting local currency amounts to USD.
        
This control report provides the exchange rates used for financial reporting and reconciliation.
The rates are extracted from RPT_FX_RATES for the specified month and year, filtered for 
'Closing' rate type with USD as the base currency.

The query handles special cases:
- USD-based companies (e.g., Germany USD entities) automatically get rate = 1
- Joins with Dim_Company and Dim_Country for complete company context""",
        notes=(
            "Provides monthly closing FX rates for USD conversion. "
            "Rate logic: Amount_USD = Amount_LCY / FX_rate. "
            "Used by bridge classification functions to report all variances in USD."
        ),
        evidence_ref="CR_05",
        descriptor_excel=None,
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]", system="NAV", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country]", system="NAV", domain="FinRec"),
        ],
        sql_query=_load_sql("CR_05"),
        quality_rules=[
            RowCountCheck(min_rows=1),
            ColumnExistsCheck("Company_Code"),
            ColumnExistsCheck("FX_rate"),
        ],
    ),
    # =================================================================
    # == 10. IPE-34: Marketplace Refund Liability
    # =================================================================
    CatalogItem(
        item_id='IPE_34',
        item_type='IPE',
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
    ),

    # =================================================================
    # == JIRA TICKETS - AUDIT EXTRACTS
    # =================================================================
    # == DS-3900: GL Actuals (Auditor's View)
    # =================================================================
    CatalogItem(
        item_id='DS-3900',
        item_type='DOC',
        control='C-PG-1',
        title='Jira: DS-3900 GL Actuals (Auditor View)',
        change_status='Info',
        last_updated='2025-10-23',
        output_type='Documentation',
        tool='Jira',
        third_party=True,
        status='Reference',
        baseline_required=False,
        cross_reference=None,
        notes=(
            "Placeholder for auditor-view GL extract. Athena path paused; retained for reference."
        ),
        evidence_ref='DS-3900',
        descriptor_excel=None,
        sources=None,
        description="Auditor-view GL extract reference (paused while focusing on SQL Server).",
    ),

    # =================================================================
    # == DS-3899: Revenue Target Values (Auditor's View)
    # =================================================================
    CatalogItem(
        item_id='DS-3899',
        item_type='DOC',
        control='C-PG-1',
        title='Jira: DS-3899 Revenue Target Values',
        change_status='Info',
        last_updated='2025-10-23',
        output_type='Documentation',
        tool='Jira',
        third_party=True,
        status='Reference',
        baseline_required=False,
        cross_reference=None,
        notes=(
            "Placeholder for auditor-view revenue target values. Athena path paused; retained for reference."
        ),
        evidence_ref='DS-3899',
        descriptor_excel=None,
        sources=None,
        description="Auditor-view revenue target values reference (paused while focusing on SQL Server).",
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


# (Athena-specific helpers removed as catalog is now SQL Server-focused)


if __name__ == "__main__":
    # Quick manual check
    from pprint import pprint
    print("C-PG-1 Catalog (summary):")
    for it in CPG1_CATALOG:
        print(f"- {it.item_id:7s} | {it.item_type:3s} | {it.title}")
    print("\nAs dicts (first 2):")
    pprint(to_dicts(CPG1_CATALOG[:2]))
