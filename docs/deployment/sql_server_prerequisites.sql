-- SQL Server prerequisites for BCP export + Google Drive upload

-- 1) Enable advanced options
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;

-- 2) Enable xp_cmdshell (required by sp_Export_Query_To_Csv_Bcp and sp_Send_Csv_To_Drive)
EXEC sp_configure 'xp_cmdshell', 1;
RECONFIGURE;

-- 3) Verify bcp availability from SQL Server host context
-- Run from OS shell on SQL Server host:
--   bcp /?
-- If bcp is not found, install SQL Server Command Line Utilities and ensure PATH includes bcp.

-- 4) Verify SQL Server service account file permissions
-- Required folder example: C:\SQLExports\
-- Service account needs write/create/delete permissions for CSV lifecycle.

-- Optional quick checks
SELECT name, value_in_use
FROM sys.configurations
WHERE name IN (
    'show advanced options',
    'xp_cmdshell'
);
