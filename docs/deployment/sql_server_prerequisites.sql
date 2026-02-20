-- SQL Server prerequisites for OPENROWSET export + webhook upload

-- 1) Enable Ad Hoc Distributed Queries (required for OPENROWSET)
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure 'Ad Hoc Distributed Queries', 1;
RECONFIGURE;

-- 2) Enable OLE Automation Procedures (required for sp_OA*)
EXEC sp_configure 'Ole Automation Procedures', 1;
RECONFIGURE;

-- 3) Verify OLEDB provider availability (must include Microsoft.ACE.OLEDB.12.0)
EXEC sp_enum_oledb_providers;

-- 4) Verify SQL Server service account write/read permissions
-- Required folder example: C:\SQLExports\
-- Also verify delete permission if local cleanup is enabled.

-- Optional quick checks
SELECT name, value_in_use
FROM sys.configurations
WHERE name IN (
    'show advanced options',
    'Ad Hoc Distributed Queries',
    'Ole Automation Procedures'
);
