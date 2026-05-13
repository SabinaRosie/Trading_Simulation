import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

# ==================================================================================
# 1. Configuration & Strategy Thresholds
# ==================================================================================
DATA_DIR = "../stocks"
INITIAL_INVESTMENT_FILE = "../investment/initial_investment_sabina.csv"
GRAND_TOTALS_FILE = "../investment/grand_totals.txt"
OUTPUT_FILE = "trading_simulation_10yr_final.csv"

START_DATE = "2015-01-01"
END_DATE = "2025-12-30"


COOLDOWN_DAYS = 4
SMA_FAST = 20
SMA_SLOW = 50
RSI_WINDOW = 14

# Quantitative Strategy Thresholds (100% PROFIT TARGET EXPERIMENT)
PROFIT_BOOKING_THRESHOLD = 1.0   # Sell if profit hits 100% (Double your money)
STOP_LOSS_THRESHOLD = 0.15       # Standard Stop Loss: 15%
DIP_BUYING_THRESHOLD = 0.12      
MOMENTUM_BREAKOUT_THRESHOLD = 0.10 
MIN_CONFIDENCE_SCORE = 60        # Standard entry barrier

def load_initial_state():
    """Loads starting holdings and cash balance from previous investment phase."""
    initial_holdings = pd.read_csv(INITIAL_INVESTMENT_FILE)
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
    
    cash = 0.0
    try:
        with open(GRAND_TOTALS_FILE, "r") as f:
            for line in f:
                if "Remaining Unspent Cash:" in line:
                    cash = float(line.split("NPR")[-1].strip().replace(",", ""))
                    break
    except:
        cash = 60.0 # Default if file not found
    return holdings, cash

def calculate_rsi(series, period=14):
    """Calculates Relative Strength Index (RSI) using standard formula."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9) # Avoid division by zero
    return 100 - (100 / (1 + rs))

def load_stock_data():
    """Loads all stock CSVs and pre-calculates Multi-Factor Indicators."""
    stock_dfs = {}
    for file in os.listdir(DATA_DIR):
        if file.endswith(".csv"):
            stock_name = file.replace(".csv", "")
            df = pd.read_csv(os.path.join(DATA_DIR, file))
            df['published_date'] = pd.to_datetime(df['published_date'])
            df = df.sort_values('published_date').drop_duplicates('published_date').set_index('published_date')
            
            # --- Technical Indicators for Quantitative Analysis ---
            df['SMA20'] = df['close'].rolling(window=SMA_FAST).mean()
            df['SMA50'] = df['close'].rolling(window=SMA_SLOW).mean()
            df['VolMA20'] = df['traded_quantity'].rolling(window=20).mean()
            df['RSI'] = calculate_rsi(df['close'], RSI_WINDOW)
            df['Return5d'] = df['close'].pct_change(5)
            
            stock_dfs[stock_name] = df
    return stock_dfs

def simulate():
    print("Initializing Multi-Factor Quantitative Engine...")
    holdings, cash = load_initial_state()
    stock_dfs = load_stock_data()
    
    all_dates = sorted(pd.to_datetime(list(set().union(*(df.index for df in stock_dfs.values())))))
    sim_dates = [d for d in all_dates if pd.Timestamp(START_DATE) <= d <= pd.Timestamp(END_DATE)]
    
    logs = []
    cooldown_until = {stock: datetime(2014, 12, 31) for stock in stock_dfs.keys()}
    
    print(f"Executing 10-Year Quantitative Simulation (2015-2024)...")
    for current_date in sim_dates:
        
        # 1. Market Health
        active_stocks_today = [s for s, df in stock_dfs.items() if current_date in df.index]
        bullish_count = 0
        for s in active_stocks_today:
            row = stock_dfs[s].loc[current_date]
            if not pd.isna(row['SMA50']) and row['close'] > row['SMA50']:
                bullish_count += 1
        
        market_health_pct = (bullish_count / len(active_stocks_today) * 100) if active_stocks_today else 0
        market_is_bearish = market_health_pct < 40
        
        # 2. SELL LOGIC
        stocks_to_sell = []
        for stock in list(holdings.keys()):
            if stock not in stock_dfs or current_date not in stock_dfs[stock].index:
                continue
            
            df = stock_dfs[stock]
            row = df.loc[current_date]
            price, sma20, sma50 = row['close'], row['SMA20'], row['SMA50']
            
            if pd.isna(sma20) or pd.isna(sma50) or current_date < cooldown_until[stock]:
                continue
                
            holding = holdings[stock]
            gain_pct = (price - holding['avg_price']) / holding['avg_price']
            
            action, strategy_signal, reason = None, "", ""
            
            if gain_pct >= PROFIT_BOOKING_THRESHOLD:
                action, strategy_signal = "SELL", "Profit Booking"
                reason = f"Target Achieved: {gain_pct*100:+.2f}% gain."
            elif gain_pct <= -STOP_LOSS_THRESHOLD:
                action, strategy_signal = "SELL", "Stop Loss"
                reason = f"Stop-Loss hit at {gain_pct*100:+.2f}%."
            elif sma20 < sma50:
                idx = df.index.get_loc(current_date)
                if idx > 0 and df.iloc[idx-1]['SMA20'] >= df.iloc[idx-1]['SMA50']:
                    action, strategy_signal = "SELL", "Trend Breakdown"
                    reason = "Death Cross: SMA20 crossed below SMA50."

            if action == "SELL" and holding['qty'] >= 15:
                stocks_to_sell.append((stock, holding['qty'], price, holding['avg_price'], strategy_signal, reason))

        for stock, qty, price, avg_p, signal, reason in stocks_to_sell:
            amt = qty * price
            cash += amt
            pl = amt - (qty * avg_p)
            del holdings[stock]
            
            # Analytics (Market Value Logic)
            tms_val = sum(h['qty'] * h['avg_price'] for h in holdings.values())
            stock_market_val = sum(holdings[s]['qty'] * (stock_dfs[s].loc[current_date]['close'] if s in stock_dfs and current_date in stock_dfs[s].index else holdings[s]['avg_price']) for s in holdings)
            port_val = cash + stock_market_val

            logs.append({
                "Date": current_date.strftime("%b %d, %Y"),
                "Stock Name": stock, "Action": "SELL", "Quantity": int(qty),
                "Price": round(price, 2), "Amount": round(amt, 2), "Cash": round(cash, 2),
                "TMS Khata Value": round(tms_val, 2), "Portfolio Value": round(port_val, 2),
                "Profit/Loss": round(pl, 2), "Gain %": f"{(price/avg_p - 1)*100:+.2f}%",
                "Reason": f"[{signal}] {reason} (Market Health: {market_health_pct:.1f}%)"
            })
            cooldown_until[stock] = current_date + timedelta(days=COOLDOWN_DAYS)

        # 3. BUY LOGIC
        if cash > 2000 and not market_is_bearish:
            potential_buys = []
            for stock, df in stock_dfs.items():
                if stock in holdings or current_date not in df.index:
                    continue
                
                row = df.loc[current_date]
                price, sma20, sma50, vol, vol_ma, rsi, ret5d = row['close'], row['SMA20'], row['SMA50'], row['traded_quantity'], row['VolMA20'], row['RSI'], row['Return5d']
                
                if pd.isna(sma20) or pd.isna(sma50) or pd.isna(rsi) or current_date < cooldown_until[stock]:
                    continue
                
                score = 0
                reasons = []
                if price > sma50 and sma20 > sma50: score += 30; reasons.append("Strong Uptrend")
                if 40 < rsi < 70: score += 15; reasons.append("Stable RSI")
                if ret5d > 0: score += 10; reasons.append("Positive Momentum")
                if vol > vol_ma * 1.5: score += 20; reasons.append("Volume Breakout")
                
                idx = df.index.get_loc(current_date)
                if idx > 0 and df.iloc[idx-1]['SMA20'] <= df.iloc[idx-1]['SMA50'] and sma20 > sma50:
                    score += 15; reasons.append("Golden Cross")
                elif price < sma20 * (1 - DIP_BUYING_THRESHOLD):
                    score += 15; reasons.append("Oversold Dip")
                
                if market_health_pct > 60: score += 10; reasons.append("Healthy Market Index")

                if score >= MIN_CONFIDENCE_SCORE:
                    potential_buys.append((stock, score, ", ".join(reasons), price))
            
            potential_buys.sort(key=lambda x: x[1], reverse=True)
            
            for stock, score, score_reason, price in potential_buys:
                if cash < 2000: break
                
                base_alloc = min(cash * 0.2, 60000) 
                invest_amt = base_alloc * (score / 100)
                qty = int(invest_amt // price)
                
                if qty >= 15:
                    amt = qty * price
                    cash -= amt
                    holdings[stock] = {'qty': qty, 'avg_price': price}
                    
                    # Analytics (Market Value Logic - to match 16 Lakh style)
                    tms_val = sum(h['qty'] * h['avg_price'] for h in holdings.values())
                    stock_market_val = sum(holdings[s]['qty'] * (stock_dfs[s].loc[current_date]['close'] if s in stock_dfs and current_date in stock_dfs[s].index else holdings[s]['avg_price']) for s in holdings)
                    port_val = cash + stock_market_val

                    logs.append({
                        "Date": current_date.strftime("%b %d, %Y"),
                        "Stock Name": stock, "Action": "BUY", "Quantity": qty,
                        "Price": round(price, 2), "Amount": round(amt, 2), "Cash": round(cash, 2),
                        "TMS Khata Value": round(tms_val, 2), "Portfolio Value": round(port_val, 2),
                        "Profit/Loss": 0, "Gain %": "0.00%",
                        "Reason": f"[Quant Buy] Confidence {score}/100: {score_reason} (Market Health: {market_health_pct:.1f}%)"
                    })
                    cooldown_until[stock] = current_date + timedelta(days=COOLDOWN_DAYS)

    if logs:
        _, init_cash = load_initial_state()
        logs[0]['Cash'] = f"({init_cash} + {logs[0]['Amount']} = {logs[0]['Cash']})"
        
        df_out = pd.DataFrame(logs)
        
        # Calculate Grand Totals for numeric columns
        total_qty = df_out["Quantity"].sum()
        total_amt = df_out["Amount"].sum()
        total_pl = df_out["Profit/Loss"].sum()
        
        # Create summary row
        summary_row = {
            "Date": "GRAND TOTAL",
            "Stock Name": "ALL",
            "Action": "SUMMARY",
            "Quantity": total_qty,
            "Price": "",
            "Amount": round(total_amt, 2),
            "Cash": "",
            "TMS Khata Value": "",
            "Portfolio Value": "",
            "Profit/Loss": round(total_pl, 2),
            "Gain %": "",
            "Reason": f"Total Turnover: NPR {total_amt:,.2f}, Total Realized P/L: NPR {total_pl:,.2f}"
        }
        
        # Append summary row to DataFrame
        df_out = pd.concat([df_out, pd.DataFrame([summary_row])], ignore_index=True)
        
        df_out.to_csv(OUTPUT_FILE, index=False)
        print(f"Simulation Complete. Generated {len(logs)} trades.")
        print(f"Final Cash Pool: NPR {cash:,.2f}")
        print(f"Total Realized Profit/Loss: NPR {total_pl:,.2f}")
        print(f"Report saved: {OUTPUT_FILE}")
        
        # --- Save 10-Year Trading Summary (CSV) ---
        summary_records = []
        for stock, data in holdings.items():
            summary_records.append({
                'Stock Name': stock,
                'Total Quantity': data['qty'],
                'Avg Buy Price': round(data['avg_price'], 2),
                'Total Invested': round(data['qty'] * data['avg_price'], 2)
            })
        
        df_summary = pd.DataFrame(summary_records)
        if not df_summary.empty:
            total_q = df_summary['Total Quantity'].sum()
            total_i = df_summary['Total Invested'].sum()
            df_summary = pd.concat([df_summary, pd.DataFrame([{
                'Stock Name': 'GRAND TOTAL',
                'Total Quantity': total_q,
                'Avg Buy Price': '',
                'Total Invested': total_i
            }])], ignore_index=True)
            
        df_summary.to_csv("trading_simulation_10yr_summary.csv", index=False)
        print(f"Summary saved: trading_simulation_10yr_summary.csv")

if __name__ == "__main__":
    simulate()
