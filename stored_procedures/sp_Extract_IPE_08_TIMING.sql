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
    DECLARE @openrowset_sql NVARCHAR(MAX)
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
        t1.[Voucher_ID],
        t1.[Code],
        t1.[Amount],
        t1.[Currency],
        t1.[Business_Use],
        t1.[Origin],
        t1.[Status],
        t1.[Creation_Date],
        t1.[Start_Date],
        t1.[End_Date],
        t1.[fk_Sales_Order_Item],
        t1.[ID_Sales_Order_Item],
        tTwo.[Order_Creation_Date],
        tTwo.[Order_Delivery_Date],
        tTwo.[Order_Cancellation_Date],
        tTwo.[Order_Item_Status],
        tTwo.[Payment_Method],
        t1.[fk_Customer],
        t1.[fk_Sales_Order],
        tTwo.[Order_Nr],
        t1.[Comment],
        t1.[Wallet_Name]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] t1
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] tTwo
        ON t1.fk_Sales_Order_Item = tTwo.ID_Sales_Order_Item
    WHERE t1.[Creation_Date] < ''' + @cutoff_str + '''
        AND t1.[Status] = ''inactive''
        AND t1.[End_Date] >= ''' + @cutoff_str + '''
        AND (tTwo.[Order_Item_Status] NOT IN (''delivered'', ''cancelled'', ''closed'') 
             OR tTwo.[Order_Item_Status] IS NULL)
        AND (tTwo.[Order_Delivery_Date] >= ''' + @cutoff_str + '''
             OR tTwo.[Order_Delivery_Date] IS NULL)
        AND (tTwo.[Order_Cancellation_Date] >= ''' + @cutoff_str + '''
             OR tTwo.[Order_Cancellation_Date] IS NULL)
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
