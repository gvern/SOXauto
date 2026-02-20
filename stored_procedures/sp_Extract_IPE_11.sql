-- =============================================
-- Stored Procedure: sp_Extract_IPE_11
-- Description: Extract Marketplace Accrued Revenues data to CSV file
-- Purpose: Seller transactions not yet paid out (accrued revenues)
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @period_month_start: Start of reporting period (YYYY-MM-DD HH:MM:SS)
--   @subsequent_month_start: End of reporting period (YYYY-MM-DD HH:MM:SS)
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- Source: RING (Seller Center)
-- GL Accounts: Marketplace accrued revenue accounts
-- Logic: Captures transactions created during the reporting period that remain unpaid
-- =============================================
CREATE PROCEDURE [dbo].[sp_Extract_IPE_11]
    @cutoff_date DATE,
    @period_month_start DATETIME,
    @subsequent_month_start DATETIME,
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
    DECLARE @cutoff_str NVARCHAR(30)
    DECLARE @period_start_str NVARCHAR(30)
    DECLARE @subsequent_start_str NVARCHAR(30)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_11_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Convert parameters to strings for query
    SET @cutoff_str = CONVERT(NVARCHAR(30), @cutoff_date, 120)
    SET @period_start_str = CONVERT(NVARCHAR(30), @period_month_start, 120)
    SET @subsequent_start_str = CONVERT(NVARCHAR(30), @subsequent_month_start, 120)
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT 
        trs.[ID_Company],
        trs.[Created_Date] AS SC_Created_Date,
        trs.[ID_Transaction] AS SC_ID_Transaction,
        trs.[Transaction_No] AS SC_Transaction_No,
        RTSR.[Transaction_Type_Name] AS SC_Transaction_Type,
        trs.[Transaction_Type] AS SC_ASG_Name,
        trs.[Nav_Type] AS SC_Nav_Type,
        trs.[ERP_Name] AS SC_Nav_Message,
        trs.[Transaction_Amount] AS SC_Transaction_Amount,
        trs.[Created_Manually] AS SC_Created_Manually,
        trs.[Vendor_Short_Code] AS SC_Vendor_No,
        trs.[BOB_ID_Vendor],
        trs.[Vendor_Name] AS SC_Vendor_Name,
        vnd.Is_Global,
        trs.[SC_ID_Sales_Order_Item],
        trs.[OMS_ID_Sales_Order_Item],
        trs.[BOB_ID_Sales_Order_Item],
        trs.[Order_Number] AS Order_Nr,
        trs.[ID_Account_Statement] AS SC_ID_Account_Statement,
        stt.[RING_Transaction_Statement_No] AS SC_Transaction_Statement_No,
        stt.[RING_Start_Date] AS SC_Start_Date,
        stt.[RING_End_Date] AS SC_End_Date,
        stt.[RING_Paid] AS SC_Paid,
        stt.[RING_Paid_Date] AS SC_Paid_Date,
        asg.[ASG_Level_1],
        asg.[ASG_Level_2],
        asg.[ASG_Level_3],
        asg.[ASG_Level_4]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_TRANSACTIONS_SELLER] trs
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[RING].[RPT_ACCOUNTSTATEMENTS] stt
        ON stt.id_company = trs.id_company 
        AND stt.[RING_ID_Transaction_Statement] = trs.[ID_Account_Statement]
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_VENDORS] vnd
        ON vnd.ID_company = trs.ID_company 
        AND vnd.BOB_ID_Vendor = trs.BOB_ID_Vendor
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_DIM_ASG_V2] asg 
        ON trs.[ID_Company] = asg.[ID_Company] 
        AND trs.[Transaction_Type] = asg.[SC_ASG_Name]
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[RING].[RPT_TRANSACTIONS] AS RTSR
        ON trs.ID_Company = RTSR.ID_Company 
        AND trs.ID_Transaction = RTSR.ID_Transaction
    WHERE trs.[Created_Date] > ''2020-01-01 00:00:00.000''
        AND trs.[Created_Date] >= ''' + @period_start_str + '''
        AND trs.[Created_Date] < ''' + @subsequent_start_str + '''
        AND asg.ASG_Level_1 = ''Revenues''
        AND (
            trs.[ID_Account_Statement] IS NULL
            OR stt.[RING_End_Date] > ''' + @cutoff_str + '''
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