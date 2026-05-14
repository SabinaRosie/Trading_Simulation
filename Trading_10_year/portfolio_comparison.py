import pandas as pd
import os
from datetime import datetime

# Configuration
DATA_DIR = "../stocks"
COMPARISON_OUTPUT = "portfolio_comparison_report.csv"
TRADING_LOG = "trading_simulation_10yr_output.csv"

def get_final_price(symbol, target_date_str):
    """Finds the last available price on or before the target date."""
    file_path = os.path.join(DATA_DIR, f"{symbol}.csv")
    if not os.path.exists(file_path):
        return 0
    
    try:
        df = pd.read_csv(file_path)
        df['published_date'] = pd.to_datetime(df['published_date'])
        target_dt = pd.to_datetime(target_date_str)
        
        past_data = df[df['published_date'] <= target_dt].sort_values('published_date', ascending=False)
        
        if past_data.empty:
            return 0
        return past_data.iloc[0]['close']
    except:
        return 0

def get_current_holdings(log_path):
    """Calculates final holdings by summing BUYS and subtracting SELLS from the log."""
    if not os.path.exists(log_path):
        return {}
    
    try:
        df = pd.read_csv(log_path)
        # Filter out GRAND TOTAL row
        df = df[df['Date'] != 'GRAND TOTAL']
        
        holdings = {}
        for _, row in df.iterrows():
            stock = row['Stock Name']
            action = row['Action']
            qty = row['Quantity']
            
            if action == 'BUY':
                holdings[stock] = holdings.get(stock, 0) + qty
            elif action == 'SELL':
                holdings[stock] = holdings.get(stock, 0) - qty
                
        return {s: q for s, q in holdings.items() if q > 0}
    except Exception as e:
        print(f"Error reading log: {e}")
        return {}

def build_comparison():
    print("Building Portfolio Comparison Report (Dec 2025)...")
    
    INITIAL_INVESTMENT_FILE = "../investment/initial_investment_sabina.csv"
    TARGET_DATE = "Dec 31, 2025" 
    DATE_STR = "Dec 31 2025"
    
    if not os.path.exists(INITIAL_INVESTMENT_FILE) or not os.path.exists(TRADING_LOG):
        print("Error: Required files missing. Run simulation first.")
        return

    # 1. Load Initial Investment
    df_init = pd.read_csv(INITIAL_INVESTMENT_FILE)
    df_init = df_init[df_init['Stock'] != 'GRAND TOTAL']
    
    # Aggregate initial holdings (sum quantities per stock)
    init_holdings = df_init.groupby('Stock').agg({
        'Quantity': 'sum',
        'Invested_Amount': 'sum',
        'Buy_Price': 'mean', # Approximation for display
        'Buy_Date': 'first'
    }).reset_index()
    
    # 2. Get Final Holdings from Log
    final_holdings = get_current_holdings(TRADING_LOG)
    
    # 3. Final Cash for Summary
    final_cash_sim = 0
    if os.path.exists(TRADING_LOG):
        try:
            df_log = pd.read_csv(TRADING_LOG)
            trade_rows = df_log[df_log['Date'] != 'GRAND TOTAL']
            if not trade_rows.empty:
                last_cash_str = str(trade_rows.iloc[-1]['Cash In Hand'])
                if "=" in last_cash_str:
                    final_cash_sim = float(last_cash_str.split("=")[-1].replace(")", "").strip())
                else:
                    final_cash_sim = float(last_cash_str)
        except Exception as e:
            print(f"Warning: Could not read final cash from log ({e})")

    # Combine all stocks
    all_stocks = sorted(list(set(init_holdings['Stock'].unique()) | set(final_holdings.keys())))
    
    records = []
    total_init_val = 0
    total_sim_val = 0
    total_bh_val = 0
    
    for stock in all_stocks:
        init_row = init_holdings[init_holdings['Stock'] == stock]
        init_qty = init_row['Quantity'].iloc[0] if not init_row.empty else 0
        init_price = init_row['Buy_Price'].iloc[0] if not init_row.empty else 0
        init_val = init_row['Invested_Amount'].iloc[0] if not init_row.empty else 0
        init_date = init_row['Buy_Date'].iloc[0] if not init_row.empty else "-"
        
        sim_qty = final_holdings.get(stock, 0)
        final_price = get_final_price(stock, TARGET_DATE)
        
        sim_val = sim_qty * final_price
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

    # 4. Add CASH row (as shown in user screenshot)
    # Get initial cash for the 'Initial_Value' column
    init_cash = 0.0
    try:
        with open("../investment/grand_totals.txt", "r") as f:
            for line in f:
                if "Remaining Unspent Cash:" in line:
                    init_cash = float(line.split("NPR")[-1].strip().replace(",", ""))
                    break
    except: pass

    cash_row = {
        'Stock': 'CASH',
        'Initial_Buy_Date': '-',
        'Initial_Qty': 0,
        'Initial_Price': 0,
        'Initial_Value': round(init_cash, 2),
        f'{DATE_STR} Qty': 0,
        f'{DATE_STR} Price': 0,
        f'{DATE_STR} Value': round(final_cash_sim, 2)
    }
    records.append(cash_row)
    
    # Adjust totals to include cash
    total_init_val += init_cash
    total_sim_val += final_cash_sim

    # Create DataFrame and add Total row
    comparison_df = pd.DataFrame(records)
    summary_row = {
        'Stock': 'TOTAL',
        'Initial_Buy_Date': '-',
        'Initial_Qty': comparison_df['Initial_Qty'].sum(),
        'Initial_Price': '',
        'Initial_Value': round(total_init_val, 2),
        f'{DATE_STR} Qty': comparison_df[f'{DATE_STR} Qty'].sum(),
        f'{DATE_STR} Price': '',
        f'{DATE_STR} Value': round(total_sim_val, 2)
    }
    
    comparison_df = pd.concat([comparison_df, pd.DataFrame([summary_row])], ignore_index=True)
    comparison_df.to_csv(COMPARISON_OUTPUT, index=False)
    
    # Calculate Results
    final_total_val = total_sim_val # Already includes cash from line 155
    total_profit = final_total_val - total_init_val
    return_pct = (total_profit / total_init_val) * 100 if total_init_val > 0 else 0

    print("\n--- PORTFOLIO COMPARISON SUMMARY (2015-2025) ---")
    print(f"Total Initial Cost:      NPR {total_init_val:,.2f}")
    print(f"Simulation Stock Value:  NPR {total_sim_val - final_cash_sim:,.2f}")
    print(f"Simulation Final Cash:   NPR {final_cash_sim:,.2f}")
    print(f"TOTAL SIMULATION VALUE:  NPR {final_total_val:,.2f}")
    
    # Update trading_summary.txt
    with open("trading_summary.txt", "w", encoding='utf-8') as f:
        f.write("========================================\n")
        f.write("       TRADING SIMULATION RESULTS\n")
        f.write("========================================\n")
        f.write(f"Initial Investment : {total_init_val:>15,.2f}\n")
        f.write(f"Final Value        : {final_total_val:>15,.2f}\n")
        f.write(f"Total Profit       : {total_profit:>15,.2f}\n")
        f.write(f"Return (%)         : {return_pct:>14.2f}%\n")
        f.write("========================================\n")
    print(f"Summary saved: trading_summary.txt")

if __name__ == "__main__":
    build_comparison()
