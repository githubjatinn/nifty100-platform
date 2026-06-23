import sqlite3
import pandas as pd

conn = sqlite3.connect('data/nifty100.db')

queries = {
    "Q1 Row Counts": "SELECT 'companies' as table_name, COUNT(*) as rows FROM companies UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow UNION ALL SELECT 'sectors', COUNT(*) FROM sectors UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap",
    "Q3 Companies < 10 years": "SELECT company_id, COUNT(DISTINCT year) as years FROM profitandloss GROUP BY company_id HAVING years < 10 ORDER BY years ASC",
    "Q4 NULL check PL": "SELECT SUM(CASE WHEN sales IS NULL THEN 1 ELSE 0 END) as null_sales, SUM(CASE WHEN net_profit IS NULL THEN 1 ELSE 0 END) as null_net_profit, SUM(CASE WHEN eps IS NULL THEN 1 ELSE 0 END) as null_eps FROM profitandloss",
    "Q6 Loss Making": "SELECT company_id, year, net_profit FROM profitandloss WHERE net_profit < 0 ORDER BY net_profit ASC LIMIT 10",
    "Q8 Top 10 by Sales": "SELECT p.company_id, p.year, p.sales FROM profitandloss p WHERE p.year = (SELECT MAX(year) FROM profitandloss WHERE company_id = p.company_id) ORDER BY p.sales DESC LIMIT 10",
    "Q9 Sector Distribution": "SELECT broad_sector, COUNT(*) as company_count FROM sectors GROUP BY broad_sector ORDER BY company_count DESC",
}

for name, sql in queries.items():
    print(f"\n=== {name} ===")
    print(pd.read_sql(sql, conn).to_string())

conn.close()