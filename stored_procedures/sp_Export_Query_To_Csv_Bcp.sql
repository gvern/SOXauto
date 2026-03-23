-- =============================================
-- Stored Procedure: sp_Export_Query_To_Csv_Bcp
-- Description: Export dynamic query results to CSV using bcp (queryout mode, no temp tables)
-- =============================================
CREATE OR ALTER PROCEDURE [n8n].[sp_Export_Query_To_Csv_Bcp]
    @query NVARCHAR(MAX),
    @output_file_path NVARCHAR(500)
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @bcp_command NVARCHAR(MAX)
    DECLARE @server_name NVARCHAR(255)
    DECLARE @xp_rc INT
    DECLARE @cmd_output TABLE (
        line_no INT IDENTITY(1,1) PRIMARY KEY,
        line NVARCHAR(4000)
    )
    DECLARE @error_line NVARCHAR(4000)
    DECLARE @throw_message NVARCHAR(2048)

    IF @query IS NULL OR LTRIM(RTRIM(@query)) = ''
    BEGIN
        THROW 50001, 'BCP export query is empty.', 1;
    END

    IF @output_file_path IS NULL OR LTRIM(RTRIM(@output_file_path)) = ''
    BEGIN
        THROW 50002, 'BCP output file path is empty.', 1;
    END

    SET @server_name = COALESCE(CAST(SERVERPROPERTY('ServerName') AS NVARCHAR(255)), @@SERVERNAME)

    BEGIN TRY
        -- Use BCP queryout directly with the query (no temp tables)
        SET @bcp_command =
            'bcp "' + REPLACE(@query, '"', '""') + '" queryout "' + REPLACE(@output_file_path, '"', '""') + '" ' +
            '-c -t"," -r"\n" -T -S "' + REPLACE(@server_name, '"', '""') + '"'

        INSERT INTO @cmd_output (line)
        EXEC @xp_rc = xp_cmdshell @bcp_command

        IF ISNULL(@xp_rc, 1) <> 0
        BEGIN
            THROW 50003, 'BCP export failed: xp_cmdshell returned a non-zero exit code.', 1;
        END

        SELECT TOP 1 @error_line = line
        FROM @cmd_output
        WHERE line IS NOT NULL
          AND (
              line LIKE '%Error = %'
              OR line LIKE '%SQLState = %'
              OR line LIKE '%Unable to open BCP host data-file%'
              OR line LIKE '%BCP copy out failed%'
          )
        ORDER BY line_no DESC

        IF @error_line IS NOT NULL
        BEGIN
            SET @throw_message = 'BCP export failed: ' + LEFT(@error_line, 1800)
            THROW 50003, @throw_message, 1;
        END
    END TRY
    BEGIN CATCH
        THROW;
    END CATCH
END
GO