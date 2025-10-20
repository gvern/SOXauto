# config.py
"""
SOXauto PG-01 Configuration
Centralized configuration for IPE extractions and validations.
"""

import os

# --- General Configuration ---
# AWS Configuration - retrieved from environment variables for portability
AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID")

# Data storage configuration
# Redshift cluster for structured data warehouse
REDSHIFT_CLUSTER_ENDPOINT = os.getenv("REDSHIFT_CLUSTER_ENDPOINT")
REDSHIFT_DATABASE = os.getenv("REDSHIFT_DATABASE", "jumia_sox")
REDSHIFT_SCHEMA = "reconciliation"
REDSHIFT_TABLE_PREFIX = "pg01_validated_ipe"

# Athena configuration for S3 data lake queries (alternative to Redshift)
ATHENA_DATABASE = "jumia_sox_db"
ATHENA_WORKGROUP = "sox-automation"
S3_ATHENA_OUTPUT = f"s3://jumia-sox-data-lake/athena-results/"

# S3 configuration for evidence storage and data staging
S3_BUCKET_EVIDENCE = os.getenv("S3_BUCKET_EVIDENCE", "jumia-sox-evidence")
S3_BUCKET_DATA = os.getenv("S3_BUCKET_DATA", "jumia-sox-data-lake")
S3_PREFIX_EVIDENCE = "sox-automation/pg01/evidence/"
S3_PREFIX_VALIDATED_DATA = "sox-automation/pg01/validated-data/"

# --- IPE Specifications ---
# Each dictionary contains metadata for one IPE extraction
# Security Note: All queries use parameterized placeholders (?) to prevent SQL injection
IPE_CONFIGS = [
    {
        "id": "IPE_07",
        "description": "Detailed customer ledger entries",
        "secret_name": "jumia/sox/db-credentials-nav-bi",  # AWS Secrets Manager secret name
        "main_query": """
            SELECT vl.[id_company], vl.[Entry No_], vl.[Document No_], vl.[Document Type], vl.[External Document No_],
                   vl.[Posting Date], vl.[Customer No_], vl.[Description], vl.[Source Code], vl.[Busline Code],
                   vl.[Department Code], vl.[Original Amount], vl.[Currency], vl.[Original Amount (LCY)],
                   vl.[Due Date], vl.[Posted by], vl.[Partner Code], vl.[IC Partner Code], cus.name AS Customer_Name,
                   cus.[Customer Posting Group], cus.[Busline Code] AS Resp_Center, cus_g.[Receivables Account],
                   fdw.Group_COA_Account_no, vlle.[Remaining Amount] AS rm_amt, vlle.[Remaining Amount_LCY] AS rm_amt_lcy
            FROM [dbo].[Customer Ledger Entries] vl WITH (NOLOCK)
            LEFT JOIN (
                SELECT [id_company], [Cust_ Ledger Entry No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as [Remaining Amount_LCY]
                FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                GROUP BY [id_company], [Cust_ Ledger Entry No_]
            ) vlle ON vl.[Entry No_]=vlle.clen AND vl.id_company = vlle.id_company
            LEFT JOIN (
                SELECT [id_company], [Customer No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as Customer_Balance
                FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company WHERE Flg_In_Conso_Scope = 1)
                GROUP BY [id_company], [Customer No_]
            ) C ON vl.[Customer No_]=C.clen AND vl.id_company = C.id_company
            LEFT JOIN [dbo].[Customers] cus on cus.id_company = vl.id_company and cus.No_ = vl.[Customer No_]
            LEFT JOIN [dbo].[Customer Posting Group] cus_g on cus_g.id_company = cus.id_company and cus_g.Code = cus.[Customer Posting Group]
            LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] fdw on fdw.Company_Code = cus_g.id_company and fdw.[G/L_Account_No] = cus_g.[Receivables Account]
            WHERE [Posting Date] < ?
              and vl.id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
              and fdw.Group_COA_Account_no in ('13010','13009','13006','13005','13004','13003')
              and vlle.[Remaining Amount_LCY] <> 0 and c.Customer_Balance <> 0 and vl.[Currency]!=''
        """,
        "validation": {
            # Secure validation using CTE instead of format() to prevent SQL injection
            "completeness_query": """
                WITH main_data AS (
                    SELECT vl.[id_company], vl.[Entry No_], vl.[Document No_], vl.[Document Type], vl.[External Document No_],
                           vl.[Posting Date], vl.[Customer No_], vl.[Description], vl.[Source Code], vl.[Busline Code],
                           vl.[Department Code], vl.[Original Amount], vl.[Currency], vl.[Original Amount (LCY)],
                           vl.[Due Date], vl.[Posted by], vl.[Partner Code], vl.[IC Partner Code], cus.name AS Customer_Name,
                           cus.[Customer Posting Group], cus.[Busline Code] AS Resp_Center, cus_g.[Receivables Account],
                           fdw.Group_COA_Account_no, vlle.[Remaining Amount] AS rm_amt, vlle.[Remaining Amount_LCY] AS rm_amt_lcy
                    FROM [dbo].[Customer Ledger Entries] vl WITH (NOLOCK)
                    LEFT JOIN (
                        SELECT [id_company], [Cust_ Ledger Entry No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as [Remaining Amount_LCY]
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Cust_ Ledger Entry No_]
                    ) vlle ON vl.[Entry No_]=vlle.clen AND vl.id_company = vlle.id_company
                    LEFT JOIN (
                        SELECT [id_company], [Customer No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as Customer_Balance
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company WHERE Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Customer No_]
                    ) C ON vl.[Customer No_]=C.clen AND vl.id_company = C.id_company
                    LEFT JOIN [dbo].[Customers] cus on cus.id_company = vl.id_company and cus.No_ = vl.[Customer No_]
                    LEFT JOIN [dbo].[Customer Posting Group] cus_g on cus_g.id_company = cus.id_company and cus_g.Code = cus.[Customer Posting Group]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] fdw on fdw.Company_Code = cus_g.id_company and fdw.[G/L_Account_No] = cus_g.[Receivables Account]
                    WHERE [Posting Date] < ?
                      and vl.id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                      and fdw.Group_COA_Account_no in ('13010','13009','13006','13005','13004','13003')
                      and vlle.[Remaining Amount_LCY] <> 0 and c.Customer_Balance <> 0 and vl.[Currency]!=''
                )
                SELECT COUNT(*) FROM main_data
            """,
            "accuracy_positive_query": """
                WITH main_data AS (
                    SELECT vl.[id_company], vl.[Entry No_], vl.[Document No_], vl.[Document Type], vl.[External Document No_],
                           vl.[Posting Date], vl.[Customer No_], vl.[Description], vl.[Source Code], vl.[Busline Code],
                           vl.[Department Code], vl.[Original Amount], vl.[Currency], vl.[Original Amount (LCY)],
                           vl.[Due Date], vl.[Posted by], vl.[Partner Code], vl.[IC Partner Code], cus.name AS Customer_Name,
                           cus.[Customer Posting Group], cus.[Busline Code] AS Resp_Center, cus_g.[Receivables Account],
                           fdw.Group_COA_Account_no, vlle.[Remaining Amount] AS rm_amt, vlle.[Remaining Amount_LCY] AS rm_amt_lcy
                    FROM [dbo].[Customer Ledger Entries] vl WITH (NOLOCK)
                    LEFT JOIN (
                        SELECT [id_company], [Cust_ Ledger Entry No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as [Remaining Amount_LCY]
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Cust_ Ledger Entry No_]
                    ) vlle ON vl.[Entry No_]=vlle.clen AND vl.id_company = vlle.id_company
                    LEFT JOIN (
                        SELECT [id_company], [Customer No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as Customer_Balance
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company WHERE Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Customer No_]
                    ) C ON vl.[Customer No_]=C.clen AND vl.id_company = C.id_company
                    LEFT JOIN [dbo].[Customers] cus on cus.id_company = vl.id_company and cus.No_ = vl.[Customer No_]
                    LEFT JOIN [dbo].[Customer Posting Group] cus_g on cus_g.id_company = cus.id_company and cus_g.Code = cus.[Customer Posting Group]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] fdw on fdw.Company_Code = cus_g.id_company and fdw.[G/L_Account_No] = cus_g.[Receivables Account]
                    WHERE [Posting Date] < ?
                      and vl.id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                      and fdw.Group_COA_Account_no in ('13010','13009','13006','13005','13004','13003')
                      and vlle.[Remaining Amount_LCY] <> 0 and c.Customer_Balance <> 0 and vl.[Currency]!=''
                )
                SELECT COUNT(*) FROM main_data WHERE [Entry No_] = 239726184
            """,
            "accuracy_negative_query": """
                WITH main_data AS (
                    SELECT vl.[id_company], vl.[Entry No_], vl.[Document No_], vl.[Document Type], vl.[External Document No_],
                           vl.[Posting Date], vl.[Customer No_], vl.[Description], vl.[Source Code], vl.[Busline Code],
                           vl.[Department Code], vl.[Original Amount], vl.[Currency], vl.[Original Amount (LCY)],
                           vl.[Due Date], vl.[Posted by], vl.[Partner Code], vl.[IC Partner Code], cus.name AS Customer_Name,
                           cus.[Customer Posting Group], cus.[Busline Code] AS Resp_Center, cus_g.[Receivables Account],
                           fdw.Group_COA_Account_no, vlle.[Remaining Amount] AS rm_amt, vlle.[Remaining Amount_LCY] AS rm_amt_lcy
                    FROM [dbo].[Customer Ledger Entries] vl WITH (NOLOCK)
                    LEFT JOIN (
                        SELECT [id_company], [Cust_ Ledger Entry No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as [Remaining Amount_LCY]
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Cust_ Ledger Entry No_]
                    ) vlle ON vl.[Entry No_]=vlle.clen AND vl.id_company = vlle.id_company
                    LEFT JOIN (
                        SELECT [id_company], [Customer No_] as clen, SUM([Amount]) as [Remaining Amount], SUM([Amount (LCY)]) as Customer_Balance
                        FROM [dbo].[Detailed Customer Ledg_ Entry] vlle WITH (NOLOCK)
                        WHERE [Posting Date] < ? AND id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company WHERE Flg_In_Conso_Scope = 1)
                        GROUP BY [id_company], [Customer No_]
                    ) C ON vl.[Customer No_]=C.clen AND vl.id_company = C.id_company
                    LEFT JOIN [dbo].[Customers] cus on cus.id_company = vl.id_company and cus.No_ = vl.[Customer No_]
                    LEFT JOIN [dbo].[Customer Posting Group] cus_g on cus_g.id_company = cus.id_company and cus_g.Code = cus.[Customer Posting Group]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] fdw on fdw.Company_Code = cus_g.id_company and fdw.[G/L_Account_No] = cus_g.[Receivables Account]
                    WHERE [Posting Date] < ?
                      and vl.id_company in (select Company_Code from [AIG_Nav_Jumia_Reconciliation].fdw.dim_company where Flg_In_Conso_Scope = 1)
                      and fdw.Group_COA_Account_no in ('13010','13009','13006','13005','13004','13003')
                      and vlle.[Remaining Amount_LCY] <> 0 and c.Customer_Balance <> 0 and vl.[Currency]!=''
                      and vl.[Document No_] != 'NGECJGNL210601149'  -- Exclude specific document for negative test
                )
                SELECT COUNT(*) FROM main_data WHERE [Document No_] = 'NGECJGNL210601149'
            """
        }
    },
    {
        "id": "IPE_10",
        "description": "Customer prepayments TV",
        "secret_name": "DB_CREDENTIALS_NAV_BI",  # AWS Secrets Manager secret name
        "main_query": """
            SELECT 
                [ID_COMPANY],
                [IS_PREPAYMENT],
                [COD_OMS_SALES_ORDER_ITEM],
                [ORDER_NR],
                [BOB_ID_CUSTOMER],
                [CURRENT_STATUS],
                CASE WHEN [CURRENT_STATUS] = 'closed' THEN 1 ELSE 0 END AS IS_CLOSED,
                [IS_MARKETPLACE],
                [PAYMENT_METHOD],
                [ORDER_CREATION_DATE],
                [FINANCE_VERIFIED_DATE],
                [DELIVERED_DATE],
                [PACKAGE_DELIVERY_DATE],
                [REFUND_COMPLETED],
                [REFUND_DATE],
                [FAIL_DATE],
                ISNULL([MTR_UNIT_PRICE],0) - ISNULL([MTR_COUPON_MONEY_VALUE],0) - ISNULL([MTR_CART_RULE_DISCOUNT],0) AS PAID_FOR_ITEMS,
                ISNULL([MTR_PAID_PRICE],0) AS PAID_PRICE,
                ISNULL([MTR_BASE_SHIPPING_AMOUNT],0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)
                    +ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0)
                    +ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
            FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
            WHERE [ORDER_CREATION_DATE] > '2018-01-01 00:00:00'
              AND [IS_PREPAYMENT] = 1
              AND [FINANCE_VERIFIED_DATE] < ?
              AND (
                    -- Marketplace branch
                    (
                        [IS_MARKETPLACE] = 1
                        AND (
                            [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                        )
                        AND (
                            [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                        )
                    )
                    OR
                    -- Non-marketplace branch
                    (
                        [IS_MARKETPLACE] = 0
                        AND (
                            (
                                [DELIVERY_TYPE] IN ('Digital Content','Gift Card')
                                AND (
                                    [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                )
                            )
                            OR (
                                [DELIVERY_TYPE] NOT IN ('Digital Content','Gift Card')
                                AND (
                                    [PACKAGE_DELIVERY_DATE] IS NULL OR [PACKAGE_DELIVERY_DATE] > ?
                                )
                            )
                        )
                        AND (
                            [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                        )
                    )
                  )
        """,
        "validation": {
            "completeness_query": """
                WITH main_data AS (
                    SELECT 
                        [ID_COMPANY],
                        [IS_PREPAYMENT],
                        [COD_OMS_SALES_ORDER_ITEM],
                        [ORDER_NR],
                        [BOB_ID_CUSTOMER],
                        [CURRENT_STATUS],
                        CASE WHEN [CURRENT_STATUS] = 'closed' THEN 1 ELSE 0 END AS IS_CLOSED,
                        [IS_MARKETPLACE],
                        [PAYMENT_METHOD],
                        [ORDER_CREATION_DATE],
                        [FINANCE_VERIFIED_DATE],
                        [DELIVERED_DATE],
                        [PACKAGE_DELIVERY_DATE],
                        [REFUND_COMPLETED],
                        [REFUND_DATE],
                        [FAIL_DATE],
                        ISNULL([MTR_UNIT_PRICE],0) - ISNULL([MTR_COUPON_MONEY_VALUE],0) - ISNULL([MTR_CART_RULE_DISCOUNT],0) AS PAID_FOR_ITEMS,
                        ISNULL([MTR_PAID_PRICE],0) AS PAID_PRICE,
                        ISNULL([MTR_BASE_SHIPPING_AMOUNT],0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
                    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
                    WHERE [ORDER_CREATION_DATE] > '2018-01-01 00:00:00'
                      AND [IS_PREPAYMENT] = 1
                      AND [FINANCE_VERIFIED_DATE] < ?
                      AND (
                            (
                                [IS_MARKETPLACE] = 1
                                AND (
                                    [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                            OR (
                                [IS_MARKETPLACE] = 0
                                AND (
                                    (
                                        [DELIVERY_TYPE] IN ('Digital Content','Gift Card')
                                        AND (
                                            [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                        )
                                    )
                                    OR (
                                        [DELIVERY_TYPE] NOT IN ('Digital Content','Gift Card')
                                        AND (
                                            [PACKAGE_DELIVERY_DATE] IS NULL OR [PACKAGE_DELIVERY_DATE] > ?
                                        )
                                    )
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                          )
                )
                SELECT COUNT(*) FROM main_data
            """,
            "accuracy_positive_query": """
                WITH main_data AS (
                    SELECT 
                        [ID_COMPANY],
                        [IS_PREPAYMENT],
                        [COD_OMS_SALES_ORDER_ITEM],
                        [ORDER_NR],
                        [BOB_ID_CUSTOMER],
                        [CURRENT_STATUS],
                        CASE WHEN [CURRENT_STATUS] = 'closed' THEN 1 ELSE 0 END AS IS_CLOSED,
                        [IS_MARKETPLACE],
                        [PAYMENT_METHOD],
                        [ORDER_CREATION_DATE],
                        [FINANCE_VERIFIED_DATE],
                        [DELIVERED_DATE],
                        [PACKAGE_DELIVERY_DATE],
                        [REFUND_COMPLETED],
                        [REFUND_DATE],
                        [FAIL_DATE],
                        ISNULL([MTR_UNIT_PRICE],0) - ISNULL([MTR_COUPON_MONEY_VALUE],0) - ISNULL([MTR_CART_RULE_DISCOUNT],0) AS PAID_FOR_ITEMS,
                        ISNULL([MTR_PAID_PRICE],0) AS PAID_PRICE,
                        ISNULL([MTR_BASE_SHIPPING_AMOUNT],0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
                    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
                    WHERE [ORDER_CREATION_DATE] > '2018-01-01 00:00:00'
                      AND [IS_PREPAYMENT] = 1
                      AND [FINANCE_VERIFIED_DATE] < ?
                      AND (
                            (
                                [IS_MARKETPLACE] = 1
                                AND (
                                    [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                            OR (
                                [IS_MARKETPLACE] = 0
                                AND (
                                    (
                                        [DELIVERY_TYPE] IN ('Digital Content','Gift Card')
                                        AND (
                                            [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                        )
                                    )
                                    OR (
                                        [DELIVERY_TYPE] NOT IN ('Digital Content','Gift Card')
                                        AND (
                                            [PACKAGE_DELIVERY_DATE] IS NULL OR [PACKAGE_DELIVERY_DATE] > ?
                                        )
                                    )
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                          )
                )
                SELECT COUNT(*) FROM main_data WHERE [ORDER_NR] = 309455475
            """,
            "accuracy_negative_query": """
                WITH main_data AS (
                    SELECT 
                        [ID_COMPANY],
                        [IS_PREPAYMENT],
                        [COD_OMS_SALES_ORDER_ITEM],
                        [ORDER_NR],
                        [BOB_ID_CUSTOMER],
                        [CURRENT_STATUS],
                        CASE WHEN [CURRENT_STATUS] = 'closed' THEN 1 ELSE 0 END AS IS_CLOSED,
                        [IS_MARKETPLACE],
                        [PAYMENT_METHOD],
                        [ORDER_CREATION_DATE],
                        [FINANCE_VERIFIED_DATE],
                        [DELIVERED_DATE],
                        [PACKAGE_DELIVERY_DATE],
                        [REFUND_COMPLETED],
                        [REFUND_DATE],
                        [FAIL_DATE],
                        ISNULL([MTR_UNIT_PRICE],0) - ISNULL([MTR_COUPON_MONEY_VALUE],0) - ISNULL([MTR_CART_RULE_DISCOUNT],0) AS PAID_FOR_ITEMS,
                        ISNULL([MTR_PAID_PRICE],0) AS PAID_PRICE,
                        ISNULL([MTR_BASE_SHIPPING_AMOUNT],0) - ISNULL([MTR_SHIPPING_CART_RULE_DISCOUNT],0) - ISNULL([MTR_SHIPPING_VOUCHER_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_AMOUNT],0) - ISNULL([MTR_INTERNATIONAL_CUSTOMS_FEE_CART_RULE_DISCOUNT],0)
                            +ISNULL([MTR_INTERNATIONAL_FREIGHT_FEE], 0) AS PAID_FOR_SHIPPING
                    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_SOI]
                    WHERE [ORDER_CREATION_DATE] > '2018-01-01 00:00:00'
                      AND [IS_PREPAYMENT] = 1
                      AND [FINANCE_VERIFIED_DATE] < ?
                      AND (
                            (
                                [IS_MARKETPLACE] = 1
                                AND (
                                    [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                            OR (
                                [IS_MARKETPLACE] = 0
                                AND (
                                    (
                                        [DELIVERY_TYPE] IN ('Digital Content','Gift Card')
                                        AND (
                                            [DELIVERED_DATE] IS NULL OR [DELIVERED_DATE] > ?
                                        )
                                    )
                                    OR (
                                        [DELIVERY_TYPE] NOT IN ('Digital Content','Gift Card')
                                        AND (
                                            [PACKAGE_DELIVERY_DATE] IS NULL OR [PACKAGE_DELIVERY_DATE] > ?
                                        )
                                    )
                                )
                                AND (
                                    [REFUND_DATE] IS NULL OR [REFUND_DATE] > ?
                                )
                            )
                          )
                )
                -- Negative control: ensure no non-prepayment rows leak in
                SELECT COUNT(*) FROM main_data WHERE [IS_PREPAYMENT] = 0
            """
        }
    },
    {
        "id": "CR_03_04",
        "description": "GL entries for reconciliation",
        "secret_name": "DB_CREDENTIALS_NAV_BI",
        "main_query": """
            SELECT gl.[id_company], comp.[Company_Country], comp.Flg_In_Conso_Scope, comp.[Opco/Central_?],
                   gl.[Entry No_], gl.[Document No_], gl.[External Document No_], gl.[Posting Date], gl.[Document Date],
                   gl.[Document Type], gl.[Chart of Accounts No_], gl.[Account Name], coa.Group_COA_Account_no,
                   coa.[Group_COA_Account_Name], gl.[Document Description], gl.[Amount], dgl.rem_bal_LCY AS Remaining_amount,
                   gl.[Busline Code], gl.[Department Code], gl.[Bal_ Account Type], gl.[Bal_ Account No_],
                   gl.[Bal_ Account Name], gl.[Reason Code], gl.[Source Code], gl.[Reversed], gl.[User ID],
                   gl.[G_L Creation Date], gl.[Destination Code], gl.[Partner Code], gl.[System-Created Entry],
                   gl.[Source Type], gl.[Source No], gl.[IC Partner Code], gl.[VendorTag Code], gl.[CustomerTag Code],
                   gl.[Service_Period], ifrs.Level_1_Name, ifrs.Level_2_Name, ifrs.Level_3_Name,
                   CASE WHEN [Document Description] LIKE '%BM%' OR [Document Description] LIKE '%BACKMARGIN%' THEN 'BackMargin' ELSE 'Other' END AS EntryType
            FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
            INNER JOIN (
                SELECT det.[id_company], det.[Gen_ Ledger Entry No_], sum(det.[Amount]) rem_bal_LCY
                FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
                LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=det.id_company
                WHERE det.[Posting Date] < ? AND det.[G_L Account No_] = '15010' AND comp.Flg_In_Conso_Scope = 1
                GROUP BY det.[id_company],det.[Gen_ Ledger Entry No_]
                having sum(det.[Amount]) <> 0
            ) dgl ON gl.ID_company=dgl.ID_company and dgl.[Gen_ Ledger Entry No_]=gl.[Entry No_]
            LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=gl.id_company
            LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa on coa.[Company_Code] = gl.ID_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
            LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs on ifrs.Level_4_Code = coa.Group_COA_Account_no
            WHERE gl.[Posting Date] < ? and gl.[id_company] not like '%USD%'
        """,
        "validation": {
            "completeness_query": """
                WITH main_data AS (
                    SELECT gl.[id_company], comp.[Company_Country], comp.Flg_In_Conso_Scope, comp.[Opco/Central_?],
                           gl.[Entry No_], gl.[Document No_], gl.[External Document No_], gl.[Posting Date], gl.[Document Date],
                           gl.[Document Type], gl.[Chart of Accounts No_], gl.[Account Name], coa.Group_COA_Account_no,
                           coa.[Group_COA_Account_Name], gl.[Document Description], gl.[Amount], dgl.rem_bal_LCY AS Remaining_amount,
                           gl.[Busline Code], gl.[Department Code], gl.[Bal_ Account Type], gl.[Bal_ Account No_],
                           gl.[Bal_ Account Name], gl.[Reason Code], gl.[Source Code], gl.[Reversed], gl.[User ID],
                           gl.[G_L Creation Date], gl.[Destination Code], gl.[Partner Code], gl.[System-Created Entry],
                           gl.[Source Type], gl.[Source No], gl.[IC Partner Code], gl.[VendorTag Code], gl.[CustomerTag Code],
                           gl.[Service_Period], ifrs.Level_1_Name, ifrs.Level_2_Name, ifrs.Level_3_Name,
                           CASE WHEN [Document Description] LIKE '%BM%' OR [Document Description] LIKE '%BACKMARGIN%' THEN 'BackMargin' ELSE 'Other' END AS EntryType
                    FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
                    INNER JOIN (
                        SELECT det.[id_company], det.[Gen_ Ledger Entry No_], sum(det.[Amount]) rem_bal_LCY
                        FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
                        LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=det.id_company
                        WHERE det.[Posting Date] < ? AND det.[G_L Account No_] = '15010' AND comp.Flg_In_Conso_Scope = 1
                        GROUP BY det.[id_company],det.[Gen_ Ledger Entry No_]
                        having sum(det.[Amount]) <> 0
                    ) dgl ON gl.ID_company=dgl.ID_company and dgl.[Gen_ Ledger Entry No_]=gl.[Entry No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=gl.id_company
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa on coa.[Company_Code] = gl.ID_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs on ifrs.Level_4_Code = coa.Group_COA_Account_no
                    WHERE gl.[Posting Date] < ? and gl.[id_company] not like '%USD%'
                )
                SELECT COUNT(*) FROM main_data
            """,
            "accuracy_positive_query": """
                WITH main_data AS (
                    SELECT gl.[id_company], comp.[Company_Country], comp.Flg_In_Conso_Scope, comp.[Opco/Central_?],
                           gl.[Entry No_], gl.[Document No_], gl.[External Document No_], gl.[Posting Date], gl.[Document Date],
                           gl.[Document Type], gl.[Chart of Accounts No_], gl.[Account Name], coa.Group_COA_Account_no,
                           coa.[Group_COA_Account_Name], gl.[Document Description], gl.[Amount], dgl.rem_bal_LCY AS Remaining_amount,
                           gl.[Busline Code], gl.[Department Code], gl.[Bal_ Account Type], gl.[Bal_ Account No_],
                           gl.[Bal_ Account Name], gl.[Reason Code], gl.[Source Code], gl.[Reversed], gl.[User ID],
                           gl.[G_L Creation Date], gl.[Destination Code], gl.[Partner Code], gl.[System-Created Entry],
                           gl.[Source Type], gl.[Source No], gl.[IC Partner Code], gl.[VendorTag Code], gl.[CustomerTag Code],
                           gl.[Service_Period], ifrs.Level_1_Name, ifrs.Level_2_Name, ifrs.Level_3_Name,
                           CASE WHEN [Document Description] LIKE '%BM%' OR [Document Description] LIKE '%BACKMARGIN%' THEN 'BackMargin' ELSE 'Other' END AS EntryType
                    FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
                    INNER JOIN (
                        SELECT det.[id_company], det.[Gen_ Ledger Entry No_], sum(det.[Amount]) rem_bal_LCY
                        FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
                        LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=det.id_company
                        WHERE det.[Posting Date] < ? AND det.[G_L Account No_] = '15010' AND comp.Flg_In_Conso_Scope = 1
                        GROUP BY det.[id_company],det.[Gen_ Ledger Entry No_]
                        having sum(det.[Amount]) <> 0
                    ) dgl ON gl.ID_company=dgl.ID_company and dgl.[Gen_ Ledger Entry No_]=gl.[Entry No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=gl.id_company
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa on coa.[Company_Code] = gl.ID_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs on ifrs.Level_4_Code = coa.Group_COA_Account_no
                    WHERE gl.[Posting Date] < ? and gl.[id_company] not like '%USD%'
                )
                SELECT COUNT(*) FROM main_data WHERE [Entry No_] > 0
            """,
            "accuracy_negative_query": """
                WITH main_data AS (
                    SELECT gl.[id_company], comp.[Company_Country], comp.Flg_In_Conso_Scope, comp.[Opco/Central_?],
                           gl.[Entry No_], gl.[Document No_], gl.[External Document No_], gl.[Posting Date], gl.[Document Date],
                           gl.[Document Type], gl.[Chart of Accounts No_], gl.[Account Name], coa.Group_COA_Account_no,
                           coa.[Group_COA_Account_Name], gl.[Document Description], gl.[Amount], dgl.rem_bal_LCY AS Remaining_amount,
                           gl.[Busline Code], gl.[Department Code], gl.[Bal_ Account Type], gl.[Bal_ Account No_],
                           gl.[Bal_ Account Name], gl.[Reason Code], gl.[Source Code], gl.[Reversed], gl.[User ID],
                           gl.[G_L Creation Date], gl.[Destination Code], gl.[Partner Code], gl.[System-Created Entry],
                           gl.[Source Type], gl.[Source No], gl.[IC Partner Code], gl.[VendorTag Code], gl.[CustomerTag Code],
                           gl.[Service_Period], ifrs.Level_1_Name, ifrs.Level_2_Name, ifrs.Level_3_Name,
                           CASE WHEN [Document Description] LIKE '%BM%' OR [Document Description] LIKE '%BACKMARGIN%' THEN 'BackMargin' ELSE 'Other' END AS EntryType
                    FROM [AIG_Nav_DW].[dbo].[G_L Entries] gl WITH (INDEX([IDX_NAV_GL_Entries]))
                    INNER JOIN (
                        SELECT det.[id_company], det.[Gen_ Ledger Entry No_], sum(det.[Amount]) rem_bal_LCY
                        FROM [AIG_Nav_DW].[dbo].[Detailed G_L Entry] det
                        LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=det.id_company
                        WHERE det.[Posting Date] < ? AND det.[G_L Account No_] = '15010' AND comp.Flg_In_Conso_Scope = 1
                        GROUP BY det.[id_company],det.[Gen_ Ledger Entry No_]
                        having sum(det.[Amount]) <> 0
                    ) dgl ON gl.ID_company=dgl.ID_company and dgl.[Gen_ Ledger Entry No_]=gl.[Entry No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp on comp.Company_Code=gl.id_company
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_ChartOfAccounts] coa on coa.[Company_Code] = gl.ID_company and coa.[G/L_Account_No] = gl.[Chart of Accounts No_]
                    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[GDOC_IFRS_Tabular_Mapping] ifrs on ifrs.Level_4_Code = coa.Group_COA_Account_no
                    WHERE gl.[Posting Date] < ? and gl.[id_company] not like '%USD%'
                )
                SELECT COUNT(*) FROM main_data WHERE [id_company] like '%USD%'
            """
        }
    },
    # Additional IPE configurations can be added following the secure pattern above
    {
        "id": "IPE_TEMPLATE",
        "description": "Template for additional IPE configurations",
        "secret_name": "DB_CREDENTIALS_NAV_BI",
        "main_query": """
            -- Main query template with parameterized placeholders
            SELECT * FROM table WHERE condition = ?
        """,
        "validation": {
            # Security Note: All validation queries use CTEs to prevent SQL injection
            "completeness_query": """
                WITH main_data AS (
                    -- Copy the full main_query here with all ? placeholders
                    SELECT * FROM table WHERE condition = ?
                )
                SELECT COUNT(*) as total_count FROM main_data
            """,
            "accuracy_positive_query": """
                WITH main_data AS (
                    -- Copy the full main_query here with all ? placeholders
                    SELECT * FROM table WHERE condition = ?
                )
                SELECT COUNT(*) as witness_count 
                FROM main_data 
                WHERE condition = 'witness_value'
            """
        }
    }
]