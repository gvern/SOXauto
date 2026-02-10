-- =============================================
-- Report: PG Detailed TV Extraction (IPE_31)
-- Description: Collection accounts reconciliation - open transactions, in-progress lists, and payments
-- Parameters: {subsequent_month_start}, {excluded_countries_ipe31}, {cutoff_date}
-- Source: OMS (Cash Reconciliation tables)
-- GL Accounts: Collection partner bank accounts
-- Business Logic: Captures all open/in-progress collection items as of period end
-- =============================================

-- CTE: Packlists in waiting status (special handling)
WITH CTE AS (
    SELECT DISTINCT 
        CONCAT(p.[ID_Company], p.[OMS_Packlist_No]) AS conc
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PACKAGES] p
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS] ppa
        ON p.id_company = ppa.id_company 
        AND p.OMS_PACKLIST_No = ppa.OMS_PACKLIST_No
        AND ppa.OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
    WHERE p.OMS_Packlist_status IN ('waitingApproval')
        OR (p.OMS_Packlist_Status = 'waitingConfirmation' 
            AND ppa.OMS_PAYMENT_RECONCILED_AMOUNT IS NULL)
)

SELECT 
    a.*,
    sn.SERVICE_PROVIDER,
    cp.Type,
    cp.ERP_Name,
    comp.[Company_Country],
    CAST({cutoff_date} AS DATE) AS Closing_date,
    bankacc.[G_L Bank Account No_]
FROM (
    -- =========================================
    -- PART 1: OPEN TRANSACTIONS
    -- =========================================
    SELECT
        t1.[ID_Company],
        CASE
            WHEN t1.[Transaction_Type] IN ('Transfer to', 'Third Party Collection')
                THEN ISNULL(p1.OMS_Payment_Date, t1.created_date)
            WHEN t1.[Transaction_Type] = 'Payment - Rev'
                THEN ISNULL(p1.payment_reversal_date, t1.created_date)
            ELSE t1.Created_Date
        END AS Event_date,
        t1.[Collection_Partner] AS CP,
        t1.[Transaction_Type],
        t1.Related_Entity,
        t1.[Amount]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_TRANSACTION] t1
    LEFT JOIN CTE 
        ON CONCAT(t1.[ID_Company], t1.Transaction_List_Nr) = CTE.conc
    LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT] p1
        ON t1.Related_Entity = p1.OMS_Payment_No
        AND t1.ID_Company = p1.ID_Company
        AND (
            (t1.Transaction_Type = 'Transfer to' AND p1.OMS_Type = 'Transfer') 
            OR (t1.Transaction_Type = 'Third Party Collection' AND p1.OMS_Type = 'Payment')
            OR (t1.Transaction_Type = 'Payment - Rev' AND p1.OMS_Type = 'Payment')
        )
    WHERE t1.[Transaction_Type] NOT IN (
            'Payment', 
            'Collection Adjustment (over)', 
            'Collection Adjustment (under)', 
            'Payment Charges',
            'Reallocation From', 
            'Transfer From', 
            'Payment Charges Rev'
        )
        AND (
            CASE
                WHEN t1.[Transaction_Type] IN ('Transfer to', 'Third Party Collection')
                    THEN ISNULL(p1.OMS_Payment_Date, t1.created_date)
                WHEN t1.[Transaction_Type] = 'Payment - Rev'
                    THEN ISNULL(p1.payment_reversal_date, t1.created_date)
                ELSE t1.Created_Date
            END
        ) < CAST({subsequent_month_start} AS DATETIME)
        AND (
            t1.Transaction_List_Nr IS NULL
            OR t1.Transaction_List_Date >= CAST({subsequent_month_start} AS DATETIME)
            OR CTE.conc IS NOT NULL
        )
        AND t1.[Amount] <> 0

    UNION ALL

    -- =========================================
    -- PART 2: REALLOCATIONS
    -- =========================================
    SELECT
        [ID_Company],
        [Original_Transaction_date] AS Event_date,
        [Collection_Partner_From] AS CP,
        [Transaction_type],
        Related_Entity,
        [Amount]
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHREC_REALLOCATIONS]
    WHERE [Original_Transaction_date] < CAST({subsequent_month_start} AS DATETIME)
        AND [Reallocated_Transaction_Date] >= CAST({subsequent_month_start} AS DATETIME)

    UNION ALL

    -- =========================================
    -- PART 3: TRANSACTIONLISTS IN PROGRESS
    -- =========================================
    SELECT
        tl.ID_company,
        tl.OMS_Packlist_Created_Date AS Event_date,
        tl.[OMS_Collection_Partner_Name] AS CP,
        'Translist in progress' AS Transaction_Type,
        tl.[OMS_Packlist_No] AS Related_entity,
        (tl.OMS_Amount_Received - ISNULL(t2.applied_amount, 0)) AS Amount
    FROM (
        SELECT
            ID_Company, 
            OMS_Collection_Partner_Name, 
            OMS_Packlist_No,
            OMS_Amount_Received, 
            OMS_Packlist_Created_Date
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]
        WHERE OMS_Packlist_Created_Date < CAST({subsequent_month_start} AS DATETIME)
            AND OMS_Packlist_Status IN ('inProgress', 'closed', 'waitingConfirmation')
            AND OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
        GROUP BY 
            ID_Company, 
            OMS_Collection_Partner_Name, 
            OMS_Packlist_No, 
            OMS_Amount_Received, 
            OMS_Packlist_Created_Date
    ) tl
    LEFT JOIN (
        SELECT
            [ID_Company], 
            [OMS_Packlist_No],
            SUM(
                ISNULL([OMS_Payment_Reconciled_Amount], 0) + 
                ISNULL([OMS_Payment_Charges_Reconciled_Amount], 0)
            ) AS applied_amount
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS]
        WHERE [OMS_Payment_Date] < CAST({subsequent_month_start} AS DATETIME)
        GROUP BY [ID_Company], [OMS_Packlist_No]
    ) t2 
        ON t2.ID_Company = tl.ID_Company 
        AND t2.OMS_Packlist_No = tl.OMS_Packlist_No
    LEFT JOIN (
        SELECT 
            id_company, 
            OMS_entity_No, 
            OMS_Force_Closed
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]
        WHERE OMS_Entity_Type = 'packlist'
            AND OMS_Force_Closed = 1
            AND (
                OMS_Close_Date < CAST({subsequent_month_start} AS DATETIME) 
                OR OMS_Close_Date IS NULL
            )
    ) fc 
        ON fc.ID_Company = tl.ID_Company 
        AND fc.OMS_Entity_No = tl.OMS_Packlist_No
    WHERE (fc.OMS_Force_Closed = 0 OR fc.OMS_Force_Closed IS NULL)
        AND (tl.OMS_Amount_Received - ISNULL(t2.applied_amount, 0)) > 0

    UNION ALL

    -- =========================================
    -- PART 4: PAYMENTS/TRANSFERS IN PROGRESS
    -- =========================================
    SELECT DISTINCT
        p.[ID_Company],
        p.[OMS_Payment_Date] AS Event_date,
        p.OMS_Collection_Partner AS CP,
        p.OMS_Type AS Transaction_Type,
        p.OMS_Payment_No AS Related_entity,
        -(
            ISNULL(p.OMS_Payment_Amount, 0) + 
            ISNULL(p.OMS_Charges_Amount, 0) - 
            ISNULL(p2.applied_amount, 0)
        ) AS Amount
    FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_CASHDEPOSIT] p
    LEFT JOIN (
        SELECT DISTINCT
            p1.[ID_Company],
            p1.[OMS_Payment_No],
            SUM(
                ISNULL(p1.[OMS_Payment_Reconciled_Amount], 0) + 
                ISNULL(p1.[OMS_Payment_Charges_Reconciled_Amount], 0)
            ) AS applied_amount
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_PACKLIST_PAYMENTS] p1
        WHERE p1.[OMS_Packlist_Created_Date] < CAST({subsequent_month_start} AS DATETIME)
            AND p1.[OMS_Payment_Date] < CAST({subsequent_month_start} AS DATETIME)
            AND p1.[OMS_Payment_Status] IN ('inProgress', 'closed', 'waitingConfirmation')
            AND OMS_PAYMENT_RECONCILED_AMOUNT IS NOT NULL
        GROUP BY p1.[ID_Company], p1.[OMS_Payment_No]
    ) p2 
        ON p2.ID_Company = p.[ID_Company]
        AND p.OMS_Payment_No = p2.OMS_Payment_No
    LEFT JOIN (
        SELECT DISTINCT
            [ID_Company],
            OMS_entity_No, 
            OMS_Force_Closed
        FROM [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONADJ]
        WHERE OMS_Entity_Type <> 'packlist'
            AND (
                (
                    OMS_Force_Closed = 1 
                    AND (
                        OMS_Close_Date < CAST({subsequent_month_start} AS DATETIME) 
                        OR OMS_Close_Date IS NULL
                    )
                ) 
                OR OMS_Close_Date < CAST({subsequent_month_start} AS DATETIME)
            )
    ) fc 
        ON fc.ID_Company = p.[ID_Company]
        AND fc.OMS_Entity_No = p.OMS_Payment_No
    WHERE p.OMS_Payment_Date < CAST({subsequent_month_start} AS DATETIME)
        AND (
            ISNULL(p.OMS_Payment_Amount, 0) + 
            ISNULL(p.OMS_Charges_Amount, 0) - 
            ISNULL(p2.applied_amount, 0)
        ) > 0
        AND fc.OMS_Force_Closed IS NULL
        AND p.OMS_Payment_Status IN ('inProgress', 'closed', 'waitingConfirmation')
) a

-- Dimension joins
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_HUBS_3PL_MAPPING] sn
    ON sn.ID_COMPANY = a.[ID_Company] 
    AND sn.[NODE] = a.cp

LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_COLLECTIONPARTNERS] cp
    ON cp.ID_Company = a.ID_Company 
    AND cp.Name = a.cp

LEFT JOIN (
    SELECT * 
    FROM [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company]
    WHERE [Flg_In_Conso_Scope] = 1
) comp 
    ON a.[ID_Company] = comp.[Company_Code]

-- Bank account join
LEFT JOIN (
    SELECT DISTINCT
        CONCAT(bk.ID_company, bk.[Service Provider No_]) AS CP_Key,
        bank_acc_post.[G_L Bank Account No_]
    FROM [AIG_Nav_DW].[dbo].[Bank Accounts] bk
    LEFT JOIN [AIG_Nav_DW].[dbo].[Bank Account Posting Group] bank_acc_post
        ON bank_acc_post.[ID_Company] = bk.[ID_Company]
        AND bank_acc_post.[Code] = bk.[Bank Account Posting Group]
    WHERE (bk.[Service Provider No_] IS NOT NULL AND bk.[Service Provider No_] <> '')
        AND bank_acc_post.[G_L Bank Account No_] <> '10058'
) bankacc
    ON bankacc.CP_Key = CONCAT(a.[ID_Company], cp.ERP_Name)

-- Country exclusions
WHERE comp.Company_Country NOT IN {excluded_countries_ipe31};
