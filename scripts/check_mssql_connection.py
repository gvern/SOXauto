#!/usr/bin/env python3
"""
Quick SQL Server connectivity check.

- Uses DB_CONNECTION_STRING if present
- Otherwise builds from MSSQL_* env vars
- Prints basic server info on success; helpful diagnostics on failure

Example env:
  export DB_CONNECTION_STRING="Driver={ODBC Driver 18 for SQL Server};Server=fin-sql.jumia.local;Database=NAV_BI;UID=user;PWD=pass;TrustServerCertificate=yes;"

macOS prerequisites:
  - brew install unixodbc
  - Install Microsoft ODBC Driver 18 for SQL Server (pkg) from docs.microsoft.com

Docker image already includes msodbcsql18.
"""
import os
import sys
import pyodbc


def build_connection_string() -> str:
    cs = os.getenv("DB_CONNECTION_STRING")
    if cs:
        return cs
    # Support DSN-based connections if provided
    dsn = os.getenv("MSSQL_DSN")
    if dsn:
        user = os.getenv("MSSQL_USER")
        password = os.getenv("MSSQL_PASSWORD")
        if not (user and password):
            raise RuntimeError(
                "MSSQL_DSN set but MSSQL_USER/MSSQL_PASSWORD missing. Set credentials or use DB_CONNECTION_STRING."
            )
        # TrustServerCertificate keeps parity with server-based connection defaults
        return f"DSN={dsn};UID={user};PWD={password};TrustServerCertificate=yes;"
    driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    user = os.getenv("MSSQL_USER")
    password = os.getenv("MSSQL_PASSWORD")
    if not (server and database and user and password):
        raise RuntimeError(
            "Missing DB connection details. Set DB_CONNECTION_STRING or MSSQL_SERVER, MSSQL_DATABASE, MSSQL_USER, MSSQL_PASSWORD"
        )
    return (
        f"Driver={{{ {driver} }}};Server={server};Database={database};"
        f"UID={user};PWD={password};TrustServerCertificate=yes;"
    )


def main() -> int:
    try:
        cs = build_connection_string()
    except Exception as e:
        print(f"[ERROR] {e}")
        print("Hint: export DB_CONNECTION_STRING or the MSSQL_* env vars")
        return 2

    print("Attempting to connect to SQL Server...")
    try:
        with pyodbc.connect(cs, timeout=10) as conn:
            cur = conn.cursor()
            cur.execute("SELECT @@VERSION")
            version = cur.fetchone()[0]
            print("✅ Connection successful")
            print("Server version:\n" + str(version))
            return 0
    except pyodbc.InterfaceError as e:
        print(f"❌ InterfaceError: {e}")
        print("- Ensure the ODBC driver is installed (msodbcsql18) and the Driver name matches.")
        print("- On macOS, use the Microsoft pkg installer for ODBC Driver 18, or run inside Docker.")
        return 3
    except pyodbc.Error as e:
        print(f"❌ pyodbc.Error: {e}")
        print("- Check server, credentials, firewall, and TLS settings.")
        print("- If using self-signed cert in dev, include TrustServerCertificate=yes in the connection string.")
        return 4
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        return 5


if __name__ == "__main__":
    sys.exit(main())
