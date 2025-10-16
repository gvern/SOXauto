# config.py

# --- Configuration Générale ---
# Nom du projet GCP et de la région pour accéder aux secrets
GCP_PROJECT_ID = "votre-projet-gcp" 
GCP_REGION = "europe-west1"

# Configuration pour la destination des données (BigQuery)
BIGQUERY_DATASET = "jumia_sox_reconciliation"
BIGQUERY_RESULTS_TABLE_PREFIX = "pg01_validated_ipe"

# Configuration pour le stockage des preuves (Google Drive)
GOOGLE_DRIVE_FOLDER_ID = "id_du_dossier_google_drive"

# --- Spécifications des IPEs ---
# Chaque dictionnaire contient les métadonnées pour une extraction
IPE_CONFIGS = [
    {
        "id": "IPE_07",
        "description": "Detailed customer ledger entries",
        "secret_name": "DB_CREDENTIALS_NAV_BI",  # Nom du secret dans Secret Manager
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
            "completeness_query": """
                SELECT COUNT(*) 
                FROM ({main_query}) AS main_data
            """,
            "accuracy_positive_query": """
                SELECT COUNT(*) 
                FROM ({main_query}) AS data 
                WHERE [Entry No_] = 239726184
            """,
            "accuracy_negative_query": """
                SELECT COUNT(*) 
                FROM ({main_query_modified}) AS data 
                WHERE [Document No_] = 'NGECJGNL210601149'
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
                SELECT COUNT(*) 
                FROM ({main_query}) AS data
            """,
            "accuracy_positive_query": """
                SELECT COUNT(*) 
                FROM ({main_query}) AS data 
                WHERE [Entry No_] > 0
            """,
            "accuracy_negative_query": """
                SELECT COUNT(*) 
                FROM ({main_query}) AS data 
                WHERE [id_company] like '%USD%'
            """
        }
    },
    # Ajoutez les 11 autres configurations d'IPE ici selon vos besoins
    {
        "id": "IPE_TEMPLATE",
        "description": "Template for additional IPE configurations",
        "secret_name": "DB_CREDENTIALS_NAV_BI",
        "main_query": """
            -- Votre requête SQL principale ici
            SELECT * FROM table WHERE condition = ?
        """,
        "validation": {
            "completeness_query": """
                SELECT COUNT(*) as total_count
                FROM ({main_query}) as main_data
            """,
            "accuracy_positive_query": """
                SELECT COUNT(*) as witness_count
                FROM ({main_query}) as main_data
                WHERE condition = 'witness_value'
            """
        }
    }
]