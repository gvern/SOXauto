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
CREATE PROCEDURE [dbo].[sp_Extract_CR_04]
    @year_start DATE,
    @year_end DATE,
    @gl_accounts_cr_04 NVARCHAR(500),
    @output_path NVARCHAR(500) = 'C:\SQLExports\'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @full_path NVARCHAR(500)
    DECLARE @filename NVARCHAR(200)
    DECLARE @openrowset_sql NVARCHAR(MAX)
    DECLARE @export_status NVARCHAR(20) = 'success'
    DECLARE @error_message NVARCHAR(4000) = NULL
    DECLARE @webhook_url NVARCHAR(1000) = 'https://n8n.ops.jumia.com/webhook-test/10d7f0e2-995f-4e76-a766-e2bd3029e75e'
    DECLARE @row_count BIGINT
    DECLARE @query NVARCHAR(MAX)
    DECLARE @year_start_str NVARCHAR(10)
    DECLARE @year_end_str NVARCHAR(10)
    
    -- Generate unique filename with timestamp
    SET @filename = 'CR_04_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Convert dates to strings for query
    SET @year_start_str = CAST(@year_start AS NVARCHAR(10))
    SET @year_end_str = CAST(@year_end AS NVARCHAR(10))
    
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
    
    -- Get row count first
    DECLARE @count_query NVARCHAR(MAX)
    SET @count_query = 'SELECT @count = COUNT(*) FROM (' + @query + ') AS subquery'
    EXEC sp_executesql @count_query, N'@count BIGINT OUTPUT', @row_count OUTPUT
    
    BEGIN TRY
        SET @openrowset_sql = N'
        INSERT INTO OPENROWSET(
            ''Microsoft.ACE.OLEDB.12.0'',
            ''Text;Database=' + REPLACE(@output_path, '''', '''''') + ';HDR=YES;FMT=Delimited'',
            ''SELECT * FROM [' + @filename + ']'')
        ' + @query

        EXEC sp_executesql @openrowset_sql
    END TRY
    BEGIN CATCH
        SET @export_status = 'error'
        SET @error_message = ERROR_MESSAGE()
    END CATCH

    EXEC [dbo].[sp_Send_Csv_To_Webhook]
        @webhook_url = @webhook_url,
        @file_path = @full_path,
        @file_name = @filename,
        @procedure_name = OBJECT_SCHEMA_NAME(@@PROCID) + '.' + OBJECT_NAME(@@PROCID),
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