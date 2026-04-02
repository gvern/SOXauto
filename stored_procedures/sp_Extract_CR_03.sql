-- =============================================
-- Stored Procedure: sp_Extract_CR_03
-- Description: Extract NAV GL Entries data to CSV file
-- Purpose: General ledger entries for variance analysis
-- Parameters: 
--   @year_start: Start of year range (YYYY-MM-DD)
--   @year_end: End of year range (YYYY-MM-DD)
--   @gl_accounts_cr_03: Comma-separated list of GL accounts (e.g., '15010')
--   @output_path: Directory for output file (default: D:\INTFIN-Data\SOC_n8n)
--   @drive_link: Google Drive folder link for upload target
-- Returns: File path, filename, and row count
-- Source: NAV Data Warehouse
-- GL Account: 15010
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_CR_03]
    @year_start DATE,
    @year_end DATE,
    @gl_accounts_cr_03 NVARCHAR(500),
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
    DECLARE @year_start_str NVARCHAR(10)
    DECLARE @year_end_str NVARCHAR(10)
    DECLARE @procedure_name NVARCHAR(255)
    DECLARE @temp_table NVARCHAR(128)
    DECLARE @select_into_sql NVARCHAR(MAX)
    DECLARE @bcp_command NVARCHAR(MAX)
    DECLARE @bcp_return_code INT
    
    -- Store procedure name early 
    SET @procedure_name = 'n8n.sp_Extract_CR_03'
    
    -- Generate unique filename with timestamp
    SET @filename = 'CR_03_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @output_path = CASE 
        WHEN RIGHT(@output_path, 1) IN ('\\', '/') THEN @output_path
        ELSE @output_path + '\\'
    END
    SET @full_path = @output_path + @filename
    
    -- Convert parameters to strings for query
    SET @year_start_str = CONVERT(NVARCHAR(10), @year_start, 120)
    SET @year_end_str = CONVERT(NVARCHAR(10), @year_end, 120)
    
    -- Build dynamic query with parameters
    SET @query = '
    SELECT
        gl.[id_company],
        comp.[Company_Country],
        comp.Flg_In_Conso_Scope,
        comp.[Opco/Central_?],
        gl.[Entry No_],
        gl.[Document No_],
        gl.[External Document No_],
        gl.[Voucher No_],
        gl.[Posting Date],
        gl.[Document Date],
        gl.[Document Type],
        gl.[Chart of Accounts No_],
        gl.[Account Name],
        coa.Group_COA_Account_no,
        coa.[Group_COA_Account_Name],
        gl.[Document Description],
        gl.[Amount],
        dgl.rem_bal_LCY AS Remaining_amount,
        gl.[Busline Code],
        gl.[Department Code],
        gl.[Bal_ Account Type],
        gl.[Bal_ Account No_],
        gl.[Bal_ Account Name],
        gl.[Reason Code],
        gl.[Source Code],
        gl.[Reversed],
        gl.[User ID],
        gl.[G_L Creation Date],
        gl.[Destination Code],
        gl.[Partner Code],
        gl.[System-Created Entry],
        gl.[Source Type],
        gl.[Source No],
        gl.[IC Partner Code],
        gl.[VendorTag Code],
        gl.[CustomerTag Code],
        gl.[Service_Period],
        ifrs.Level_1_Name,
        ifrs.Level_2_Name,
        ifrs.Level_3_Name,
        CASE
            WHEN gl.[Document Description] LIKE ''%BM%'' 
                OR gl.[Document Description] LIKE ''%BACKMARGIN%'' 
            THEN ''BackMargin''
            ELSE ''Other''
        END AS EntryType
    FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
    INNER JOIN (
        SELECT
            det.[id_company],
            det.[Gen_ Ledger Entry No_],
            SUM(det.[Amount]) AS rem_bal_LCY
        FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
        LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
            ON comp.Company_Code = det.id_company
        WHERE det.[Posting Date] BETWEEN ''' + @year_start_str + ''' AND ''' + @year_end_str + '''
            AND det.[G_L Account No_] IN (' + @gl_accounts_cr_03 + ')
            AND comp.Flg_In_Conso_Scope = 1
        GROUP BY det.[id_company], det.[Gen_ Ledger Entry No_]
        HAVING SUM(det.[Amount]) <> 0
    ) dgl
        ON gl.id_company = dgl.id_company 
        AND dgl.[Gen_ Ledger Entry No_] = gl.[Entry No_]
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
        ON comp.Company_Code = gl.id_company
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa
        ON coa.[Company_Code] = gl.id_company 
        AND coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs
        ON ifrs.Level_4_Code = coa.Group_COA_Account_no
    WHERE gl.[Posting Date] BETWEEN ''' + @year_start_str + ''' AND ''' + @year_end_str + '''
        AND gl.[id_company] NOT LIKE ''%USD%''
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

    -- Call Drive upload procedure with stored procedure name variable
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
