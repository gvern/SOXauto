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
    # SQL Server support (preferred going forward)
    sql_query: Optional[str] = None
    description: Optional[str] = None


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
        ],
    sql_query="""select vl.[id_company],
vl.[Entry No_],
vl.[Document No_],
vl.[Document Type],
vl.[External Document No_],
vl.[Posting Date],
vl.[Customer No_],
vl.[Description],
vl.[Source Code],
vl.[Busline Code],
vl.[Department Code],
vl.[Original Amount],
vl.[Currency],
vl.[Original Amount (LCY)],
vl.[Due Date],
vl.[Posted by],
vl.[Partner Code],
vl.[IC Partner Code],
cus.name Customer_Name,
cus.[Customer Posting Group],
cus.[Busline Code] Resp_Center,
cus_g.[Receivables Account],
fdw.Group_COA_Account_no,
vlle.[Remaining Amount] rm_amt,
vlle.[Remaining Amount_LCY] rm_amt_lcy
FROM [dbo].[Customer Ledger Entries] vl WITH (NOLOCK)
LEFT JOIN (
SELECT [id_company]
,[Cust_ Ledger Entry No_] as clen
,SUM([Amount]) as [Remaining Amount]
,SUM([Amount (LCY)]) as [Remaining Amount_LCY]
FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
where [Posting Date] < '{cutoff_date}'
and id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
Group by [id_company], [Cust_ Ledger Entry No_]) vlle ON vl.[Entry No_]=vlle.clen AND vl.id_company = vlle.id_company
LEFT JOIN (
SELECT [id_company]
,[Customer No_] as clen
,SUM([Amount]) as [Remaining Amount]
,SUM([Amount (LCY)]) as Customer_Balance
FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
where [Posting Date] < '{cutoff_date}'
and id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
Group by [id_company], [Customer No_]) C ON vl.[Customer No_]=C.clen AND vl.id_company = C.id_company
LEFT JOIN [dbo].[Customers] cus on cus.id_company = vl.id_company and cus.No_ = vl.[Customer No_]
LEFT JOIN [dbo].[Customer Posting Group] cus_g on cus_g.id_company = cus.id_company and cus_g.Code = cus.[Customer Posting Group]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] fdw on fdw.Company_Code = cus_g.id_company and fdw.[G/L_Account_No] = cus_g.[Receivables Account]
where [Posting Date] < '{cutoff_date}'
and vl.id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
and fdw.Group_COA_Account_no in ('13010','13009','13006','13005','13004','13003')
and vlle.[Remaining Amount_LCY] <> 0
and c.Customer_Balance <> 0
and vl.[Currency]!=''""",
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
            "Multiple baseline files: CR_05_test.xlsx, "
            "CR_05a__IPE Baseline__FA table - FX rates.xlsx, "
            "CR_05b__IPE Baseline__Daily FX rates.xlsx. "
            "May require two separate Athena tables or one combined view."
        ),
        evidence_ref="CR_05",
        descriptor_excel=None,
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]", system="NAV", domain="FinRec"),
        ],
        sql_query="""SELECT [Base_Currency]
            ,[Quote_Currency]
            ,[Rate_Date]
            ,[bid]
            FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES_DAILY]
            where year([Rate_Date]) in ('2025','2024','2023')
            and [Base_Currency] in ('EUR','USD','AED','GBP')""",
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
    sql_query="""SELECT TOP (1) [Currency Code],year([Starting Date]) year,month([Starting Date]) month,[Relational Exch_ Rate Amount]
FROM [D365BC14_DZ].[dbo].[Jade DZ$Currency Exchange Rate]
WHERE [Currency Code] = 'USD'
and [Starting Date] = '{fx_date}'""",
        
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
    sql_query="""SELECT [ID_COMPANY]
,[IS_PREPAYMENT]
,[COD_OMS_SALES_ORDER_ITEM]
,[ORDER_NR]
,[BOB_ID_CUSTOMER]
,[CURRENT_STATUS]
,case when [CURRENT_STATUS] = 'closed' then 1 else 0 end IS_CLOSED
,[IS_MARKETPLACE]
,[PAYMENT_METHOD]
,[ORDER_CREATION_DATE]
,[FINANCE_VERIFIED_DATE]
,[DELIVERED_DATE]
,[PACKAGE_DELIVERY_DATE]
,[REFUND_COMPLETED]
,[REFUND_DATE]
,[FAIL_DATE]
,ISNULL([MTR_UNIT_PRICE],0)-ISNULL([MTR_COUPON_MONEY_VALUE],0)-ISNULL([MTR_CART_RULE_DISCOUNT],0) PAID_FOR_ITEMS
,ISNULL([MTR_PAID_PRICE],0) PAID_PRICE
,ISNULL([MTR_BASE_SHIPPING_AMOUNT],0)-ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0)-ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)+ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0)-ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0) + ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) PAID_FOR_SHIPPING
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
WHERE ORDER_CREATION_DATE > '2018-01-01 00:00:00'
AND [IS_PREPAYMENT] = 1
AND [FINANCE_VERIFIED_DATE] BETWEEN '2018-01-01 00:00:00'
AND DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
AND (
IS_MARKETPLACE = 1
AND (
([DELIVERED_DATE] IS NULL
OR [DELIVERED_DATE] > DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
)
AND (
[REFUND_DATE] IS NULL
OR [REFUND_DATE] > DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
)
)
OR (
IS_MARKETPLACE = 0
AND (
(
(
[DELIVERY_TYPE] IN (
'Digital Content'
,'Gift Card'
)
AND [DELIVERED_DATE] IS NULL
OR [DELIVERED_DATE] > DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
)
OR (
[DELIVERY_TYPE] NOT IN (
'Digital Content'
,'Gift Card'
)
AND [PACKAGE_DELIVERY_DATE] IS NULL
OR [PACKAGE_DELIVERY_DATE] > DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
)
)
AND (
[REFUND_DATE] IS NULL
OR [REFUND_DATE] > DATEADD(s, - 1, DATEADD(mm, DATEDIFF(m, 0, GETDATE()), 0))
)
)
)
)""",
        
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
        description="""This query extracts voucher target values, which are a direct input for the "Timing Difference" bridge classification. 
It retrieves inactive vouchers created before the cutoff date that remain valid at the cutoff date, 
along with related sales order item information for reconciliation purposes.""",
        notes=(
            "File '4. All Countries June-25 - IBSAR Other AR related Accounts.xlsx / Tab 18412' "
            "-> All Countries - Jun.25 - Voucher TV Extract.xlsx. GL = 18412. "
            "Test data: IPE_08_test.xlsx"
        ),
        evidence_ref="IPE_08",
        descriptor_excel="IPE_FILES/IPE_08_test.xlsx",
        sources=[
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]", system="BOB", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]", system="OMS", domain="FinRec"),
        ],
        sql_query="""SELECT
    t1.[ID_Company],
    t1.[Voucher_ID],
    t1.[Code],
    t1.[Amount],
    t1.[Currency],
    t1.[Business_Use],
    t1.[Origin],
    t1.[Status],
    t1.[Creation_Date],
    t1.[Start_Date],
    t1.[End_Date],
    t1.[fk_Sales_Order_Item],
    t1.[ID_Sales_Order_Item],
    tTwo.[Order_Creation_Date],
    tTwo.[Order_Delivery_Date],
    tTwo.[Order_Cancellation_Date],
    tTwo.[Order_Item_Status],
    tTwo.[Payment_Method],
    t1.[fk_Customer],
    t1.[fk_Sales_Order],
    tTwo.[Order_Nr],
    t1.[Comment],
    t1.[Wallet_Name]
FROM
    [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
LEFT JOIN
    [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
ON
    t1.fk_Sales_Order_Item = tTwo.ID_Sales_Order_Item
WHERE
    t1.[Creation_Date] < '{cutoff_date}'
    AND t1.[Status] = 'active'
    AND t1.[Start_Date] <= '{cutoff_date}'
    AND t1.[End_Date] >= '{cutoff_date}'
    AND t1.[Business_Use] NOT IN ('marketing', 'newsletter')
    AND tTwo.[Order_Item_Status] IS NULL""",
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
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING]", system="OMS", domain="FinRec"),
            _src_sql("[AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING]", system="NAV", domain="FinRec"),
        ],
    sql_query="""Declare @subsequentmonth datetime
SET @subsequentmonth = DATEADD(DAY, 1, EOMONTH(GETDATE(), -1)) --#Subsequent Month Date of analysis
;
WITH CTE AS (
    SELECT DISTINCT CONCAT(p.[ID_Company], p.[OMS_Packlist_No]) conc
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES] p
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS] ppa
        ON p.id_company = ppa.id_company
        AND p.OMS_PACKLIST_No = ppa.OMS_PACKLIST_No
        AND ppa.OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
    WHERE p.OMS_Packlist_status IN ('waitingApproval')
       OR (p.OMS_Packlist_Status = 'waitingConfirmation' AND ppa.OMS_PAYMENT_RECONCILED_AMOUNT IS NULL)
)
SELECT
    a.*,
    sn.SERVICE_PROVIDER,
    cp.Type,
    cp.ERP_Name,
    comp.[Company_Country],
    DATEADD(day, -1, @subsequentmonth) AS Closing_date,
    bankacc.[G_L Bank Account No_]
FROM (
    -- OPEN TRANSACTIONS --
    SELECT
        t1.[ID_Company],
        CASE
            WHEN t1.[Transaction_Type] = 'Transfer to' OR t1.[Transaction_Type] = 'Third Party Collection'
                THEN ISNULL(p1.OMS_Payment_Date, t1.created_date)
            WHEN t1.[Transaction_Type] = 'Payment - Rev'
                THEN ISNULL(p1.payment_reversal_date, t1.created_date)
            ELSE t1.Created_Date
        END AS Event_date,
        t1.[Collection_Partner] AS CP,
        t1.[Transaction_Type],
        t1.Related_Entity,
        t1.[Amount]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION] t1
    LEFT JOIN CTE ON CONCAT(t1.[ID_Company], t1.Transaction_List_Nr) = CTE.conc
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT] p1
        ON t1.Related_Entity = p1.OMS_Payment_No
        AND t1.ID_Company = p1.ID_Company
        AND (
            (t1.Transaction_Type = 'Transfer to' AND p1.OMS_Type = 'Transfer') OR
            (t1.Transaction_Type = 'Third Party Collection' AND  p1.OMS_Type = 'Payment') OR
            (t1.Transaction_Type = 'Payment - Rev' AND  p1.OMS_Type = 'Payment')
        )
    WHERE t1.[Transaction_Type] NOT IN (
            'Payment','Collection Adjustment (over)','Collection Adjustment (under)','Payment Charges',
            'Reallocation From','Transfer From','Payment Charges Rev'
        )
      AND (
        CASE
            WHEN t1.[Transaction_Type] = 'Transfer to' OR t1.[Transaction_Type] = 'Third Party Collection'
                THEN ISNULL(p1.OMS_Payment_Date, t1.created_date)
            WHEN t1.[Transaction_Type] = 'Payment - Rev'
                THEN ISNULL(p1.payment_reversal_date, t1.created_date)
            ELSE t1.Created_Date
        END
      ) < @subsequentmonth
      AND (
        t1.Transaction_List_Nr IS NULL
        OR t1.Transaction_List_Date >= @subsequentmonth
        OR CTE.conc IS NOT NULL
      )
      AND t1.[Amount] <> 0
    UNION ALL
    SELECT
        [ID_Company],
        [Original_Transaction_date] AS Event_date,
        [Collection_Partner_From] AS CP,
        [Transaction_type],
        Related_Entity,
        [Amount]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS] realoc
    WHERE [Original_Transaction_date] < @subsequentmonth
      AND [Reallocated_Transaction_Date] >= @subsequentmonth
    UNION ALL
    -- TRANSACTIONLISTS IN PROGRESS --
    SELECT
        tl.ID_company,
        tl.OMS_Packlist_Created_Date AS Event_date,
        tl.[OMS_Collection_Partner_Name] AS CP,
        'Translist in progress' AS Transaction_Type,
        tl.[OMS_Packlist_No] AS Related_entity,
        (tl.OMS_Amount_Received - ISNULL(t2.applied_amount, 0)) AS Amount
    FROM (
        SELECT
            ID_Company, OMS_Collection_Partner_Name, OMS_Packlist_No,
            OMS_Amount_Received, OMS_Packlist_Created_Date
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]
        WHERE OMS_Packlist_Created_Date < @subsequentmonth
          AND OMS_Packlist_Status IN ('inProgress', 'closed', 'waitingConfirmation')
          AND OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
        GROUP BY ID_Company, OMS_Collection_Partner_Name, OMS_Packlist_No, OMS_Amount_Received, OMS_Packlist_Created_Date
    ) tl
    LEFT JOIN (
        SELECT
            [ID_Company], [OMS_Packlist_No],
            SUM(ISNULL([OMS_Payment_Reconciled_Amount], 0) + ISNULL([OMS_Payment_Charges_Reconciled_Amount], 0)) AS applied_amount
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]
        WHERE [OMS_Payment_Date] < @subsequentmonth
        GROUP BY [ID_Company], [OMS_Packlist_No]
    ) t2 ON t2.ID_Company = tl.ID_Company AND t2.OMS_Packlist_No = tl.OMS_Packlist_No
    LEFT JOIN (
        SELECT id_company, OMS_entity_No, OMS_Force_Closed
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]
        WHERE OMS_Entity_Type = 'packlist'
          AND OMS_Force_Closed = 1
          AND (OMS_Close_Date < @subsequentmonth OR OMS_Close_Date IS NULL)
    ) fc ON fc.ID_Company = tl.ID_Company AND fc.OMS_Entity_No = tl.OMS_Packlist_No
    WHERE (fc.OMS_Force_Closed = 0 OR fc.OMS_Force_Closed IS NULL)
      AND (tl.OMS_Amount_Received - ISNULL(t2.applied_amount, 0)) > 0
    UNION ALL
    -- PAYMENTS/TRANSFERS IN PROGRESS --
    SELECT DISTINCT
        p.[ID_Company] AS [ID_Company],
        p.[OMS_Payment_Date] AS Event_date,
        p.OMS_Collection_Partner AS CP,
        p.OMS_Type AS Transaction_Type,
        p.OMS_Payment_No AS Related_entity,
        -(ISNULL(p.OMS_Payment_Amount, 0) + ISNULL(p.OMS_Charges_Amount, 0) - ISNULL(p2.applied_amount, 0)) AS Amount
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT] p
    LEFT JOIN (
        SELECT DISTINCT
            p1.[ID_Company] AS [ID_Company],
            p1.[OMS_Payment_No],
            SUM(ISNULL(p1.[OMS_Payment_Reconciled_Amount], 0) + ISNULL(p1.[OMS_Payment_Charges_Reconciled_Amount], 0)) AS applied_amount
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS] p1
        WHERE p1.[OMS_Packlist_Created_Date] < @subsequentmonth
          AND p1.[OMS_Payment_Date] < @subsequentmonth
          AND p1.[OMS_Payment_Status] IN ('inProgress', 'closed', 'waitingConfirmation')
          AND OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
        GROUP BY p1.[ID_Company], p1.[OMS_Payment_No]
    ) p2 ON p2.ID_Company = p.[ID_Company]
         AND p.OMS_Payment_No = p2.OMS_Payment_No
    LEFT JOIN (
        SELECT DISTINCT
            [ID_Company] AS [ID_Company],
            OMS_entity_No, OMS_Force_Closed
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]
        WHERE OMS_Entity_Type <> 'packlist'
          AND ((OMS_Force_Closed = 1 AND (OMS_Close_Date < @subsequentmonth OR OMS_Close_Date IS NULL)) OR OMS_Close_Date < @subsequentmonth)
    ) fc ON fc.ID_Company =  p.[ID_Company]
         AND fc.OMS_Entity_No = p.OMS_Payment_No
    WHERE p.OMS_Payment_Date < @subsequentmonth
      AND (ISNULL(p.OMS_Payment_Amount, 0) + ISNULL(p.OMS_Charges_Amount, 0) - ISNULL(p2.applied_amount, 0)) > 0
      AND fc.OMS_Force_Closed IS NULL
      AND p.OMS_Payment_Status IN ('inProgress', 'closed', 'waitingConfirmation')
) a
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING] sn
    ON sn.ID_COMPANY = a.[ID_Company] AND sn.[NODE] = a.cp
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONPARTNERS] cp
    ON cp.ID_Company = a.ID_Company AND cp.Name = a.cp
LEFT JOIN (
    SELECT * FROM [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]
    WHERE [Flg_In_Conso_Scope] = 1
) comp ON a.[ID_Company] = comp.[Company_Code]
-- BANK ACCOUNT JOIN
LEFT JOIN (
    SELECT DISTINCT
        CONCAT(
            bk.ID_company,
            bk.[Service Provider No_]
        ) AS CP_Key,
        bank_acc_post.[G_L Bank Account No_]
    FROM [AIG_Nav_DW].[dbo].[Bank Accounts] bk
    LEFT JOIN [AIG_Nav_DW].[dbo].[Bank Account Posting Group] bank_acc_post
        ON bank_acc_post.[ID_Company] = bk.[ID_Company]
        AND bank_acc_post.[Code] = bk.[Bank Account Posting Group]
    WHERE (bk.[Service Provider No_] IS NOT NULL AND bk.[Service Provider No_] <> '')
      AND bank_acc_post.[G_L Bank Account No_] <> '10058'
) bankacc
ON bankacc.CP_Key = CONCAT(a.[ID_Company], cp.ERP_Name)
WHERE Company_Country not in ('TN','TZ','ZA')""",
        
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
    # IA BASELINE VALIDATION COMPLETED:
    # [✓] Source Table: [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]
    # [✓] Filters: WHERE clause filters on CLOSING_DATE (between year_start and year_end)
    # [✓] Filters: WHERE clause filters on GROUP_COA_ACCOUNT_NO (LIKE patterns and IN clause)
    # CONCLUSION: Query matches IA baseline requirements for CR_04
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
    sql_query="""SELECT *
FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]
where CLOSING_DATE between '{year_start}' and '{year_end}'
and (
    GROUP_COA_ACCOUNT_NO like '145%' OR
    GROUP_COA_ACCOUNT_NO like '15%' OR
    GROUP_COA_ACCOUNT_NO in ('18650','18397')
)""",
        
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
        sql_query="""SELECT
    gl.[id_company],
    comp.[Company_Country],
    comp.Flg_In_Conso_Scope,
    comp.[Opco/Central_?],
    gl.[Entry No_],
    gl.[Document No_],
    gl.[External Document No_],
    gl.[Posting Date],
    gl.[Document Date],
    gl.[Document Type],
    gl.[Chart of Accounts No_],
    gl.[Account Name],
    coa.Group_COA_Account_no,
    coa.[Group_COA_Account_Name],
    gl.[Document Description],
    gl.[Amount],
    dgl.rem_bal_LCY Remaining_amount,
    gl.[Busline Code],
    gl.[Department Code],
    gl.[Bal_ Account Type],
    gl.[Bal_ Account No_],
    gl.[Bal_ Account Name],
    gl.[Reason Code],
    gl.[Source Code],
    gl.[Reversed],
    gl.[User ID],
    gl.[G_L Creation Date],
    gl.[Destination Code],
    gl.[Partner Code],
    gl.[System-Created Entry],
    gl.[Source Type],
    gl.[Source No],
    gl.[IC Partner Code],
    gl.[VendorTag Code],
    gl.[CustomerTag Code],
    gl.[Service_Period],
    ifrs.Level_1_Name,
    ifrs.Level_2_Name,
    ifrs.Level_3_Name,
    CASE
        WHEN [Document Description] LIKE '%BM%' OR [Document Description] LIKE '%BACKMARGIN%' THEN 'BackMargin'
        ELSE 'Other'
    END AS EntryType
FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
INNER JOIN (
    SELECT
        det.[id_company],
        det.[Gen_ Ledger Entry No_],
        sum(det.[Amount]) rem_bal_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
        on comp.Company_Code = det.id_company
    WHERE det.[Posting Date] BETWEEN '{year_start}' AND '{year_end}'
    AND det.[G_L Account No_] IN {gl_accounts}
    AND comp.Flg_In_Conso_Scope = 1
    GROUP BY det.[id_company], det.[Gen_ Ledger Entry No_]
    having sum(det.[Amount]) <> 0
) dgl
    on gl.ID_company = dgl.ID_company and dgl.[Gen_ Ledger Entry No_] = gl.[Entry No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    on comp.Company_Code = gl.id_company
left join [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa
    on coa.[Company_Code] = gl.ID_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs
    on ifrs.Level_4_Code = coa.Group_COA_Account_no
WHERE comp.Flg_In_Conso_Scope = 1
""",
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
