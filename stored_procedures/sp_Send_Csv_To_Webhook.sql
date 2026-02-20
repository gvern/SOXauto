-- =============================================
-- Stored Procedure: sp_Send_Csv_To_Webhook
-- Description: Send generated CSV file content to n8n webhook
-- =============================================
CREATE OR ALTER PROCEDURE [dbo].[sp_Send_Csv_To_Webhook]
    @webhook_url NVARCHAR(1000),
    @file_path NVARCHAR(1000),
    @file_name NVARCHAR(255),
    @procedure_name NVARCHAR(255) = NULL,
    @row_count BIGINT = NULL,
    @export_status NVARCHAR(20) = 'success',
    @error_message NVARCHAR(4000) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @file_content NVARCHAR(MAX) = N''
    DECLARE @read_file_sql NVARCHAR(MAX)
    DECLARE @http_obj INT
    DECLARE @http_status INT = 0
    DECLARE @hr INT
    DECLARE @row_count_str NVARCHAR(50)
    DECLARE @del_cmd NVARCHAR(1200)

    IF @export_status = 'success'
    BEGIN
        BEGIN TRY
            SET @read_file_sql = N'
            SELECT @content_out = BulkColumn
            FROM OPENROWSET(BULK ''' + REPLACE(@file_path, '''', '''''') + ''', SINGLE_CLOB) AS src'

            EXEC sp_executesql
                @read_file_sql,
                N'@content_out NVARCHAR(MAX) OUTPUT',
                @content_out = @file_content OUTPUT
        END TRY
        BEGIN CATCH
            SET @export_status = 'error'
            SET @error_message = COALESCE(@error_message + ' | ', '') + 'Failed to read generated file: ' + ERROR_MESSAGE()
            SET @file_content = COALESCE(@error_message, 'Unknown error')
        END CATCH
    END
    ELSE
    BEGIN
        SET @file_content = COALESCE(@error_message, 'Export failed before file upload')
    END

    SET @row_count_str = COALESCE(CONVERT(NVARCHAR(50), @row_count), '')

    BEGIN TRY
        EXEC @hr = sp_OACreate 'MSXML2.ServerXMLHTTP', @http_obj OUT
        EXEC @hr = sp_OAMethod @http_obj, 'open', NULL, 'POST', @webhook_url, false
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'Content-Type', 'text/csv; charset=utf-8'
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-File-Name', @file_name
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Procedure-Name', COALESCE(@procedure_name, '')
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Export-Status', @export_status
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Row-Count', @row_count_str

        IF @error_message IS NOT NULL
            EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Error-Message', LEFT(@error_message, 1000)

        EXEC @hr = sp_OAMethod @http_obj, 'send', NULL, @file_content
        EXEC @hr = sp_OAGetProperty @http_obj, 'status', @http_status OUT
        EXEC sp_OADestroy @http_obj
    END TRY
    BEGIN CATCH
        IF @http_obj IS NOT NULL
            EXEC sp_OADestroy @http_obj
    END CATCH

    IF @export_status = 'success' AND @http_status = 200
    BEGIN
        BEGIN TRY
            SET @del_cmd = 'del /Q "' + @file_path + '"'
            EXEC xp_cmdshell @del_cmd, NO_OUTPUT
        END TRY
        BEGIN CATCH
            SET @error_message = COALESCE(@error_message + ' | ', '') + 'Cleanup failed: ' + ERROR_MESSAGE()
        END CATCH
    END
END
GO
