-- =============================================
-- Stored Procedure: sp_Extract_IPE_08_USAGE
-- Description: Extract TV Voucher Usage data to CSV file
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @cutoff_year: Year of cutoff (INT) - kept for consistency
--   @id_companies_active: Comma-separated list of company IDs
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_08_USAGE]
    @cutoff_date DATE,
    @cutoff_year INT,
    @id_companies_active NVARCHAR(500),
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
    SET @procedure_name = 'n8n.sp_Extract_IPE_08_USAGE'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_08_USAGE_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT
        soi.[ID_Company],
        scv.[id] AS voucher_id,
        soi.[voucher_type],
        scv.[business_use],
        YEAR(scv.[created_at]) AS creation_year,
        CONCAT(YEAR(soi.[DELIVERED_DATE]), ''-'', FORMAT(soi.[DELIVERED_DATE], ''MM'')) AS Delivery_mth,
        SUM(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS shipping_storecredit,
        SUM(CASE WHEN soi.[is_marketplace] = 1 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS MPL_storecredit,
        SUM(CASE WHEN soi.[is_marketplace] = 0 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS RTL_storecredit,
        SUM(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) + 
        SUM(CASE WHEN soi.[is_marketplace] = 1 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) +
        SUM(CASE WHEN soi.[is_marketplace] = 0 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS TotalAmountUsed
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] scv
        ON soi.[ID_Company] = scv.[ID_Company]
        AND soi.[voucher_code] = scv.[code]
    WHERE soi.[VOUCHER_TYPE] = ''reusablecredit''
        AND soi.[PACKAGE_DELIVERY_DATE] < ''' + @cutoff_str + '''
        AND YEAR(soi.[DELIVERED_DATE]) > 2014
        AND soi.[ID_Company] IN (' + @id_companies_active + ')
    GROUP BY
        soi.[ID_Company],
        scv.[id],
        soi.[voucher_type],
        scv.[business_use],
        YEAR(scv.[created_at]),
        CONCAT(YEAR(soi.[DELIVERED_DATE]), ''-'', FORMAT(soi.[DELIVERED_DATE], ''MM''))
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
