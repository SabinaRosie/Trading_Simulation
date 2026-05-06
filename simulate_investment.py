import os
import csv
from datetime import datetime, timedelta

def format_date_concept(date_obj):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[date_obj.month-1]} {date_obj.day:02d}, {date_obj.year}"

def calculate_sma(history, current_date_str, window=20):
    past_prices = [h['close'] for h in history if h['date'] < current_date_str]
    if len(past_prices) < window:
        return None
    return sum(past_prices[-window:]) / window

def run_simulation():
    stocks_dir = r'c:\Users\PS\Desktop\Sabina_Trading\stocks'
    total_budget = 300000
    start_date = datetime(2013, 1, 1)
    end_date = datetime(2014, 12, 30)
    
    stock_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('.csv')])
    
    stocks_history = {}
    stocks_data_map = {}
    for filename in stock_files:
        symbol = filename.replace('.csv', '')
        stocks_history[symbol] = []
        stocks_data_map[symbol] = {}
        filepath = os.path.join(stocks_dir, filename)
        with open(filepath, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row['published_date']
                p = float(row['close'])
                stocks_history[symbol].append({'date': d, 'close': p})
                stocks_data_map[symbol][d] = p
        stocks_history[symbol].sort(key=lambda x: x['date'])

    stock_quantities = {symbol: 0 for symbol in stocks_history.keys()}
    stock_invested_total = {symbol: 0.0 for symbol in stocks_history.keys()}
    transactions = []
    global_cash = total_budget
    
    # --- PHASE 1: MANDATORY 15 SHARES FOR EVERYONE ---
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        candidates = []
        for symbol in stocks_history.keys():
            if date_str in stocks_data_map[symbol]:
                candidates.append({'symbol': symbol, 'price': stocks_data_map[symbol][date_str]})
        candidates.sort(key=lambda x: x['price'])
        
        for item in candidates:
            symbol = item['symbol']
            price = item['price']
            if stock_quantities[symbol] == 0:
                qty = 15
                cost = qty * price
                if global_cash >= cost:
                    global_cash -= cost
                    stock_quantities[symbol] += qty
                    stock_invested_total[symbol] += cost
                    transactions.append({
                        'Stock': symbol,
                        'Buy_Date': format_date_concept(current_date),
                        'Buy_Price': price,
                        'Quantity': qty,
                        'Invested_Amount': cost
                    })
        current_date += timedelta(days=1)

    # --- PHASE 2: GROWTH ---
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        candidates = []
        for symbol in stocks_history.keys():
            if date_str in stocks_data_map[symbol]:
                candidates.append({'symbol': symbol, 'price': stocks_data_map[symbol][date_str]})
        candidates.sort(key=lambda x: x['price'])
        
        for item in candidates:
            symbol = item['symbol']
            price = item['price']
            current_sma = calculate_sma(stocks_history[symbol], date_str, window=20)
            if current_sma and price < (current_sma * 0.95):
                qty = 15
                cost = qty * price
                if global_cash >= cost:
                    global_cash -= cost
                    stock_quantities[symbol] += qty
                    stock_invested_total[symbol] += cost
                    transactions.append({
                        'Stock': symbol,
                        'Buy_Date': format_date_concept(current_date),
                        'Buy_Price': price,
                        'Quantity': qty,
                        'Invested_Amount': cost
                    })
        current_date += timedelta(days=1)

    # FINAL VALUATION
    total_market_value = 0
    total_invested = sum(stock_invested_total.values())
    total_shares_purchased = sum(stock_quantities.values())
    
    stock_summaries = []
    for symbol in sorted(stocks_history.keys()):
        final_price = 0.0
        temp_date = end_date
        for _ in range(1000): 
            check_str = temp_date.strftime('%Y-%m-%d')
            if check_str in stocks_data_map[symbol]:
                final_price = stocks_data_map[symbol][check_str]
                break
            temp_date -= timedelta(days=1)
        
        qty = stock_quantities[symbol]
        invested = stock_invested_total[symbol]
        total_market_value += (qty * (final_price if final_price else 0))
        if qty > 0:
            stock_summaries.append({
                'Stock': symbol,
                'Total_Quantity': qty,
                'Avg_Price': invested / qty,
                'Total_Invested': invested
            })

    remaining_cash = total_budget - total_invested
    total_portfolio_value = total_market_value + remaining_cash
    total_profit = total_portfolio_value - total_budget

    # --- SAVE FILE 1: TRANSACTION LOG (CSV) ---
    transactions.sort(key=lambda x: datetime.strptime(x['Buy_Date'], "%b %d, %Y"))
    with open('initial_investment_sabina.csv', mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['Stock', 'Buy_Date', 'Buy_Price', 'Quantity', 'Invested_Amount']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    # --- SAVE FILE 2: STOCK-WISE SUMMARY (CSV) ---
    with open('stock_wise_summary.csv', mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Stock Name', 'Total Quantity', 'Avg Buy Price', 'Total Invested'])
        for s in stock_summaries:
            writer.writerow([s['Stock'], s['Total_Quantity'], f"{s['Avg_Price']:.2f}", f"{s['Total_Invested']:.2f}"])

    # --- SAVE FILE 3: GRAND TOTALS (TXT) ---
    with open('grand_totals.txt', mode='w', encoding='utf-8') as f:
        f.write(f"--- FINAL PORTFOLIO TOTALS (Dec 30, 2014) ---\n")
        f.write(f"Total Invested Quantity: {total_shares_purchased} Shares\n")
        f.write(f"Total Invested Cash:     NPR {total_invested:,.2f}\n")
        f.write(f"Remaining Unspent Cash:  NPR {remaining_cash:,.2f}\n")
        f.write(f"Market Value of Shares:  NPR {total_market_value:,.2f}\n")
        f.write(f"TOTAL PORTFOLIO VALUE:   NPR {total_portfolio_value:,.2f}\n")
        f.write(f"TOTAL PROFIT/LOSS:       NPR {total_profit:,.2f} ({ (total_profit/total_budget)*100 :.2f}%)\n")

    print(f"Success! Three files generated:")
    print(f"- initial_investment_sabina.csv (Transactions)")
    print(f"- stock_wise_summary.csv (Summary)")
    print(f"- grand_totals.txt (Final Metrics)")

if __name__ == "__main__":
    run_simulation()
