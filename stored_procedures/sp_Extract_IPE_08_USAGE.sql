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
    DECLARE @temp_table NVARCHAR(128)
    DECLARE @select_into_sql NVARCHAR(MAX)
    DECLARE @bcp_command NVARCHAR(MAX)
    DECLARE @bcp_return_code INT
    
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
        AND soi.[PACKAGE_DELIVERY_DATE] < CAST(''' + @cutoff_str + ''' AS DATE)
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
