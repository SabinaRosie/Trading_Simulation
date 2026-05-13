import pandas as pd
import os
from datetime import datetime

# Configuration
DATA_DIR = "../stocks"
COMPARISON_OUTPUT = "portfolio_comparison_report.csv"
TRADING_LOG = "trading_simulation_10yr_final.csv"

def get_final_price(symbol, target_date_str):
    """Finds the last available price on or before the target date."""
    file_path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(file_path):
        return 0
    
    df = pd.read_csv(file_path)
    df['published_date'] = pd.to_datetime(df['published_date'])
    target_dt = pd.to_datetime(target_date_str)
    
    # Filter for data on or before target date
    past_data = df[df['published_date'] <= target_dt].sort_values('published_date', ascending=False)
    
    if past_data.empty:
        return 0
    return past_data.iloc[0]['close']

def build_comparison():
    print("Building Portfolio Comparison Report...")
    
    # Paths
    INITIAL_SUMMARY = "../investment/stock_wise_summary.csv"
    TRADING_SUMMARY = "trading_simulation_10yr_summary.csv"
    INITIAL_TRANS = "../investment/initial_investment_sabina.csv"
    
    TARGET_DATE = "Dec 30, 2025"
    DATE_STR = "Dec 30 2025"
    
    if not os.path.exists(INITIAL_SUMMARY) or not os.path.exists(TRADING_SUMMARY):
        print("Error: Summary files missing. Run simulations first.")
        return

    # 1. Load Initial Summary
    df_init_sum = pd.read_csv(INITIAL_SUMMARY)
    df_init_sum = df_init_sum[df_init_sum['Stock Name'] != 'GRAND TOTAL']
    
    # 2. Load Trading Summary
    df_trade_sum = pd.read_csv(TRADING_SUMMARY)
    df_trade_sum = df_trade_sum[df_trade_sum['Stock Name'] != 'GRAND TOTAL']
    
    # 3. Load Initial Transactions (for dates)
    df_init_trans = pd.read_csv(INITIAL_TRANS)
    
    # Final Cash for Summary (Extracted from Trading Log)
    final_cash_sim = 0
    if os.path.exists(TRADING_LOG):
        try:
            df_log = pd.read_csv(TRADING_LOG)
            # Find the last valid trade row (excluding GRAND TOTAL)
            trade_rows = df_log[df_log['Date'] != 'GRAND TOTAL']
            if not trade_rows.empty:
                last_cash_str = str(trade_rows.iloc[-1]['Cash'])
                # If cash format is "(60 + 7185 = 7245)", extract 7245
                if "=" in last_cash_str:
                    final_cash_sim = float(last_cash_str.split("=")[-1].replace(")", "").strip())
                else:
                    final_cash_sim = float(last_cash_str)
        except Exception as e:
            print(f"Warning: Could not read final cash from log ({e})")

    all_stocks = sorted(list(set(df_init_sum['Stock Name'].unique()) | set(df_trade_sum['Stock Name'].unique())))
    
    records = []
    total_init_val = 0
    total_sim_val = 0
    total_bh_val = 0
    
    for stock in all_stocks:
        # Initial Data
        init_row = df_init_sum[df_init_sum['Stock Name'] == stock]
        init_qty = init_row['Total Quantity'].iloc[0] if not init_row.empty else 0
        init_price = init_row['Avg Buy Price'].iloc[0] if not init_row.empty else 0
        init_val = init_row['Total Invested'].iloc[0] if not init_row.empty else 0
        
        # Initial Date from transactions
        trans_row = df_init_trans[df_init_trans['Stock'] == stock]
        init_date = trans_row['Buy_Date'].iloc[0] if not trans_row.empty else "-"
        
        # Simulation Data
        sim_row = df_trade_sum[df_trade_sum['Stock Name'] == stock]
        sim_qty = sim_row['Total Quantity'].iloc[0] if not sim_row.empty else 0
        
        # Final Price for Valuation
        final_price = get_final_price(stock, TARGET_DATE)
        sim_val = sim_qty * final_price # Market Value
        
        # Buy & Hold (Benchmark)
        bh_val = init_qty * final_price
        
        records.append({
            'Stock': stock,
            'Initial_Buy_Date': init_date,
            'Initial_Qty': init_qty,
            'Initial_Price': round(init_price, 2),
            'Initial_Value': round(init_val, 2),
            f'{DATE_STR} Qty': sim_qty,
            f'{DATE_STR} Price': round(final_price, 2),
            f'{DATE_STR} Value': round(sim_val, 2)
        })
        
        total_init_val += init_val
        total_sim_val += sim_val
        total_bh_val += bh_val

    comparison_df = pd.DataFrame(records)
    
    # Grand Total
    summary_row = {
        'Stock': 'TOTAL',
        'Initial_Buy_Date': '',
        'Initial_Qty': comparison_df['Initial_Qty'].sum(),
        'Initial_Price': '',
        'Initial_Value': round(total_init_val, 2),
        f'{DATE_STR} Qty': comparison_df[f'{DATE_STR} Qty'].sum(),
        f'{DATE_STR} Price': '',
        f'{DATE_STR} Value': round(total_sim_val, 2)
    }
    
    comparison_df = pd.concat([comparison_df, pd.DataFrame([summary_row])], ignore_index=True)
    comparison_df.to_csv(COMPARISON_OUTPUT, index=False)
    
    final_total_val = total_sim_val + final_cash_sim
    total_profit = final_total_val - total_init_val
    return_pct = (total_profit / total_init_val) * 100 if total_init_val > 0 else 0

    print("\n--- PORTFOLIO COMPARISON SUMMARY ---")
    print(f"Total Initial Cost:      NPR {total_init_val:,.2f}")
    print(f"Buy & Hold Final Value:  NPR {total_bh_val:,.2f}")
    print(f"Simulation Stock Value:  NPR {total_sim_val:,.2f}")
    print(f"Simulation Final Cash:   NPR {final_cash_sim:,.2f}")
    print(f"TOTAL SIMULATION VALUE:  NPR {final_total_val:,.2f}")
    print(f"Comparison report saved: {COMPARISON_OUTPUT}")

    # --- SAVE FILE: TRADING GRAND TOTALS (TXT) ---
    with open("trading_grand_totals.txt", "w", encoding='utf-8') as f:
        f.write(f"--- 10-YEAR TRADING SIMULATION TOTALS (2015-2025) ---\n")
        f.write(f"Initial Investment (2014): NPR {total_init_val:,.2f}\n")
        f.write(f"Final Portfolio Value (2025): NPR {final_total_val:,.2f}\n")
        f.write(f"  - Final Stock Value:      NPR {total_sim_val:,.2f}\n")
        f.write(f"  - Final Cash Balance:     NPR {final_cash_sim:,.2f}\n")
        f.write(f"--------------------------------------------------\n")
        f.write(f"TOTAL NET PROFIT:           NPR {total_profit:,.2f}\n")
        f.write(f"TOTAL RETURN PERCENTAGE:    {return_pct:.2f}%\n")
    print(f"Summary saved: trading_grand_totals.txt")

if __name__ == "__main__":
    build_comparison()
