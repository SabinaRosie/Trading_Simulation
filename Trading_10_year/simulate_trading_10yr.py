import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# Configuration (Paths for Sabina_Trading)
DATA_DIR = "../stocks"
INITIAL_INVESTMENT_FILE = "../investment/initial_investment_sabina.csv"
INITIAL_GRAND_TOTALS = "../investment/grand_totals.txt"
OUTPUT_FILE = "trading_simulation_10yr_output.csv"

START_DATE = "2015-01-01"
END_DATE = "2025-12-31"

COOLDOWN_DAYS = 4
SMA_FAST = 20
SMA_SLOW = 50

# Strategy Thresholds (Reverted to High-Performance Pure SMA)
PROFIT_BOOKING_THRESHOLD = 0.50  # 50% gain
STOP_LOSS_THRESHOLD = 0.15      # 15% loss
DIP_BUYING_THRESHOLD = 0.12      # 12% below SMA
MOMENTUM_BREAKOUT_THRESHOLD = 0.10 # 10% gain in 5 days

def load_initial_state():
    # Load holdings and filter summary rows
    initial_holdings = pd.read_csv(INITIAL_INVESTMENT_FILE)
    initial_holdings = initial_holdings[initial_holdings['Stock'] != 'GRAND TOTAL']
    
    agg_holdings = initial_holdings.groupby('Stock').agg({
        'Quantity': 'sum',
        'Invested_Amount': 'sum'
    }).reset_index()
    
    holdings = {}
    for _, row in agg_holdings.iterrows():
        stock = row['Stock']
        qty = row['Quantity']
        amt = row['Invested_Amount']
        holdings[stock] = {
            'qty': qty,
            'avg_price': amt / qty,
            'last_action_date': datetime(2014, 12, 31)
        }
    
    # Load cash from grand_totals.txt
    cash = 0.0
    try:
        with open(INITIAL_GRAND_TOTALS, "r") as f:
            for line in f:
                if "Remaining Unspent Cash:" in line:
                    cash = float(line.split("NPR")[-1].strip().replace(",", ""))
                    break
    except:
        cash = 60.0
        
    return holdings, cash

def load_stock_data():
    stock_dfs = {}
    for file in os.listdir(DATA_DIR):
        if file.endswith(".csv"):
            stock_name = file.replace(".csv", "")
            try:
                df = pd.read_csv(os.path.join(DATA_DIR, file))
                df['published_date'] = pd.to_datetime(df['published_date'])
                df = df.sort_values('published_date').drop_duplicates('published_date').set_index('published_date')
                
                # Indicators
                df['SMA20'] = df['close'].rolling(window=SMA_FAST).mean()
                df['SMA50'] = df['close'].rolling(window=SMA_SLOW).mean()
                df['Return5d'] = df['close'].pct_change(5)
                
                stock_dfs[stock_name] = df
            except: continue
    return stock_dfs

def simulate():
    print(f"Executing 11-Year Pure SMA Simulation ({START_DATE}-{END_DATE})...")
    holdings, cash = load_initial_state()
    stock_dfs = load_stock_data()
    
    all_dates = sorted(pd.to_datetime(list(set().union(*(df.index for df in stock_dfs.values())))))
    sim_dates = [d for d in all_dates if pd.Timestamp(START_DATE) <= d <= pd.Timestamp(END_DATE)]
    
    logs = []
    cooldown_until = {stock: datetime(2014, 12, 31) for stock in stock_dfs.keys()}
    
    for current_date in sim_dates:
        for stock, df in stock_dfs.items():
            if current_date not in df.index: continue
            row = df.loc[current_date]
            price, sma20, sma50, ret5d = row['close'], row['SMA20'], row['SMA50'], row['Return5d']
            
            if pd.isna(sma20) or pd.isna(sma50): continue
            if current_date < cooldown_until.get(stock, datetime(2014, 12, 31)): continue
            
            action = None
            reason = ""
            
            # 1. SELL LOGIC
            if stock in holdings:
                holding = holdings[stock]
                qty, avg_p = holding['qty'], holding['avg_price']
                gain_pct = (price - avg_p) / avg_p
                
                if gain_pct >= PROFIT_BOOKING_THRESHOLD:
                    action, reason = "SELL", f"Take Profit Triggered: {gain_pct*100:+.2f}% gain achieved."
                elif gain_pct <= -STOP_LOSS_THRESHOLD:
                    action, reason = "SELL", f"Stop-loss activated after {STOP_LOSS_THRESHOLD*100:.0f}% downside protection threshold."
                elif sma20 < sma50:
                    idx = df.index.get_loc(current_date)
                    if idx > 0 and df.iloc[idx-1]['SMA20'] >= df.iloc[idx-1]['SMA50']:
                        action, reason = "SELL", "20-Day SMA crossed below 50-Day SMA indicating bearish momentum."
                
                if action == "SELL":
                    total_amt = qty * price
                    cash += total_amt
                    tms_val = sum(h['qty'] * h['avg_price'] for s, h in holdings.items() if s != stock)
                    port_val = cash + sum(h['qty'] * (stock_dfs[s].loc[current_date]['close'] if current_date in stock_dfs[s].index else h['avg_price']) for s, h in holdings.items() if s != stock)
                    pl = total_amt - (qty * avg_p)
                    
                    logs.append({
                        "Date": current_date.strftime("%b %d, %Y"), "Stock Name": stock, "Action": "SELL", "Quantity": qty,
                        "Price": round(price, 2), "Total Amount": round(total_amt, 2), "Cash In Hand": round(cash, 2),
                        "TMS Khata Value": round(tms_val, 2), "Portfolio Value": round(port_val, 2),
                        "Profit/Loss": round(pl, 2), "Gain/Loss Percentage": f"{(pl/(qty*avg_p))*100:.2f}%", "Exact Reason for Buy/Sell": reason
                    })
                    del holdings[stock]
                    cooldown_until[stock] = current_date + timedelta(days=COOLDOWN_DAYS)
                    continue

            # 2. BUY LOGIC
            if stock not in holdings and cash > 1000:
                idx = df.index.get_loc(current_date)
                if idx > 0 and df.iloc[idx-1]['SMA20'] <= df.iloc[idx-1]['SMA50'] and sma20 > sma50:
                    action, reason = "BUY", "20-Day SMA crossed above 50-Day SMA indicating bullish momentum."
                elif price < sma20 * (1 - DIP_BUYING_THRESHOLD):
                    action, reason = "BUY", f"Price dropped {DIP_BUYING_THRESHOLD*100:.0f}% below SMA; dip buying opportunity detected."
                elif ret5d > MOMENTUM_BREAKOUT_THRESHOLD:
                    action, reason = "BUY", f"Strong upward trend confirmed (5-day return: {ret5d*100:.2f}%)."

                if action == "BUY":
                    invest_amt = min(cash * 0.1, 50000)
                    qty = int(invest_amt // price)
                    if qty >= 5:
                        total_amt = qty * price
                        cash -= total_amt
                        holdings[stock] = {'qty': qty, 'avg_price': price, 'last_action_date': current_date}
                        tms_v = sum(h['qty'] * h['avg_price'] for s, h in holdings.items())
                        port_v = cash + sum(h['qty'] * (stock_dfs[s].loc[current_date]['close'] if current_date in stock_dfs[s].index else h['avg_price']) for s, h in holdings.items())
                        logs.append({
                            "Date": current_date.strftime("%b %d, %Y"), "Stock Name": stock, "Action": "BUY", "Quantity": qty,
                            "Price": round(price, 2), "Total Amount": round(total_amt, 2), "Cash In Hand": round(cash, 2),
                            "TMS Khata Value": round(tms_v, 2), "Portfolio Value": round(port_v, 2),
                            "Profit/Loss": 0.0, "Gain/Loss Percentage": "0.00%", "Exact Reason for Buy/Sell": reason
                        })
                        cooldown_until[stock] = current_date + timedelta(days=COOLDOWN_DAYS)

    if logs:
        # Summary Row and Formatting
        _, init_cash = load_initial_state()
        first_a = logs[0]['Total Amount']
        if logs[0]['Action'] == "BUY": logs[0]['Cash In Hand'] = f"({init_cash} - {first_a} = {logs[0]['Cash In Hand']})"
        else: logs[0]['Cash In Hand'] = f"({init_cash} + {first_a} = {logs[0]['Cash In Hand']})"

        pd_logs = pd.DataFrame(logs)
        total_pl = pd_logs["Profit/Loss"].sum()
        total_amt = pd_logs["Total Amount"].sum()
        total_gain_pct = (total_pl / (total_amt - total_pl)) * 100 if (total_amt - total_pl) != 0 else 0
        
        summary_row = {
            "Date": "GRAND TOTAL", "Stock Name": "ALL", "Action": "SUMMARY",
            "Quantity": pd_logs["Quantity"].sum(), "Price": "", "Total Amount": round(total_amt, 2),
            "Cash In Hand": "", "TMS Khata Value": "", "Portfolio Value": "",
            "Profit/Loss": round(total_pl, 2), "Gain/Loss Percentage": f"{total_gain_pct:.2f}%",
            "Exact Reason for Buy/Sell": f"Total Realized P/L: NPR {total_pl:,.2f}"
        }
        pd_logs = pd.concat([pd_logs, pd.DataFrame([summary_row])], ignore_index=True)
        pd_logs.to_csv(OUTPUT_FILE, index=False)
        print(f"Simulation complete. Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    simulate()
