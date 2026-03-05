-- =============================================
-- Stored Procedure: sp_Extract_CR_03
-- Description: Extract NAV GL Entries data to CSV file
-- Purpose: General ledger entries for variance analysis
-- Parameters: 
--   @subsequent_month_start: Start of next month (YYYY-MM-DD HH:MM:SS)
--   @gl_accounts_cr_03: Comma-separated list of GL accounts (e.g., '15010')
--   @output_path: Directory for output file (default: C:\SQLExports\)
-- Returns: File path, filename, and row count
-- Source: NAV Data Warehouse
-- GL Account: 15010
-- =============================================
CREATE PROCEDURE [n8n].[sp_Extract_CR_03]
    @subsequent_month_start DATETIME,
    @gl_accounts_cr_03 NVARCHAR(500),
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
    DECLARE @subsequent_str NVARCHAR(30)
    DECLARE @procedure_name NVARCHAR(255)
    
    -- Store procedure name early 
    SET @procedure_name = 'n8n.sp_Extract_CR_03'
    
    -- Generate unique filename with timestamp
    SET @filename = 'CR_03_' + 
                    FORMAT(GETDATE(), 'yyyyMMdd_HHmmss') + '.csv'
    SET @full_path = @output_path + @filename
    
    -- Convert parameter to string for query
    SET @subsequent_str = CONVERT(NVARCHAR(30), @subsequent_month_start, 120)
    
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
    FROM [AIG_Nav_DW].[n8n].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
    INNER JOIN (
        SELECT
            det.[id_company],
            det.[Gen_ Ledger Entry No_],
            SUM(det.[Amount]) AS rem_bal_LCY
        FROM [AIG_Nav_DW].[n8n].[Detailed G_L Entry] det
        LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
            ON comp.Company_Code = det.id_company
        WHERE det.[Posting Date] < CAST(''' + @subsequent_str + ''' AS DATETIME)
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
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[n8n].[GDOC_IFRS_Tabular_Mapping] ifrs
        ON ifrs.Level_4_Code = coa.Group_COA_Account_no
    WHERE gl.[Posting Date] < CAST(''' + @subsequent_str + ''' AS DATETIME)
        AND gl.[id_company] NOT LIKE ''%USD%''
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

    -- Call webhook with stored procedure name variable
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
