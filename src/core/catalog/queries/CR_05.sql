SELECT
    comp.[Company_Code],
    comp.[Company_Name],
    comp.[Opco/Central_?],
    comp.[Company_Country],
    comp.[Is_Active?],
    fx.[rate_type],
    fx.[year],
    fx.[cod_month],
    case
        when c.[Country_Name] in ('United States of America') or (c.[Country_Name] in ('Germany') and right(comp.[Company_Code],4)='_USD')
        then 1
        else fx.rate
    end FX_rate,
    c.[Country_Name]
FROM [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Company] comp
left join (
    Select [country_code],[rate_type],[year],[cod_month],[rate]
    from [AIG_Nav_Jumia_Reconciliation].[dbo].[RPT_FX_RATES]
    where [year] = {year}
    and [cod_month] = {month}
    and [rate_type] = 'Closing'
    and [base_currency] = 'USD'
    and country <> 'United arab emirates (the)'
) fx
    on fx.country_code = comp.Company_Country
left join [AIG_Nav_Jumia_Reconciliation].[fdw].[Dim_Country] c
    on comp.[Company_Country] = c.[Country_Code]
