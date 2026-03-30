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
CREATE PROCEDURE [n8n].[sp_Extract_IPE_07]
    @cutoff_date DATE,
    @customer_posting_groups NVARCHAR(500),
    @output_path NVARCHAR(500) = 'C:\SQLExports\',
    @drive_link NVARCHAR(1000)
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @full_path NVARCHAR(500)
    DECLARE @filename NVARCHAR(200)
    DECLARE @export_status NVARCHAR(20) = 'success'
    DECLARE @error_message NVARCHAR(4000) = NULL
    DECLARE @row_count BIGINT
    DECLARE @query NVARCHAR(MAX)
    DECLARE @procedure_name NVARCHAR(255)
    DECLARE @cutoff_str NVARCHAR(10)
    DECLARE @spid_str NVARCHAR(10)
    DECLARE @temp1_name NVARCHAR(50)
    DECLARE @temp2_name NVARCHAR(50)
    DECLARE @sql NVARCHAR(MAX)
    
    -- Store procedure name
    SET @procedure_name = 'n8n.sp_Extract_IPE_07'
    
    -- Convert values to strings for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    SET @spid_str = CAST(@@SPID AS NVARCHAR(10))
    SET @temp1_name = '##temp_' + @spid_str
    SET @temp2_name = '##temp2_' + @spid_str
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_07_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Clean up any existing temp tables
    SET @sql = 'IF OBJECT_ID(''tempdb..' + @temp1_name + ''') IS NOT NULL DROP TABLE ' + @temp1_name
    EXEC sp_executesql @sql
    
    SET @sql = 'IF OBJECT_ID(''tempdb..' + @temp2_name + ''') IS NOT NULL DROP TABLE ' + @temp2_name
    EXEC sp_executesql @sql
    
    -- Build temp table 1: Customer-level remaining balances
    SET @sql = '
    SELECT * 
    INTO ' + @temp1_name + '
    FROM (
        SELECT 
            [id_company],
            [Customer No_],
            SUM([Amount (LCY)]) AS rem_bal_LCY
        FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
        WHERE [Posting Date] <= ''' + @cutoff_str + '''
        GROUP BY [id_company], [Customer No_]
        HAVING SUM([Amount (LCY)]) <> 0
    ) a'
    EXEC sp_executesql @sql
    
    -- Create index on temp table 1
    SET @sql = '
    CREATE NONCLUSTERED INDEX IDX_Temp_' + @spid_str + '
    ON ' + @temp1_name + ' ([ID_company], [Customer No_])
    INCLUDE (rem_bal_LCY)'
    EXEC sp_executesql @sql
    
    -- Build temp table 2: Entry-level remaining balances
    SET @sql = '
    SELECT * 
    INTO ' + @temp2_name + '
    FROM (
        SELECT 
            [id_company],
            [Cust_ Ledger Entry No_],
            SUM([Amount (LCY)]) AS rem_amt_LCY
        FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
        WHERE [Posting Date] <= ''' + @cutoff_str + '''
        GROUP BY [id_company], [Cust_ Ledger Entry No_]
        HAVING SUM([Amount (LCY)]) <> 0
    ) b'
    EXEC sp_executesql @sql
    
    -- Create index on temp table 2
    SET @sql = '
    CREATE NONCLUSTERED INDEX IDX_Temp2_' + @spid_str + '
    ON ' + @temp2_name + ' ([ID_company], [Cust_ Ledger Entry No_])
    INCLUDE (rem_amt_LCY)'
    EXEC sp_executesql @sql
    
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
            WHEN EOMONTH(cle.[Due Date]) < EOMONTH(CAST(''' + @cutoff_str + ''' AS DATE)) THEN ''Credit''
            WHEN EOMONTH(cle.[Due Date]) > EOMONTH(CAST(''' + @cutoff_str + ''' AS DATE)) THEN ''Debit''
            ELSE ''Due Month'' 
        END AS Debit_Credit_DueMonth
    FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
    INNER JOIN ' + @temp1_name + ' dcle
        ON cle.ID_company = dcle.ID_company 
        AND cle.[Customer No_] = dcle.[Customer No_]
    INNER JOIN ' + @temp2_name + ' dcle_2
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
    WHERE cle.[Posting Date] <= ''' + @cutoff_str + '''
        AND cle.[Customer Posting Group] IN (' + @customer_posting_groups + ')
        AND comp.Flg_In_Conso_Scope = 1'

    -- Create temporary table from query (with aliases preserved)
    DECLARE @temp_table NVARCHAR(128) = '##TempExport_' + REPLACE(CONVERT(NVARCHAR(36), NEWID()), '-', '')
    DECLARE @select_into_sql NVARCHAR(MAX)
    DECLARE @bcp_command NVARCHAR(MAX)
    DECLARE @bcp_return_code INT

    BEGIN TRY
        -- Step 1: Populate temp table with query results
        SET @select_into_sql = 'SELECT * INTO ' + @temp_table + ' FROM (' + @query + ') AS sq'
        EXEC sp_executesql @select_into_sql

        -- Step 2: Get row count from temp table
        DECLARE @count_query_temp NVARCHAR(MAX) = 'SELECT @count = COUNT(*) FROM ' + @temp_table
        EXEC sp_executesql @count_query_temp, N'@count BIGINT OUTPUT', @row_count OUTPUT

        -- Step 3: Export via BCP from temp table
        SET @bcp_command = 'bcp "SELECT * FROM ' + @temp_table + '" queryout "' + @full_path + '" -T -c'
        EXEC @bcp_return_code = xp_cmdshell @bcp_command

        IF @bcp_return_code <> 0
        BEGIN
            SET @export_status = 'error'
            SET @error_message = 'BCP command failed with return code: ' + CAST(@bcp_return_code AS NVARCHAR(10))
        END
    END TRY
    BEGIN CATCH
        SET @export_status = 'error'
        SET @error_message = ERROR_MESSAGE()
    END CATCH

    -- Clean up temporary table
    IF OBJECT_ID('tempdb..' + @temp_table) IS NOT NULL
        EXEC ('DROP TABLE ' + @temp_table)
    
    -- Clean up temp tables
    SET @sql = 'IF OBJECT_ID(''tempdb..' + @temp1_name + ''') IS NOT NULL DROP TABLE ' + @temp1_name
    EXEC sp_executesql @sql
    
    SET @sql = 'IF OBJECT_ID(''tempdb..' + @temp2_name + ''') IS NOT NULL DROP TABLE ' + @temp2_name
    EXEC sp_executesql @sql
    
    -- Send to Google Drive
    EXEC [n8n].[sp_Send_Csv_To_Drive]
        @drive_link = @drive_link,
        @file_path = @full_path,
        @file_name = @filename,
        @procedure_name = @procedure_name,
        @row_count = @row_count,
        @export_status = @export_status,
        @error_message = @error_message

    -- Check if export succeeded
    IF @export_status <> 'success'
    BEGIN
        SELECT 
            'error' AS status,
            @error_message AS error_message
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
