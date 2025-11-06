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
    on gl.id_company = dgl.id_company and dgl.[Gen_ Ledger Entry No_] = gl.[Entry No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    on comp.Company_Code = gl.id_company
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa
    on coa.[Company_Code] = gl.id_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs
    on ifrs.Level_4_Code = coa.Group_COA_Account_no
WHERE comp.Flg_In_Conso_Scope = 1
