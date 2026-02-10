-- =============================================
-- Stored Procedure: sp_Extract_IPE_08_USAGE
-- Description: Extract TV Voucher Usage data to CSV file
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @cutoff_year: Cutoff year for filtering (YYYY) - Not used in query but kept for consistency
--   @id_companies_active: Comma-separated list of company IDs (e.g., '1,2,3')
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- =============================================
CREATE PROCEDURE [dbo].[sp_Extract_IPE_08_USAGE]
    @cutoff_date DATE,
    @cutoff_year INT,
    @id_companies_active NVARCHAR(500),
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
    SET @filename = 'IPE_08_USAGE_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT 
        soi.[ID_Company],
        scv.[id],
        soi.[voucher_type],
        scv.[business_use],
        YEAR(scv.[created_at]) AS creation_year,
        YEAR(soi.[PACKAGE_DELIVERY_DATE]) * 100 + MONTH(soi.[PACKAGE_DELIVERY_DATE]) AS Delivery_mth,
        SUM(ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS shipping_storecredit,
        SUM(CASE WHEN soi.[is_marketplace] = 1 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS MPL_storecredit,
        SUM(CASE WHEN soi.[is_marketplace] = 0 THEN ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS RTL_storecredit,
        SUM(ISNULL(soi.[MTR_COUPON_MONEY_VALUE], 0) + ISNULL(soi.[MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS TotalAmountUsed
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI] soi
    LEFT JOIN (
        SELECT 
            ID_company,
            [id],
            [code],
            [business_use],
            [created_at]
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING]
    ) scv
        ON scv.ID_company = soi.[ID_Company] 
        AND scv.[code] = soi.[voucher_code]
    WHERE soi.[VOUCHER_TYPE] = ''reusablecredit''
        AND soi.[PACKAGE_DELIVERY_DATE] < ''' + CAST(@cutoff_date AS NVARCHAR(10)) + '''
        AND YEAR(soi.[DELIVERED_DATE]) > 2014
        AND soi.ID_Company IN (' + @id_companies_active + ')
    GROUP BY
        soi.[ID_Company],
        scv.[id],
        soi.[voucher_type],
        scv.[business_use],
        YEAR(scv.[created_at]),
        YEAR(soi.[PACKAGE_DELIVERY_DATE]) * 100 + MONTH(soi.[PACKAGE_DELIVERY_DATE])
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