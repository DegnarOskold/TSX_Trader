import json
import codecs
import re
import pandas as pd
import yfinance as yf
from datetime import datetime
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
import market_analyzer

# Calculate True P&L
csv_path = os.path.join(base_dir, 'trades.csv')
df = pd.read_csv(csv_path)

today_str = datetime.now().strftime('%Y-%m-%d')

# Cumulative Realized P&L Tracker
holdings_tracker = {}
realized_trades = []

for idx, row in df.iterrows():
    action = str(row['Action']).strip().upper()
    ticker = str(row['Ticker']).strip()
    date_str = str(row['Date']).strip()
    
    qty = 0.0
    if pd.notna(row.get('Quantity')) and str(row.get('Quantity')).strip() != '':
        qty = float(row['Quantity'])
    elif pd.notna(row.get('Amount')) and str(row.get('Amount')).strip() != '':
        qty = float(row['Amount'])
    elif pd.notna(row.get('Shares')) and str(row.get('Shares')).strip() != '':
        qty = float(row['Shares'])
        
    price = float(row['Price']) if pd.notna(row.get('Price')) else 0.0
    
    if ticker in ['CASH']:
        continue
        
    if action in ['INIT', 'BUY']:
        if ticker not in holdings_tracker:
            holdings_tracker[ticker] = {'shares': 0.0, 'total_cost': 0.0}
        holdings_tracker[ticker]['shares'] += qty
        holdings_tracker[ticker]['total_cost'] += qty * price
    elif action == 'DIVIDEND':
        div_pnl = round(qty * price, 2)
        realized_trades.append({
            'date': date_str,
            'ticker': ticker,
            'action': 'DIVIDEND',
            'pnl': div_pnl,
            'pct': 100.0,
            'shares': qty,
            'price': price
        })
    elif action == 'SELL':
        if ticker in holdings_tracker and holdings_tracker[ticker]['shares'] > 0:
            avg_cost = holdings_tracker[ticker]['total_cost'] / holdings_tracker[ticker]['shares']
            cost = avg_cost * qty
            proceeds = price * qty
            pnl = proceeds - cost
            pct = (pnl / cost) * 100 if cost > 0 else 0.0
            realized_trades.append({
                'date': date_str,
                'ticker': ticker,
                'action': 'SELL',
                'pnl': pnl,
                'pct': pct,
                'shares': qty,
                'price': price,
                'cost': cost,
                'proceeds': proceeds
            })
            holdings_tracker[ticker]['shares'] -= qty
            holdings_tracker[ticker]['total_cost'] -= cost
            if holdings_tracker[ticker]['shares'] <= 1e-5:
                holdings_tracker[ticker]['shares'] = 0.0
                holdings_tracker[ticker]['total_cost'] = 0.0

rdf = pd.DataFrame(realized_trades)
active_df = rdf[rdf['date'] >= '2026-06-22']
active_realized = active_df['pnl'].sum()
active_wins = len(active_df[active_df['pnl'] > 0])
active_losses = len(active_df[active_df['pnl'] < 0])
total_all_time = rdf['pnl'].sum()
win_rate = (active_wins / len(active_df)) * 100 if len(active_df) > 0 else 0.0

# Today's closed trades
todays_closed = [t for t in realized_trades if t['date'].startswith(today_str)]

deposits = df[df['Action'] == 'DEPOSIT']['Price'].sum() if 'DEPOSIT' in df['Action'].values else 0.0
start_equity = 5920.88 + deposits
tickers = df['Ticker'].unique()
current_shares = {}
cost_bases = {}

for ticker in tickers:
    if ticker == 'CASH':
        continue
    subset = df[df['Ticker'] == ticker]
    if not subset.empty:
        shares = subset.iloc[-1]['Shares_Balance']
        if shares > 0:
            current_shares[ticker] = shares
            buys = subset[subset['Action'] == 'BUY']
            if not buys.empty:
                cost_bases[ticker] = buys.iloc[-1]['Price']

current_cash = df.iloc[-1]['Cash_Balance']
current_equity = current_cash
portfolio_values = {}

for t, shares in current_shares.items():
    data = yf.Ticker(t).history(period="1d")
    price = None
    if not data.empty and pd.notna(data['Close'].iloc[-1]):
        price = data['Close'].iloc[-1]
    else:
        hist_5d = yf.Ticker(t).history(period="5d")
        if not hist_5d.empty and pd.notna(hist_5d['Close'].iloc[-1]):
            price = hist_5d['Close'].iloc[-1]
        elif t in cost_bases:
            price = cost_bases[t]

    if price is not None:
        val = price * shares
        portfolio_values[t] = {'price': price, 'val': val, 'shares': shares}
        current_equity += val

absolute_pnl = current_equity - start_equity
percentage_pnl = (absolute_pnl / start_equity) * 100

# Macro check
macro_green = {}
for sym in ['GC=F', 'CL=F']:
    data = yf.Ticker(sym).history(period="2d")
    if len(data) >= 2:
        close_today = data['Close'].iloc[-1]
        close_yday = data['Close'].iloc[-2]
        macro_green[sym] = (close_today > close_yday)
    else:
        macro_green[sym] = True

def is_commodity_aligned(ticker):
    if ticker in ['AEM.TO', 'ABX.TO', 'K.TO', 'FNV.TO']:
        return macro_green.get('GC=F', True)
    if ticker in ['CNQ.TO', 'SU.TO', 'CVE.TO', 'TOU.TO']:
        return macro_green.get('CL=F', True)
    return True

content = market_analyzer.generate_dossier()
blocks = content.split('\n\n')

owned = []
buys = []
sells = []

for block in blocks:
    lines = block.strip().split('\n')
    if not lines or not lines[0]:
        continue
    ticker = lines[0].strip(':').strip()
    if not ticker.endswith('.TO') and not ticker in ['CASH', 'TOTAL']:
        continue
        
    if 'Shares Owned:' in block and 'Shares Owned: 0.0000' not in block:
        unrealized = [l for l in lines if 'Unrealised P&L' in l]
        
        # Stagnation rule check
        buy_records = df[(df['Ticker'] == ticker) & (df['Action'] == 'BUY')]
        days_held = 0
        if not buy_records.empty:
            purchase_date_str = buy_records['Date'].iloc[-1]
            try:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d')
            days_held = (datetime.now() - purchase_date).days
        
        ema_cross = next((l for l in lines if 'EMA Crossover' in l), "")
        
        if unrealized:
            pnl_line = unrealized[0].strip()
            match = re.search(r'\(([-+]\d+\.\d+)%\)', pnl_line)
            flag = ""
            if match:
                pct = float(match.group(1))
                if pct > 2.0:
                    flag = " 🚀 *(PROFIT TARGET: >2% gain! Move Stop Loss up to Breakeven)*"
                elif pct < -5.0:
                    flag = " 🛑 *(STOP LOSS TRIGGERED: -5% Limit reached!)*"
                    sells.append(f"🔴 **SELL ALERT: {ticker} (Stop Loss Triggered @ -5%)**")
                elif pct < 0 and days_held > 4 and 'BEARISH' in ema_cross:
                    flag = " 📉 *(STAGNATION EXIT: Held > 4 days, Negative, Bearish Cross. SELL)*"
                    sells.append(f"🔴 **SELL ALERT: {ticker} (Stagnation Exit: Held > 4 days, Negative, Bearish Cross)**")
            owned.append(f"- **{ticker}:** {pnl_line.split(': ')[1]}{flag}")

    elif 'Shares Owned: 0.0000' in block:
        ema_cross = next((l for l in lines if 'EMA Crossover' in l), None)
        rsi_line = next((l for l in lines if 'RSI' in l), None)
        adx_line = next((l for l in lines if 'ADX' in l), None)
        vol_line = next((l for l in lines if 'Vol Ratio' in l), None)
        
        if rsi_line and adx_line and ema_cross and vol_line:
            cross = ema_cross.split(': ')[1]
            rsi = float(rsi_line.split(': ')[1])
            adx = float(adx_line.split(': ')[1])
            vol_ratio = float(vol_line.split(': ')[1].replace('x',''))
            
            # Target calculation
            price_line = next((l for l in lines if 'Current Market Price' in l), None)
            bb_mid_line = next((l for l in lines if 'Bollinger Mid' in l), None)
            atr_line = next((l for l in lines if 'ATR (' in l), None)
            
            target = 0
            stop = 0
            if price_line and bb_mid_line and atr_line:
                try:
                    price = float(price_line.split('$')[1].strip())
                    bb_mid = float(bb_mid_line.split('$')[1].strip())
                    atr = float(atr_line.split('$')[1].strip())
                    
                    target = bb_mid
                    if target <= price or pd.isna(target):
                        target = price + (1.5 * atr)
                    stop = price * 0.95
                except Exception:
                    continue
            
            if pd.isna(target) or pd.isna(stop) or target <= 0 or stop <= 0:
                continue
                
            if 'BULLISH' in cross:
                # STRICT OVERBOUGHT FILTER
                if rsi > 75:
                    rsi_pass = False
                elif rsi > 65:
                    rsi_pass = (vol_ratio > 1.25)
                else:
                    rsi_pass = True
                    
                adx_pass = (adx > 20) or (vol_ratio > 1.25)
                
                if rsi_pass and adx_pass:
                    if is_commodity_aligned(ticker):
                        if vol_ratio > 1.25:
                            buys.append(f"🟢 **{ticker} [REGULAR BUY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target Sell: `${target:.2f}` | Stop Loss: `${stop:.2f}`")
                        else:
                            buys.append(f"🟡 **{ticker} [LOW-VOLUME SCALED ENTRY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target Sell: `${target:.2f}` | Stop Loss: `${stop:.2f}`\n  *(Recommended 25-50% position size due to low volume)*")
            
            # Capitulation Reversal
            if rsi < 35 and vol_ratio > 1.25:
                if is_commodity_aligned(ticker):
                    buys.append(f"🟣 **{ticker} [CAPITULATION REVERSAL]**\n  - {rsi_line}\n  - {vol_line}\n  - Target Sell: `${target:.2f}` | Stop Loss: `${stop:.2f}`")

pnl_sign = "+" if absolute_pnl >= 0 else ""
msg = (
    f"🏁 **END-OF-DAY (EOD) SUMMARY** ({today_str}) 🏁\n\n"
    f"**TOTAL UNREALIZED P&L:** `{pnl_sign}${absolute_pnl:,.2f}` (`{pnl_sign}{percentage_pnl:.2f}%`)\n\n"
    f"**Portfolio Holdings:**\n"
)
if owned:
    msg += '\n'.join(owned)
else:
    msg += f"- 100% Cash (`${current_cash:,.2f}`). No open equity positions."

msg += f"\n- **Available Cash:** `${current_cash:,.2f} CAD`"
msg += f"\n- **Total Portfolio Equity:** `${current_equity:,.2f} CAD`"

if todays_closed:
    msg += "\n\n**Today's Realized Activity:**\n"
    for t in todays_closed:
        sign = "+" if t['pnl'] >= 0 else ""
        msg += f"- **{t['ticker']} ({t['action']}):** {sign}${t['pnl']:.2f} CAD ({sign}{t['pct']:.2f}%)\n"

msg += (
    f"\n**Cumulative Performance:**\n"
    f"- **Active Guidance Realized P&L:** `+${active_realized:,.2f} CAD` across {len(active_df)} trades ({active_wins}W / {active_losses}L — {win_rate:.1f}% Win Rate)\n"
    f"- **All-Time Realized P&L:** `+${total_all_time:,.2f} CAD`"
)

msg += "\n\n**Commodity & Macro Wrap:**\n"
msg += f"- Gold (`GC=F`): {'🟢 Positive / Green' if macro_green.get('GC=F') else '🔴 Negative / Red'}\n"
msg += f"- Crude Oil (`CL=F`): {'🟢 Positive / Green' if macro_green.get('CL=F') else '🔴 Negative / Red'}\n"

msg += "\n**Actionable EOD Signals & Next-Day Watchlist:**\n"
if sells:
    msg += '\n\n'.join(sells)
if buys:
    if sells:
        msg += '\n\n'
    msg += '\n\n'.join(buys)
if not sells and not buys:
    msg += "• No actionable overnight adjustments. Watchlist is balanced heading into tomorrow's open."

chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "5286201039"))
entry = json.dumps({'chat_id': chat_id, 'text': msg}) + '\n'
queue_file = os.path.join(base_dir, 'outgoing_queue.jsonl')
with codecs.open(queue_file, 'a', encoding='utf-8') as f:
    f.write(entry)

print("--- EOD SUMMARY MESSAGE ---")
print(msg)
