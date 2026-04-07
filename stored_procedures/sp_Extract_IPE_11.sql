-- =============================================
-- Stored Procedure: sp_Extract_IPE_11
-- Description: Extract Marketplace Accrued Revenues data to CSV file
-- Purpose: Seller transactions not yet paid out (accrued revenues)
-- Parameters: 
--   @period_month_start: Start of reporting period (YYYY-MM-DD HH:MM:SS)
--   @subsequent_month_start: Start of next month / exclusive end of reporting period (YYYY-MM-DD HH:MM:SS)
--   @output_path: Directory for output file (default: D:\INTFIN-Data\SOC_n8n)
--   @drive_link: Google Drive folder link for upload target
-- Returns: File path, filename, and row count
-- Source: RING (Seller Center)
-- GL Accounts: Marketplace accrued revenue accounts
-- Logic: Captures transactions created during the reporting period that remain unpaid
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_11]
    @period_month_start DATETIME,
    @subsequent_month_start DATETIME,
    @output_path NVARCHAR(500) = 'D:\INTFIN-Data\SOC_n8n',
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
    DECLARE @period_start_str NVARCHAR(30)
    DECLARE @subsequent_start_str NVARCHAR(30)
    DECLARE @temp_table NVARCHAR(128)
    DECLARE @select_into_sql NVARCHAR(MAX)
    DECLARE @bcp_command VARCHAR(8000)
    DECLARE @bcp_return_code INT
    
    -- Store procedure name (@@PROCID doesn't work in EXEC parameters)
    SET @procedure_name = 'n8n.sp_Extract_IPE_11'
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_11_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @output_path = CASE 
        WHEN RIGHT(@output_path, 1) IN ('\\', '/') THEN @output_path
        ELSE @output_path + '\\'
    END
    SET @full_path = @output_path + @filename
    
    -- Convert parameters to strings for query
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
            OR stt.[RING_End_Date] >= ''' + @subsequent_start_str + '''
        )
    '

    -- Create temporary table from query (with aliases preserved)
    SET @temp_table = '##TempExport_' + REPLACE(CONVERT(NVARCHAR(36), NEWID()), '-', '')

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
