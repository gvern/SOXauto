-- =============================================
-- Report: NAV GL Entries (CR_03)
-- Description: General ledger entries 
-- Parameters: {subsequent_month_start}, {gl_accounts_cr_03}
-- Source: NAV Data Warehouse
-- GL Account: 15010
-- Purpose: Extract GL entries for variance analysis 
-- =============================================

SELECT
    gl.[id_company],
    comp.[Company_Country],
    comp.Flg_In_Conso_Scope,
    comp.[Opco/Central_?],
    gl.[Entry No_],
    gl.[Document No_],
    gl.[External Document No_],
    gl.[Voucher No_],
    gl.[Posting Date],
    gl.[Document Date],
    gl.[Document Type],
    gl.[Chart of Accounts No_],
    gl.[Account Name],
    coa.Group_COA_Account_no,
    coa.[Group_COA_Account_Name],
    gl.[Document Description],
    gl.[Amount],
    dgl.rem_bal_LCY AS Remaining_amount,
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
        WHEN gl.[Document Description] LIKE '%BM%' 
            OR gl.[Document Description] LIKE '%BACKMARGIN%' 
        THEN 'BackMargin'
        ELSE 'Other'
    END AS EntryType
FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
INNER JOIN (
    -- Subquery: Calculate remaining balances for GL entries
    SELECT
        det.[id_company],
        det.[Gen_ Ledger Entry No_],
        SUM(det.[Amount]) AS rem_bal_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
        ON comp.Company_Code = det.id_company
    WHERE det.[Posting Date] < CAST({subsequent_month_start} AS DATETIME)
        AND det.[G_L Account No_] IN {gl_accounts_cr_03}
        AND comp.Flg_In_Conso_Scope = 1
    GROUP BY det.[id_company], det.[Gen_ Ledger Entry No_]
    HAVING SUM(det.[Amount]) <> 0
) dgl
    ON gl.id_company = dgl.id_company 
    AND dgl.[Gen_ Ledger Entry No_] = gl.[Entry No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    ON comp.Company_Code = gl.id_company
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa
    ON coa.[Company_Code] = gl.id_company 
    AND coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs
    ON ifrs.Level_4_Code = coa.Group_COA_Account_no
WHERE gl.[Posting Date] < CAST({subsequent_month_start} AS DATETIME)
    AND gl.[id_company] NOT LIKE '%USD%';
