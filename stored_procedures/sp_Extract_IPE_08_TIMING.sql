-- =============================================
-- Stored Procedure: sp_Extract_IPE_08_TIMING
-- Description: Extract TV Voucher Timing Differences data to CSV file
-- Purpose: Vouchers created before cutoff, still valid at cutoff, but inactive
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- Bridge: Timing Difference
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_08_TIMING]
    @cutoff_date DATE,
    @output_path NVARCHAR(500) = 'C:\SQLExports\'
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @full_path NVARCHAR(500)
    DECLARE @filename NVARCHAR(200)
    DECLARE @export_status NVARCHAR(20) = 'success'
    DECLARE @error_message NVARCHAR(4000) = NULL
    DECLARE @webhook_url NVARCHAR(1000) = 'https://n8n.ops.jumia.com/webhook-test/10d7f0e2-995f-4e76-a766-e2bd3029e75e'
    DECLARE @row_count BIGINT
    DECLARE @query NVARCHAR(MAX)
    DECLARE @procedure_name NVARCHAR(255)
    DECLARE @cutoff_str NVARCHAR(10)
    
    -- Store procedure name (@@PROCID doesn't work in EXEC parameters)
    SET @procedure_name = 'n8n.sp_Extract_IPE_08_TIMING'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_08_TIMING_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT
        t1.[ID_Company],
        t1.[id] AS [Voucher_ID],
        t1.[Code],
        t1.[discount_amount] AS [Amount],
        NULL AS [Currency],
        t1.[Business_Use],
        t1.[type] AS [Origin],
        CASE
            WHEN ISNULL(t1.[is_active], 0) = 1 THEN ''active''
            ELSE ''inactive''
        END AS [Status],
        t1.[created_at] AS [Creation_Date],
        t1.[from_date] AS [Start_Date],
        t1.[to_date] AS [End_Date],
        tTwo.[COD_OMS_SALES_ORDER_ITEM] AS [fk_Sales_Order_Item],
        tTwo.[ID_Sales_Order_Item],
        tTwo.[ORDER_CREATION_DATE] AS [Order_Creation_Date],
        tTwo.[DELIVERED_DATE] AS [Order_Delivery_Date],
        tTwo.[CANCELLATION_DATE] AS [Order_Cancellation_Date],
        tTwo.[CURRENT_STATUS] AS [Order_Item_Status],
        tTwo.[Payment_Method],
        t1.[fk_Customer],
        tTwo.[COD_OMS_SALES_ORDER] AS [fk_Sales_Order],
        tTwo.[Order_Nr],
        t1.[description] AS [Comment],
        NULL AS [Wallet_Name]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
        ON t1.[ID_Company] = tTwo.[ID_Company]
        AND t1.[Code] = tTwo.[voucher_code]
    WHERE t1.[created_at] < CAST(''' + @cutoff_str + ''' AS DATE)
        AND ISNULL(t1.[is_active], 0) = 0
        AND t1.[to_date] >= CAST(''' + @cutoff_str + ''' AS DATE)
        AND (
            tTwo.[CURRENT_STATUS] NOT IN (''delivered'', ''cancelled'', ''closed'')
            OR tTwo.[CURRENT_STATUS] IS NULL
        )
        AND (
            tTwo.[DELIVERED_DATE] >= CAST(''' + @cutoff_str + ''' AS DATE)
            OR tTwo.[DELIVERED_DATE] IS NULL
        )
        AND (
            tTwo.[CANCELLATION_DATE] >= CAST(''' + @cutoff_str + ''' AS DATE)
            OR tTwo.[CANCELLATION_DATE] IS NULL
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

    EXEC [n8n].[sp_Send_Csv_To_Webhook]
        @webhook_url = @webhook_url,
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
