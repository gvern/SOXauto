-- =============================================
-- App: [FI]
-- Report: Customer Balances
-- Description: Customer Balances - Monthly Balances at Date
-- Parameters: {cutoff_date}
-- =============================================

SET NOCOUNT ON;

IF OBJECT_ID('tempdb..##temp') IS NOT NULL DROP TABLE ##temp;
IF OBJECT_ID('tempdb..##temp2') IS NOT NULL DROP TABLE ##temp2;

-- Build temp table 1: Customer-level remaining balances
SELECT * 
INTO ##temp 
FROM (
    SELECT 
        [id_company],
        [Customer No_],
        SUM([Amount (LCY)]) AS rem_bal_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
    WHERE [Posting Date] <= {cutoff_date}
    GROUP BY [id_company], [Customer No_]
    HAVING SUM([Amount (LCY)]) <> 0
) a;

CREATE NONCLUSTERED INDEX IDX_Temp
ON ##temp ([ID_company], [Customer No_])
INCLUDE (rem_bal_LCY);

-- Build temp table 2: Entry-level remaining balances
SELECT * 
INTO ##temp2 
FROM (
    SELECT 
        [id_company],
        [Cust_ Ledger Entry No_],
        SUM([Amount (LCY)]) AS rem_amt_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
    WHERE [Posting Date] <= {cutoff_date}
    GROUP BY [id_company], [Cust_ Ledger Entry No_]
    HAVING SUM([Amount (LCY)]) <> 0
) b;

CREATE NONCLUSTERED INDEX IDX_Temp2
ON ##temp2 ([ID_company], [Cust_ Ledger Entry No_])
INCLUDE (rem_amt_LCY);

-- Main query: Customer ledger entries with balances
SELECT 
    cle.[id_company],
    comp.Company_Country,
    comp.[Opco/Central_?],
    cle.[Entry No_],
    cle.[GL Entry No_],
    cle.[Document No_],
    cle.[Document Type],
    cle.[External Document No_],
    cle.[Posting Date],
    cle.[Customer No_],
    cst.[Name] AS 'Customer Name',
    cst.[Busline Code] AS 'Customer Busline',
    cst.[Automatically integrated],
    cst.[Customer Posting Group] AS currentpostinggroup,
    cst.[Stream],
    cle.[Customer Posting Group],
    cle.[Description],
    cle.[Source Code],
    cle.[Reason Code],
    cle.[Busline Code],
    bl.[Busline_Vertical_Name_1],
    bl.[Busline_Vertical_Name_2],
    bl.[Busline_Vertical_Name_3],
    cle.[Department Code],
    cle.[Original Amount],
    cle.[Currency],
    cle.[Original Amount (LCY)],
    dcle_2.rem_amt_LCY,
    cle.[Open],
    cle.[Due Date],
    cle.[Posted by],
    cle.[Destination Code],
    cle.[Partner Code],
    cle.[IC Partner Code],
    CASE 
        WHEN EOMONTH(cle.[Due Date]) < EOMONTH(CAST({cutoff_date} AS DATE)) THEN 'Credit'
        WHEN EOMONTH(cle.[Due Date]) > EOMONTH(CAST({cutoff_date} AS DATE)) THEN 'Debit'
        ELSE 'Due Month' 
    END AS 'Debit_Credit_DueMonth'
FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
INNER JOIN ##temp dcle
    ON cle.ID_company = dcle.ID_company 
    AND cle.[Customer No_] = dcle.[Customer No_]
INNER JOIN ##temp2 dcle_2
    ON cle.ID_company = dcle_2.ID_company 
    AND cle.[Entry No_] = dcle_2.[Cust_ Ledger Entry No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    ON comp.Company_Code = cle.id_company
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Busline] bl
    ON bl.[Company_Code] = cle.id_company 
    AND bl.[Busline_Code] = cle.[Busline Code]
LEFT JOIN [AIG_Nav_DW].[dbo].[Customers] cst
    ON cst.[id_company] = cle.id_company 
    AND cst.[No_] = cle.[Customer No_]
WHERE cle.[Posting Date] <= {cutoff_date}
    AND cle.[Customer Posting Group] IN {customer_posting_groups}
    AND comp.Flg_In_Conso_Scope = 1;

DROP TABLE ##temp;
DROP TABLE ##temp2;
