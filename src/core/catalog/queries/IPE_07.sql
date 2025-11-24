SET NOCOUNT ON;

IF OBJECT_ID('tempdb..##temp') IS NOT NULL DROP TABLE ##temp;
IF OBJECT_ID('tempdb..##temp2') IS NOT NULL DROP TABLE ##temp2;

select * into ##temp from (
    SELECT [id_company]
    ,[Customer No_]
    ,sum([Amount (LCY)]) rem_bal_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
    WHERE [Posting Date] <= '{cutoff_date}'
    GROUP BY [id_company],[Customer No_]
    Having sum([Amount (LCY)]) <> 0
) a;

CREATE NONCLUSTERED INDEX IDX_Temp
ON ##temp ([ID_company],[Customer No_])
INCLUDE (rem_bal_LCY);

select * into ##temp2 from (
    SELECT [id_company]
    ,[Cust_ Ledger Entry No_]
    ,sum([Amount (LCY)]) rem_amt_LCY
    FROM [AIG_Nav_DW].[dbo].[Detailed Customer Ledg_ Entry]
    WHERE [Posting Date] <= '{cutoff_date}'
    GROUP BY [id_company],[Cust_ Ledger Entry No_]
    Having sum([Amount (LCY)]) <> 0
) b;

CREATE NONCLUSTERED INDEX IDX_Temp2
ON ##temp2 ([ID_company],[Cust_ Ledger Entry No_])
INCLUDE (rem_amt_LCY);

SELECT cle.[id_company]
,comp.Company_Country
,comp.[Opco/Central_?]
,cle.[Entry No_]
,cle.[GL Entry No_]
,cle.[Document No_]
,cle.[Document Type]
,cle.[External Document No_]
,cle.[Posting Date]
,cle.[Customer No_]
,cst.[Name] 'Customer Name'
,cst.[Busline Code] 'Customer Busline'
,cst.[Automatically integrated]
,cst.[Customer Posting Group] currentpostinggroup
,cst.[Stream],cle.[Customer Posting Group]
,cle.[Description]
,cle.[Source Code]
,cle.[Reason Code]
,cle.[Busline Code]
,bl.[Busline_Vertical_Name_1]
,bl.[Busline_Vertical_Name_2]
,bl.[Busline_Vertical_Name_3]
,cle.[Department Code]
,cle.[Original Amount]
,cle.[Currency]
,cle.[Original Amount (LCY)]
,dcle_2.rem_amt_LCY
,cle.[Open],cle.[Due Date]
,cle.[Posted by]
,cle.[Destination Code]
,cle.[Partner Code]
,cle.[IC Partner Code]
,CASE WHEN EOMONTH(cle.[Due Date]) < EOMONTH(GETDATE()) THEN 'Credit'
    WHEN EOMONTH(cle.[Due Date]) > EOMONTH(GETDATE()) THEN 'Debit'
    ELSE 'Due Month' END 'Debit_Credit_DueMonth'
FROM [AIG_Nav_DW].[dbo].[Customer Ledger Entries] cle
INNER JOIN ##temp dcle
    on cle.ID_company=dcle.ID_company and cle.[Customer No_]=dcle.[Customer No_]
INNER JOIN ##temp2 dcle_2
    on cle.ID_company=dcle_2.ID_company and cle.[Entry No_]=dcle_2.[Cust_ Ledger Entry No_]
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
    on comp.Company_Code=cle.id_company
LEFT JOIN [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Busline] bl
    on bl.[Company_Code]=cle.id_company and bl.[Busline_Code]=cle.[Busline Code]
LEFT JOIN [AIG_Nav_DW].[dbo].[Customers] cst
    on cst.[id_company]=cle.id_company and cst.[No_]=cle.[Customer No_]
WHERE cle.[Posting Date] <= '{cutoff_date}'
and cle.[Customer Posting Group] in (
    'LOAN-REC-NAT', 'B2B-NG-NAT','B2C-NG-NAT','B2C-NG-INT','NTR-NG-NAT',
    'B2B-NG-INT','NTR-NG-INT','UE','INL','EXPORT','EU','NATIONAL', 
    'OM','NAT','AUS','EXCB2B-NAT','EMP-NAT'
)
and comp.Flg_In_Conso_Scope = 1;

DROP TABLE ##temp;
DROP TABLE ##temp2;
