-- =============================================
-- Stored Procedure: sp_Extract_IPE_08_ISSUANCE
-- Description: Extract TV Voucher Issuance data to CSV file
-- Parameters: 
--   @cutoff_date: Cutoff date for extraction (YYYY-MM-DD)
--   @id_companies_active: Comma-separated list of company IDs (e.g., '1,2,3')
--   @output_path: Directory for output file (default: D:\SOC_n8n\)
--   @drive_link: Google Drive folder link for upload target
-- Returns: File path, filename, and row count
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_IPE_08_ISSUANCE]
    @cutoff_date DATE,
    @id_companies_active NVARCHAR(500),
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
    SET @procedure_name = 'n8n.sp_Extract_IPE_08_ISSUANCE'
    
    -- Convert date to string for dynamic SQL
    SET @cutoff_str = CONVERT(NVARCHAR(10), @cutoff_date, 120)
    
    -- Generate unique filename with timestamp
    SET @filename = 'IPE_08_ISSUANCE_' + FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @output_path = CASE 
        WHEN RIGHT(@output_path, 1) IN ('\\', '/') THEN @output_path
        ELSE @output_path + '\\'
    END
    SET @full_path = @output_path + @filename
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT
        scv.[ID_COMPANY],
        scv.[id],
        scv.[business_use],
        CASE WHEN scv.[business_use] = ''jpay_store_credit'' THEN (
            CASE WHEN LEFT(scv.[code], 2) = ''GC'' THEN ''jpay_store_credit_gift''
                WHEN LEFT(scv.[code], 2) = ''JP'' THEN ''jpay_store_credit_DS'' 
                ELSE ''jpay_store_credit_other'' 
            END)
            ELSE scv.[business_use] 
        END AS business_use_formatted,
        scv2.[template_id],
        scv2.[template_name],
        scv.[description],
        scv.[is_active],
        scv.[type],
        scv.[Template_status],
        scv.[discount_amount],
        scv.[from_date],
        scv.[to_date],
        CONCAT(YEAR(scv.[to_date]), ''-'', MONTH(scv.[to_date])) AS expiration_ym,
        (CASE 
            WHEN scv.[to_date] < ''' + @cutoff_str + ''' THEN ''expired'' 
            ELSE ''valid'' 
        END) AS Is_Valid,
        scv.[created_at],
        CONCAT(YEAR(scv.[created_at]), ''-'', MONTH(scv.[created_at])) AS creation_ym,
        CONCAT(YEAR(scv.[updated_at]), ''-'', MONTH(scv.[updated_at])) AS last_update_ym,
        scv.[last_time_used],
        scv.[snapshot_date],
        scv.[voucher_inactive_date],
        scv.[template_inactive_date],
        CONCAT(YEAR(scv.[voucher_inactive_date]), ''-'', MONTH(scv.[voucher_inactive_date])) AS codeinactive_ym,
        CONCAT(YEAR(scv.[template_inactive_date]), ''-'', MONTH(scv.[template_inactive_date])) AS templateinactive_ym,
        scv.[reason],
        scv.[updated_at],
        scv.[fk_customer],
        scv.[used_discount_amount],
        scv.[times_used],
        scv.[remaining_amount],
        sd3.[voucher_type],
        ISNULL(sd3.shipping_discount, 0) AS shipping_discount,
        ISNULL(sd3.shipping_storecredit, 0) AS shipping_storecredit,
        ISNULL(sd3.MPL_storecredit, 0) AS MPL_storecredit,
        ISNULL(sd3.RTL_storecredit, 0) AS RTL_storecredit,
        (ISNULL(sd3.shipping_storecredit, 0) + ISNULL(sd3.MPL_storecredit, 0) + ISNULL(sd3.RTL_storecredit, 0)) AS TotalAmountUsed,
        (ISNULL(scv.discount_amount, 0) - (ISNULL(sd3.shipping_storecredit, 0) + ISNULL(sd3.MPL_storecredit, 0) + ISNULL(sd3.RTL_storecredit, 0))) AS TotalRemainingAmount,
        CASE 
            WHEN scv.[to_date] > (
                CASE 
                    WHEN scv.[voucher_inactive_date] > scv.[template_inactive_date] 
                    THEN scv.[template_inactive_date] 
                    ELSE scv.[voucher_inactive_date] 
                END)
            THEN (
                CASE 
                    WHEN scv.[voucher_inactive_date] > scv.[template_inactive_date] 
                    THEN scv.[template_inactive_date] 
                    ELSE scv.[voucher_inactive_date] 
                END)
            ELSE scv.[to_date] 
        END AS min_inactive_date
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[V_STORECREDITVOUCHER_CLOSING] scv 
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[StoreCreditVoucher] scv2 
        ON scv.id = scv2.id 
        AND scv.ID_COMPANY = scv2.ID_COMPANY
    LEFT JOIN (
        SELECT
            [ID_Company],
            [voucher_code],
            [voucher_type],
            SUM(ISNULL([MTR_SHIPPING_DISCOUNT_AMOUNT], 0)) AS shipping_discount,
            SUM(ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT], 0)) AS shipping_storecredit,
            SUM(CASE WHEN [is_marketplace] = 1 THEN ISNULL([MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS MPL_storecredit,
            SUM(CASE WHEN [is_marketplace] = 0 THEN ISNULL([MTR_COUPON_MONEY_VALUE], 0) ELSE 0 END) AS RTL_storecredit
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
        WHERE [PACKAGE_DELIVERY_DATE] < ''' + @cutoff_str + '''
            AND YEAR([DELIVERED_DATE]) > 2014
        GROUP BY
            [ID_Company],
            [voucher_code],
            [voucher_type]
    ) sd3 
        ON scv.ID_company = sd3.[ID_Company] 
        AND scv.[code] = sd3.[voucher_code]
    WHERE scv.ID_company IN (' + @id_companies_active + ')
        AND scv.created_at > ''2016-12-31'' 
        AND scv.created_at < ''' + @cutoff_str + '''
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
