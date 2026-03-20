-- =============================================
-- Stored Procedure: sp_Extract_CR_04
-- Description: Extract NAV GL Balances data to CSV file
-- Purpose: General ledger Balances for variance analysis
-- Parameters: 
--   @year_start: Start of year range (YYYY-MM-DD)
--   @year_end: End of year range (YYYY-MM-DD)
--   @gl_accounts_cr_04: Comma-separated list of GL accounts (e.g., '18650','18397')
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- Source: NAV Data Warehouse
-- GL Accounts: 18650, 18397 (and accounts starting with 145%, 15%)
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_CR_04]
    @year_start DATE,
    @year_end DATE,
    @gl_accounts_cr_04 NVARCHAR(500),
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
    DECLARE @year_start_str NVARCHAR(10)
    DECLARE @year_end_str NVARCHAR(10)
    
    -- Store procedure name (@@PROCID doesn't work in EXEC parameters)
    SET @procedure_name = 'n8n.sp_Extract_CR_04'
    
    -- Generate unique filename with timestamp
    SET @filename = 'CR_04_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Convert dates to strings for query
    SET @year_start_str = CONVERT(NVARCHAR(10), @year_start, 120)
    SET @year_end_str = CONVERT(NVARCHAR(10), @year_end, 120)
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT *
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_BS_ANAPLAN_IMPORT_IFRS_MAPPING_CURRENCY_SPLIT]
    WHERE CLOSING_DATE BETWEEN CAST(''' + @year_start_str + ''' AS DATE) AND CAST(''' + @year_end_str + ''' AS DATE)
        AND (
            GROUP_COA_ACCOUNT_NO LIKE ''145%'' 
            OR GROUP_COA_ACCOUNT_NO LIKE ''15%'' 
            OR GROUP_COA_ACCOUNT_NO IN (' + @gl_accounts_cr_04 + ')
        )
    '
    
    -- Create temporary table from query (with aliases preserved)
    DECLARE @temp_table NVARCHAR(128) = '#TempExport_' + REPLACE(CONVERT(NVARCHAR(36), NEWID()), '-', '')
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
    
    EXEC [n8n].[sp_Send_Csv_To_Drive]
        @drive_link = @drive_link,
        @file_path = @full_path,
        @file_name = @filename,
        @procedure_name = @procedure_name,
        @row_count = @row_count,
        @export_status = @export_status,
        @error_message = @error_message
        
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
