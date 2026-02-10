-- =============================================
-- Stored Procedure: sp_Extract_IPE_07
-- Description: Extract Customer Balances data to CSV file
-- App: [FI]
-- Purpose: Customer Balances - Monthly Balances at Date
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @customer_posting_groups: Comma-separated list of posting groups (e.g., 'TV,FEE-MP')
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- =============================================
CREATE PROCEDURE [dbo].[sp_Extract_IPE_07]
    @cutoff_date DATE,
    @customer_posting_groups NVARCHAR(500),
    @output_path NVARCHAR(500) = 'C:\SQLExports\'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @full_path NVARCHAR(500)
    DECLARE @filename NVARCHAR(200)
    DECLARE @bcp_cmd NVARCHAR(4000)
    DECLARE @result_code INT
    DECLARE @row_count BIGINT
    DECLARE @query NVARCHAR(MAX)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_07_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Clean up any existing temp tables
    IF OBJECT_ID('tempdb..##temp_' + CAST(@@SPID AS NVARCHAR(10))) IS NOT NULL 
        DROP TABLE ##temp_' + CAST(@@SPID AS NVARCHAR(10))
    IF OBJECT_ID('tempdb..##temp2_' + CAST(@@SPID AS NVARCHAR(10))) IS NOT NULL 
        DROP TABLE ##temp2_' + CAST(@@SPID AS NVARCHAR(10))
    
    -- Build temp table 1: Customer-level remaining balances
    EXEC('
    SELECT * 
    INTO ##temp_' + CAST(@@SPID AS NVARCHAR(10)) + '
    FROM (
        SELECT 
            [id_company],
            [Customer No_],
            SUM([Amount (LCY)]) AS rem_bal_LCY
        FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
        WHERE [Posting Date] <= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        GROUP BY [id_company], [Customer No_]
        HAVING SUM([Amount (LCY)]) <> 0
    ) a
    ')
    
    -- Create index on temp table 1
    EXEC('
    CREATE NONCLUSTERED INDEX IDX_Temp_' + CAST(@@SPID AS NVARCHAR(10)) + '
    ON ##temp_' + CAST(@@SPID AS NVARCHAR(10)) + ' ([ID_company], [Customer No_])
    INCLUDE (rem_bal_LCY)
    ')
    
    -- Build temp table 2: Entry-level remaining balances
    EXEC('
    SELECT * 
    INTO ##temp2_' + CAST(@@SPID AS NVARCHAR(10)) + '
    FROM (
        SELECT 
            [id_company],
            [Cust_ Ledger Entry No_],
            SUM([Amount (LCY)]) AS rem_amt_LCY
        FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
        WHERE [Posting Date] <= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        GROUP BY [id_company], [Cust_ Ledger Entry No_]
        HAVING SUM([Amount (LCY)]) <> 0
    ) b
    ')
    
    -- Create index on temp table 2
    EXEC('
    CREATE NONCLUSTERED INDEX IDX_Temp2_' + CAST(@@SPID AS NVARCHAR(10)) + '
    ON ##temp2_' + CAST(@@SPID AS NVARCHAR(10)) + ' ([ID_company], [Cust_ Ledger Entry No_])
    INCLUDE (rem_amt_LCY)
    ')
    
    -- Build main query with parameters
    SET @query = '
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
        cst.[Name] AS Customer_Name,
        cst.[Busline Code] AS Customer_Busline,
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
            WHEN EOMONTH(cle.[Due Date]) < EOMONTH(CAST(''' + CAST(@cutoff_date AS NVARCHAR(10)) + ''' AS DATE)) THEN ''Credit''
            WHEN EOMONTH(cle.[Due Date]) > EOMONTH(CAST(''' + CAST(@cutoff_date AS NVARCHAR(10)) + ''' AS DATE)) THEN ''Debit''
            ELSE ''Due Month'' 
        END AS Debit_Credit_DueMonth
    FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
    INNER JOIN ##temp_' + CAST(@@SPID AS NVARCHAR(10)) + ' dcle
        ON cle.ID_company = dcle.ID_company 
        AND cle.[Customer No_] = dcle.[Customer No_]
    INNER JOIN ##temp2_' + CAST(@@SPID AS NVARCHAR(10)) + ' dcle_2
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
    WHERE cle.[Posting Date] <= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        AND cle.[Customer Posting Group] IN (' + @customer_posting_groups + ')
        AND comp.Flg_In_Conso_Scope = 1
    '
    
    -- Get row count first
    DECLARE @count_query NVARCHAR(MAX)
    SET @count_query = 'SELECT @count = COUNT(*) FROM (' + @query + ') AS subquery'
    EXEC sp_executesql @count_query, N'@count BIGINT OUTPUT', @row_count OUTPUT
    
    -- Build BCP command for export
    SET @bcp_cmd = 'bcp "' + @query + '" queryout "' + @full_path + 
                   '" -c -t"," -T -S' + @@SERVERNAME + ' -d AIG_Nav_Jumia_Reconciliation'
    
    -- Execute BCP export
    EXEC @result_code = xp_cmdshell @bcp_cmd
    
    -- Clean up temp tables
    EXEC('
    IF OBJECT_ID(''tempdb..##temp_' + CAST(@@SPID AS NVARCHAR(10)) + ''') IS NOT NULL 
        DROP TABLE ##temp_' + CAST(@@SPID AS NVARCHAR(10)) + '
    IF OBJECT_ID(''tempdb..##temp2_' + CAST(@@SPID AS NVARCHAR(10)) + ''') IS NOT NULL 
        DROP TABLE ##temp2_' + CAST(@@SPID AS NVARCHAR(10)) + '
    ')
    
    -- Check if export succeeded
    IF @result_code <> 0
    BEGIN
        SELECT 
            'error' AS status,
            'BCP export failed' AS error_message,
            @result_code AS error_code
        RETURN
    END
    
    -- Return success result to n8n
    SELECT 
        'success' AS status,
        @full_path AS file_path,
        @filename AS file_name,
        @row_count AS row_count,
        FORMAT(GETDATE(), 'yyyy-MM-dd HH:mm:ss') AS execution_timestamp
END
GO