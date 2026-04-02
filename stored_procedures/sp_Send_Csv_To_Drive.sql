-- =============================================
-- Stored Procedure: sp_Send_Csv_To_Drive
-- Description: Upload CSV file to Google Drive using PowerShell + Service Account
-- Parameters:
--   @file_path: Full local path of the CSV file to upload
--   @file_name: Final file name in Google Drive
--   @drive_link: Google Drive folder URL used to derive @folder_id when not provided
--   @folder_id: Explicit Google Drive folder ID override
--   @procedure_name: Source procedure name reported in the response payload
--   @row_count: Exported row count reported in the response payload
--   @export_status: Upstream export status; skips upload when set to error
--   @error_message: Upstream export error propagated when upload is skipped
--   @ps_script_path: PowerShell uploader script path
--   @service_account_json_path: Service account credential file for Google Drive API
-- Returns: Upload status, Drive file identifiers, and contextual metadata
-- =============================================
CREATE OR ALTER PROCEDURE [n8n].[sp_Send_Csv_To_Drive]
    @file_path NVARCHAR(500),
    @file_name NVARCHAR(200),
    @drive_link NVARCHAR(1000) = NULL,
    @folder_id NVARCHAR(100) = NULL,
    @procedure_name NVARCHAR(255) = NULL,
    @row_count BIGINT = NULL,
    @export_status NVARCHAR(20) = 'success',
    @error_message NVARCHAR(4000) = NULL,
    @ps_script_path NVARCHAR(500) = 'C:\Scripts\Upload-ToDrive.ps1',
    @service_account_json_path NVARCHAR(500) = 'C:\Scripts\mssql-drive-export.json'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @ps_command NVARCHAR(4000)
    DECLARE @json_result NVARCHAR(MAX)
    DECLARE @gdrive_status NVARCHAR(20)
    DECLARE @gdrive_file_id NVARCHAR(200)
    DECLARE @gdrive_web_link NVARCHAR(1000)
    DECLARE @gdrive_error NVARCHAR(4000)
    DECLARE @raw_line NVARCHAR(MAX)
    DECLARE @cmd_output TABLE (
        line_no INT IDENTITY(1,1) PRIMARY KEY,
        line NVARCHAR(MAX)
    )

    -- Extract folder id from drive_link when not explicitly provided.
    IF (@folder_id IS NULL OR LTRIM(RTRIM(@folder_id)) = '') AND @drive_link IS NOT NULL
    BEGIN
        DECLARE @pos_folders INT = CHARINDEX('/folders/', @drive_link)
        DECLARE @pos_id INT = CHARINDEX('id=', @drive_link)

        IF @pos_folders > 0
        BEGIN
            DECLARE @folders_start INT = @pos_folders + LEN('/folders/')
            DECLARE @folders_tail NVARCHAR(400) = SUBSTRING(@drive_link, @folders_start, 400)
            DECLARE @folders_end INT = PATINDEX('%[?&#/]%', @folders_tail)
            SET @folder_id = CASE
                WHEN @folders_end > 0 THEN LEFT(@folders_tail, @folders_end - 1)
                ELSE @folders_tail
            END
        END
        ELSE IF @pos_id > 0
        BEGIN
            DECLARE @id_start INT = @pos_id + LEN('id=')
            DECLARE @id_tail NVARCHAR(400) = SUBSTRING(@drive_link, @id_start, 400)
            DECLARE @id_end INT = PATINDEX('%[&#/]%', @id_tail)
            SET @folder_id = CASE
                WHEN @id_end > 0 THEN LEFT(@id_tail, @id_end - 1)
                ELSE @id_tail
            END
        END
    END

    IF @folder_id IS NULL OR LTRIM(RTRIM(@folder_id)) = ''
    BEGIN
        SELECT
            'error' AS status,
            NULL AS file_id,
            NULL AS web_view_link,
            'Missing folder_id: provide either @folder_id or valid @drive_link' AS error_message,
            @procedure_name AS procedure_name,
            @row_count AS row_count,
            @file_name AS file_name;
        RETURN;
    END

    IF @export_status = 'error'
    BEGIN
        SELECT
            'error' AS status,
            NULL AS file_id,
            NULL AS web_view_link,
            @error_message AS error_message,
            @procedure_name AS procedure_name,
            @row_count AS row_count,
            @file_name AS file_name;
        RETURN;
    END

    SET @ps_command =
        'powershell.exe -ExecutionPolicy Bypass -NoProfile -File "' + REPLACE(@ps_script_path, '"', '""') + '" ' +
        '-FilePath "' + REPLACE(@file_path, '"', '""') + '" ' +
        '-FolderId "' + REPLACE(@folder_id, '"', '""') + '" ' +
        '-FileName "' + REPLACE(@file_name, '"', '""') + '" ' +
        '-ServiceAccountJsonPath "' + REPLACE(@service_account_json_path, '"', '""') + '" ' +
        '-DeleteAfterUpload $true'

    BEGIN TRY
        INSERT INTO @cmd_output (line)
        EXEC xp_cmdshell @ps_command

        SELECT TOP 1 @json_result = line
        FROM @cmd_output
        WHERE line IS NOT NULL AND line LIKE '{%}'
        ORDER BY line_no DESC

        IF @json_result IS NOT NULL
        BEGIN
            SELECT
                @gdrive_status = JSON_VALUE(@json_result, '$.status'),
                @gdrive_file_id = JSON_VALUE(@json_result, '$.file_id'),
                @gdrive_web_link = JSON_VALUE(@json_result, '$.web_view_link'),
                @gdrive_error = JSON_VALUE(@json_result, '$.error_message')
        END
        ELSE
        BEGIN
            SELECT TOP 1 @raw_line = line
            FROM @cmd_output
            WHERE line IS NOT NULL
            ORDER BY line_no DESC

            SET @gdrive_status = 'error'
            SET @gdrive_error = 'No JSON response from PowerShell script. Last output: ' + LEFT(COALESCE(@raw_line, ''), 3000)
        END
    END TRY
    BEGIN CATCH
        SET @gdrive_status = 'error'
        SET @gdrive_error = ERROR_MESSAGE()
    END CATCH

    SELECT
        COALESCE(@gdrive_status, 'error') AS status,
        @gdrive_file_id AS file_id,
        @gdrive_web_link AS web_view_link,
        @gdrive_error AS error_message,
        @procedure_name AS procedure_name,
        @row_count AS row_count,
        @file_name AS file_name;
END
GO
