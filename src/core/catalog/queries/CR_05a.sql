SELECT TOP (1) [Currency Code],year([Starting Date]) year,month([Starting Date]) month,[Relational Exch_ Rate Amount]
FROM [D365BC14_DZ].[dbo].[Jade DZ$Currency Exchange Rate]
WHERE [Currency Code] = 'USD'
and [Starting Date] = '{fx_date}'
