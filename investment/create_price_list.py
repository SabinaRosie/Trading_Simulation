import os
import csv

stocks_dir = r'c:\Users\PS\Desktop\Sabina_Trading\stocks'
output_file = 'initial_stock_prices_15_shares.csv'
files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('.csv')])

with open(output_file, 'w', newline='', encoding='utf-8') as fout:
    writer = csv.writer(fout)
    writer.writerow(['Stock', 'Starting Price (2013)', 'Cost for 15 Shares'])
    
    for f in files:
        symbol = f.replace('.csv', '')
        filepath = os.path.join(stocks_dir, f)
        with open(filepath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Find the first entry in 2013 or 2014
                if row['published_date'].startswith('2013') or row['published_date'].startswith('2014'):
                    price = float(row['close'])
                    cost = price * 15
                    writer.writerow([symbol, f'{price:.2f}', f'{cost:.2f}'])
                    break

print(f"Successfully created {output_file}")
