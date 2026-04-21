-- =============================================
-- Stored Procedure: sp_Extract_IPE_10
-- Description: Extract TV Customer Prepayments data to CSV file
-- Purpose: Customer prepayment balances - orders paid but not yet delivered/refunded
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @output_path: Directory for output file (default: D:\SOC_n8n\)
--   @drive_link: Google Drive folder link for upload target
-- Returns: File path, filename, and row count
-- GL Accounts: Customer prepayment liability accounts
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_10]
    @cutoff_date DATE,
    @output_path NVARCHAR(500) = 'D:\SOC_n8n\',
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
    DECLARE @temp_table NVARCHAR(128)
    DECLARE @select_into_sql NVARCHAR(MAX)
    DECLARE @bcp_command VARCHAR(8000)
    DECLARE @bcp_return_code INT
    
    -- Store procedure name (@@PROCID doesn't work in EXEC parameters)
    SET @procedure_name = 'n8n.sp_Extract_IPE_10'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_10_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @output_path = CASE 
        WHEN RIGHT(@output_path, 1) IN ('\\', '/') THEN @output_path
        ELSE @output_path + '\\'
    END
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT
        [ID_COMPANY],
        [IS_PREPAYMENT],
        [COD_OMS_SALES_ORDER_ITEM],
        [ORDER_NR],
        [BOB_ID_CUSTOMER],
        [CURRENT_STATUS],
        CASE WHEN [CURRENT_STATUS] = ''closed'' THEN 1 ELSE 0 END AS IS_CLOSED,
        [IS_MARKETPLACE],
        [DELIVERY_TYPE],
        [PAYMENT_METHOD],
        [ORDER_CREATION_DATE],
        [FINANCE_VERIFIED_DATE],
        [DELIVERED_DATE],
        [PACKAGE_DELIVERY_DATE],
        [REFUND_COMPLETED],
        [REFUND_DATE],
        [FAIL_DATE],
        ISNULL([MTR_UNIT_PRICE], 0) - ISNULL([MTR_COUPON_MONEY_VALUE], 0) - ISNULL([MTR_CART_RULE_DISCOUNT], 0) AS PAID_FOR_ITEMS,
        ISNULL([MTR_PAID_PRICE], 0) AS PAID_PRICE,
        ISNULL([MTR_BASE_SHIPPING_AMOUNT], 0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT], 0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT], 0) + ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT], 0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT], 0) + ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
    WHERE ORDER_CREATION_DATE > ''2018-01-01 00:00:00''
        AND [IS_PREPAYMENT] = 1
        AND [FINANCE_VERIFIED_DATE] BETWEEN ''2018-01-01 00:00:00'' AND CAST(''' + @cutoff_str + ''' AS DATETIME)
        AND (
            (
                IS_MARKETPLACE = 1
                AND (
                    (
                        [DELIVERED_DATE] IS NULL
                        OR [DELIVERED_DATE] > CAST(''' + @cutoff_str + ''' AS DATETIME)
                    )
                    AND (
                        [REFUND_DATE] IS NULL
                        OR [REFUND_DATE] > CAST(''' + @cutoff_str + ''' AS DATETIME)
                    )
                )
            )
            OR
            (
                IS_MARKETPLACE = 0
                AND (
                    (
                        (
                            [DELIVERY_TYPE] IN (''Digital Content'', ''Gift Card'')
                            AND (
                                [DELIVERED_DATE] IS NULL
                                OR [DELIVERED_DATE] > CAST(''' + @cutoff_str + ''' AS DATETIME)
                            )
                        )
                        OR
                        (
                            [DELIVERY_TYPE] NOT IN (''Digital Content'', ''Gift Card'')
                            AND (
                                [PACKAGE_DELIVERY_DATE] IS NULL
                                OR [PACKAGE_DELIVERY_DATE] > CAST(''' + @cutoff_str + ''' AS DATETIME)
                            )
                        )
                    )
                    AND (
                        [REFUND_DATE] IS NULL
                        OR [REFUND_DATE] > CAST(''' + @cutoff_str + ''' AS DATETIME)
                    )
                )
            )
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
        SET @bcp_command = 'bcp "SELECT * FROM ' + @temp_table + '" queryout "' + @full_path + '" -c -T -S CHAOS\INTFIN2019'
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
