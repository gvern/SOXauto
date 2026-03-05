-- =============================================
-- Stored Procedure: sp_Extract_IPE_10
-- Description: Extract TV Customer Prepayments data to CSV file
-- Purpose: Customer prepayment balances - orders paid but not yet delivered/refunded
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- GL Accounts: Customer prepayment liability accounts
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_10]
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
    SET @procedure_name = 'n8n.sp_Extract_IPE_10'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_10_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
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
