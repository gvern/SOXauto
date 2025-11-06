# IPE_FILES

This folder is for the descriptive Excel files referenced by the C-PG-1 catalog (`src/core/ipe_catalog_pg1.py`).

How it works

- Each catalog item contains a `descriptor_excel` field (e.g., `IPE_FILES/IPE_07.xlsx`).
- Place the corresponding Excel file here with the exact filename specified in the catalog.
- Files are not committed here by default; add .gitignore rules as needed if these files are sensitive.

Suggested filenames

- IPE_07.xlsx — Customer balances (Ageing details)
- CR_05.xlsx — FX rates
- IPE_11.xlsx — Marketplace accrued revenues
- IPE_10.xlsx — Customer prepayments TV
- IPE_08.xlsx — TV - Voucher liabilities
- IPE_31.xlsx — PG detailed TV extraction (collection accounts)
- IPE_34.xlsx — Marketplace refund liability (MPL)
- IPE_12.xlsx — TV - Packages delivered not reconciled
- CR_04.xlsx — NAV GL balances
- DOC_PG_BALANCES.xlsx — Consolidated PG balances working file (if needed)

Notes

- The catalog is metadata-only; runners use `mssql_runner.py` to connect via Teleport.
- We can later wire runners to pick up documentation paths from the catalog for evidence packaging.
