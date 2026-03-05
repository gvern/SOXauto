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
    DECLARE @del_cmd NVARCHAR(1200)
    
    -- Pre-compute header values (sp_OAMethod doesn't accept expressions)
    DECLARE @proc_name_header NVARCHAR(255)
    DECLARE @row_count_header NVARCHAR(50)
    DECLARE @error_msg_header NVARCHAR(1000)
    
    SET @proc_name_header = COALESCE(@procedure_name, '')
    SET @row_count_header = COALESCE(CONVERT(NVARCHAR(50), @row_count), '')
    SET @error_msg_header = LEFT(COALESCE(@error_message, ''), 1000)
    
    -- Read file content if export was successful
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
            -- Update error header after catching error
            SET @error_msg_header = LEFT(COALESCE(@error_message, ''), 1000)
        END CATCH
    END
    ELSE
    BEGIN
        SET @file_content = COALESCE(@error_message, 'Export failed before file upload')
    END
    
    -- Send HTTP POST to webhook
    BEGIN TRY
        EXEC @hr = sp_OACreate 'MSXML2.ServerXMLHTTP', @http_obj OUT
        EXEC @hr = sp_OAMethod @http_obj, 'open', NULL, 'POST', @webhook_url, false
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'Content-Type', 'text/csv; charset=utf-8'
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-File-Name', @file_name
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Procedure-Name', @proc_name_header
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Export-Status', @export_status
        EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Row-Count', @row_count_header
        
        IF @error_message IS NOT NULL
            EXEC @hr = sp_OAMethod @http_obj, 'setRequestHeader', NULL, 'X-Error-Message', @error_msg_header
        
        EXEC @hr = sp_OAMethod @http_obj, 'send', NULL, @file_content
        EXEC @hr = sp_OAGetProperty @http_obj, 'status', @http_status OUT
        EXEC sp_OADestroy @http_obj
    END TRY
    BEGIN CATCH
        IF @http_obj IS NOT NULL
            EXEC sp_OADestroy @http_obj
    END CATCH
    
    -- Cleanup: delete file if upload was successful
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
