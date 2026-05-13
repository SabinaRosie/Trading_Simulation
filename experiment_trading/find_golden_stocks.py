import pandas as pd
import os

DATA_DIR = "../stocks"
START_DATE = "2015-01-01"
END_DATE = "2025-12-30"

def analyze_golden_stocks():
    results = []
    
    for file in os.listdir(DATA_DIR):
        if file.endswith(".csv"):
            stock = file.replace(".csv", "")
            df = pd.read_csv(os.path.join(DATA_DIR, file))
            df['published_date'] = pd.to_datetime(df['published_date'])
            df = df.sort_values('published_date')
            
            # Get Start Price
            start_row = df[df['published_date'] >= START_DATE]
            if start_row.empty: continue
            start_price = start_row.iloc[0]['close']
            
            # Get End Price
            end_row = df[df['published_date'] <= END_DATE]
            if end_row.empty: continue
            end_price = end_row.iloc[-1]['close']
            
            # Get Max Price (The Peak)
            peak_price = df[(df['published_date'] >= START_DATE) & (df['published_date'] <= END_DATE)]['close'].max()
            
            growth_pct = ((end_price - start_price) / start_price) * 100
            peak_pct = ((peak_price - start_price) / start_price) * 100
            
            results.append({
                'Stock': stock,
                'Start Price (2015)': round(start_price, 2),
                'End Price (2025)': round(end_price, 2),
                'Peak Price': round(peak_price, 2),
                'Total Growth %': round(growth_pct, 2),
                'Max Potential %': round(peak_pct, 2)
            })
            
    df_results = pd.DataFrame(results).sort_values('Total Growth %', ascending=False)
    df_results.to_csv("golden_stocks_ranking.csv", index=False)
    
    print("\n--- TOP 10 GOLDEN STOCKS (BY 10-YEAR GROWTH) ---")
    print(df_results.head(10).to_string(index=False))
    
    print("\nRanking saved to: trading/golden_stocks_ranking.csv")

if __name__ == "__main__":
    analyze_golden_stocks()
