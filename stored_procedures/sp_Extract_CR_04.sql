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
    DECLARE @bcp_cmd NVARCHAR(4000)
    DECLARE @result_code INT
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
    
    -- Build BCP command for export
    SET @bcp_cmd = 'bcp "' + @query + '" queryout "' + @full_path + 
                   '" -c -t"," -T -S' + @@SERVERNAME + ' -d AIG_Nav_Jumia_Reconciliation'
    
    -- Execute BCP export
    EXEC @result_code = xp_cmdshell @bcp_cmd
    
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