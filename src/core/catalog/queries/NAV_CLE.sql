-- NAV Customer Ledger Entries (CLE) for Business Line Reclass Analysis
-- 
-- Purpose:
--   Extract Customer Ledger Entries from NAV with business line codes
--   to identify customers with balances across multiple business lines.
--
-- Output Schema:
--   customer_id          : Customer number (NAV Customer No_)
--   business_line_code   : Business line code (Global Dimension 1 Code or Busline Code)
--   amount_lcy           : Remaining amount in local currency
--   posting_date         : Transaction posting date
--   document_no          : Document number
--   customer_name        : Customer name (optional, for reference)
--   entry_no             : Ledger entry number
--
-- Usage:
--   This query is used by the Business Line Reclass bridge calculation
--   to analyze CLE pivot per customer and business line. Customers with
--   balances across multiple business lines are flagged as reclass candidates.
--
-- Parameters:
--   {cutoff_date} - Period end date (YYYY-MM-DD format)
--
-- Data Source:
--   [AIG_Nav_DW].[dbo].[Customer Ledger Entries]
--   [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
--   [AIG_Nav_DW].[dbo].[Customers]
--   [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]

SET NOCOUNT ON;

-- Create temporary table for customers with open balances
IF OBJECT_ID('tempdb..##cle_balances') IS NOT NULL DROP TABLE ##cle_balances;

SELECT 
    cle.[id_company],
    cle.[Customer No_] AS customer_id,
    -- Use Busline Code as business line (or Global Dimension 1 Code if preferred)
    COALESCE(cle.[Busline Code], cle.[Global Dimension 1 Code], 'UNASSIGNED') AS business_line_code,
    SUM(dcle.[Amount (LCY)]) AS amount_lcy
INTO ##cle_balances
FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
INNER JOIN [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry] dcle
    ON cle.[id_company] = dcle.[id_company]
    AND cle.[Entry No_] = dcle.[Cust_ Ledger Entry No_]
WHERE dcle.[Posting Date] <= '{cutoff_date}'
GROUP BY 
    cle.[id_company],
    cle.[Customer No_],
    COALESCE(cle.[Busline Code], cle.[Global Dimension 1 Code], 'UNASSIGNED')
HAVING SUM(dcle.[Amount (LCY)]) <> 0;

-- Create index for performance
CREATE NONCLUSTERED INDEX IDX_CLE_Balances
ON ##cle_balances ([id_company], [customer_id], [business_line_code])
INCLUDE (amount_lcy);

-- Main query: Join back to get customer details
SELECT 
    bal.customer_id,
    bal.business_line_code,
    bal.amount_lcy,
    comp.Company_Country,
    comp.[Opco/Central_?] AS opco_or_central,
    cst.[Name] AS customer_name,
    cst.[Customer Posting Group] AS customer_posting_group,
    cst.[Stream] AS customer_stream,
    -- Aggregate posting date information (latest posting date for this customer+BL)
    MAX(cle.[Posting Date]) AS latest_posting_date,
    -- Count of entries for this customer+BL combination
    COUNT(DISTINCT cle.[Entry No_]) AS num_entries,
    -- Representative document number (first alphabetically)
    MIN(cle.[Document No_]) AS sample_document_no
FROM ##cle_balances bal
LEFT JOIN [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
    ON bal.id_company = cle.id_company
    AND bal.customer_id = cle.[Customer No_]
    AND bal.business_line_code = COALESCE(cle.[Busline Code], cle.[Global Dimension 1 Code], 'UNASSIGNED')
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    ON comp.Company_Code = bal.id_company
LEFT JOIN [AIG_Nav_DW].[dbo].[Customers] cst
    ON cst.[id_company] = bal.id_company
    AND cst.[No_] = bal.customer_id
WHERE 
    -- Filter to in-scope companies
    comp.Flg_In_Conso_Scope = 1
    -- Only include relevant customer posting groups (same as IPE_07)
    AND cst.[Customer Posting Group] IN (
        'LOAN-REC-NAT', 'B2B-NG-NAT','B2C-NG-NAT','B2C-NG-INT','NTR-NG-NAT',
        'B2B-NG-INT','NTR-NG-INT','UE','INL','EXPORT','EU','NATIONAL', 
        'OM','NAT','AUS','EXCB2B-NAT','EMP-NAT'
    )
GROUP BY 
    bal.customer_id,
    bal.business_line_code,
    bal.amount_lcy,
    comp.Company_Country,
    comp.[Opco/Central_?],
    cst.[Name],
    cst.[Customer Posting Group],
    cst.[Stream]
ORDER BY 
    bal.customer_id,
    bal.business_line_code;

-- Cleanup
DROP TABLE ##cle_balances;
