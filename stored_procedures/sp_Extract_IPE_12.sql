-- =============================================
-- Stored Procedure: sp_Extract_IPE_12
-- Description: Extract TV Packages Delivered Not Reconciled data to CSV file
-- Purpose: Packages delivered but not yet reconciled (payment issues)
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- Source: OMS
-- Business Logic: Packages delivered up to cutoff date that remain unreconciled
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_12]
    @cutoff_date DATE,
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
    
    -- Store procedure name (@@PROCID doesn't work in EXEC parameters)
    SET @procedure_name = 'n8n.sp_Extract_IPE_12'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_12_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT 
        soi.[ID_COMPANY],
        soi.[COD_OMS_ID_PACKAGE],
        soi.[PAYMENT_METHOD],
        soi.[IS_MARKETPLACE],
        soi.[Order_nr],
        soi.[PACKAGE_NUMBER],
        soi.[VOUCHER_TYPE],
        soi.[BOB_ID_CUSTOMER],
        soi.[ORDER_NR],
        soi.[ORDER_CREATION_DATE],
        soi.[SHIPPED_DATE],
        soi.[DELIVERED_DATE],
        soi.[PACKAGE_DELIVERY_DATE],
        soi.[IS_PREPAYMENT],
        soi.[MTR_SHIPPING_FEE_MODIFICATION],
        soi.[TRACKING_NUMBER],
        soi.[OMS_PACKAGE_STATUS],
        ct.[Customer_Type_L1] AS Customer_Type,
        pck.amount_expected,
        pck.amount_received,
        pck.fk_package_status,
        pck.delivered_update_date,
        pck.delivery_date,
        pck.fk_collection_partner,
        pck.last_mile,
        pck.package_status,
        pck.payment_method_confirmed,
        pck.order_nr,
        pck.troubleshoot_resolution_date,
        ISNULL(soi.[MTR_AMOUNT_PAID], 0) AS amount_paid,
        ISNULL(soi.[MTR_PAID_PRICE], 0) AS paid_price,
        ISNULL(soi.[MTR_BASE_SHIPPING_AMOUNT], 0)
            - ISNULL(soi.[MTR_SHIPPING_CART_RULE_DISCOUNT], 0)
            - ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)
            + ISNULL(soi.[MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT], 0)
            - ISNULL(soi.[MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT], 0)
            + ISNULL(soi.[MTR_INTERNATIONAL_FREIGHT_FEE], 0)
            - ISNULL(soi.[MTR_INTERNATIONAL_DELIVERY_FEE_CART_RULE], 0) AS paid_shipping
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
    LEFT JOIN [STG_AIG_NAV_JUMIA_REC].[OMS].[PACKAGE_CASHREC] pck
        ON pck.ID_COMPANY = soi.ID_COMPANY 
        AND pck.[package_nr] = soi.PACKAGE_NUMBER
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_DIM_BOB_CUSTOMER_TYPE] ct 
        ON ct.Bob_Customer_Type = soi.BOB_CUSTOMER_TYPE
    WHERE soi.IS_PREPAYMENT = 0 
        AND soi.Payment_method <> ''NoPayment'' 
        AND soi.DELIVERED_DATE BETWEEN ''2019-01-01 00:00:00'' AND CAST(''' + @cutoff_str + ''' AS DATE)
        AND (
            pck.troubleshoot_resolution_date IS NULL 
            OR pck.troubleshoot_resolution_date > CAST(''' + @cutoff_str + ''' AS DATE)
        )
    '

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
