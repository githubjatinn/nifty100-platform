import sqlite3
import pandas as pd
import random

conn = sqlite3.connect('data/nifty100.db')

# Year coverage per company
df = pd.read_sql("""
    SELECT company_id, COUNT(DISTINCT year) as years
    FROM profitandloss
    GROUP BY company_id
    ORDER BY years ASC
""", conn)

print("=== Companies with < 5 years ===")
print(df[df['years'] < 5].to_string())

print("\n=== 5 Random Companies - Year Coverage ===")
sample = random.sample(list(df['company_id']), 5)
for ticker in sample:
    years = pd.read_sql(f"""
        SELECT year FROM profitandloss
        WHERE company_id = '{ticker}'
        ORDER BY year
    """, conn)
    print(f"\n{ticker}: {list(years['year'])}")

conn.close()