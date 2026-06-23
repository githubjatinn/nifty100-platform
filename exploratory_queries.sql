-- Query 1: Row counts for all tables
SELECT 'companies' as table_name, COUNT(*) as rows FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap;

-- Query 2: Year coverage per company (min and max year)
SELECT company_id,
       MIN(year) as first_year,
       MAX(year) as last_year,
       COUNT(DISTINCT year) as total_years
FROM profitandloss
GROUP BY company_id
ORDER BY total_years ASC;

-- Query 3: Companies with less than 10 years of data
SELECT company_id, COUNT(DISTINCT year) as years
FROM profitandloss
GROUP BY company_id
HAVING years < 10
ORDER BY years ASC;

-- Query 4: NULL check on key P&L columns
SELECT
    SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) as null_sales,
    SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) as null_net_profit,
    SUM(CASE WHEN eps IS NULL THEN 1 ELSE 0 END) as null_eps,
    SUM(CASE WHEN operating_profit IS NULL THEN 1 ELSE 0 END) as null_op_profit
FROM profitandloss;

-- Query 5: NULL check on balance sheet key columns
SELECT
    SUM(CASE WHEN total_assets IS NULL THEN 1 ELSE 0 END) as null_total_assets,
    SUM(CASE WHEN total_liabilities IS NULL THEN 1 ELSE 0 END) as null_total_liab,
    SUM(CASE WHEN borrowings IS NULL THEN 1 ELSE 0 END) as null_borrowings
FROM balancesheet;

-- Query 6: Companies with negative net profit (loss making)
SELECT company_id, year, net_profit
FROM profitandloss
WHERE net_profit < 0
ORDER BY net_profit ASC
LIMIT 20;

-- Query 7: Debt-free companies (borrowings = 0) in latest year
SELECT b.company_id, b.year, b.borrowings
FROM balancesheet b
WHERE b.borrowings = 0
AND b.year = (SELECT MAX(year) FROM balancesheet WHERE company_id = b.company_id)
ORDER BY b.company_id;

-- Query 8: Top 10 companies by sales in latest year
SELECT p.company_id, c.company_name, p.year, p.sales
FROM profitandloss p
JOIN companies c ON p.company_id = c.id
WHERE p.year = (SELECT MAX(year) FROM profitandloss WHERE company_id = p.company_id)
ORDER BY p.sales DESC
LIMIT 10;

-- Query 9: Sector distribution of companies
SELECT broad_sector, COUNT(*) as company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- Query 10: Documents coverage - companies with missing annual reports
SELECT c.id, c.company_name,
       COUNT(d.Year) as reports_available
FROM companies c
LEFT JOIN documents d ON c.id = d.company_id
GROUP BY c.id
ORDER BY reports_available ASC
LIMIT 15;