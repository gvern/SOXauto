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
CREATE PROCEDURE [dbo].[sp_Extract_IPE_08_TIMING]
    @cutoff_date DATE,
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
    SET @filename = 'IPE_08_TIMING_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
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
    WHERE t1.[Creation_Date] < ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        AND t1.[Status] = ''inactive''
        AND t1.[End_Date] >= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        AND (tTwo.[Order_Item_Status] NOT IN (''delivered'', ''cancelled'', ''closed'') 
             OR tTwo.[Order_Item_Status] IS NULL)
        AND (tTwo.[Order_Delivery_Date] >= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
             OR tTwo.[Order_Delivery_Date] IS NULL)
        AND (tTwo.[Order_Cancellation_Date] >= ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
             OR tTwo.[Order_Cancellation_Date] IS NULL)
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