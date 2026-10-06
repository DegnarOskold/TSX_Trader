import json
import codecs
import re
import sys
import pandas as pd
import yfinance as yf
from datetime import datetime
import os

# Enforce market window between 9:30 AM and 4:00 PM ET
now = datetime.now()
mins = now.hour * 60 + now.minute
if not (565 <= mins <= 965):
    print(f"Current time {now.strftime('%I:%M %p')} is outside the active 9:30 AM - 4:00 PM window. Skipping scan.")
    sys.exit(0)

# Calculate True P&L
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, 'trades.csv')
df = pd.read_csv(csv_path)

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

current_equity = df.iloc[-1]['Cash_Balance']
for t, shares in current_shares.items():
    data = yf.Ticker(t).history(period="1d")
    price = None
    if not data.empty and pd.notna(data['Close'].iloc[-1]):
        price = data['Close'].iloc[-1]
    else:
        # Fallback to 5d history if 1d is temporarily empty (e.g. market open print lag)
        hist_5d = yf.Ticker(t).history(period="5d")
        if not hist_5d.empty and pd.notna(hist_5d['Close'].iloc[-1]):
            price = hist_5d['Close'].iloc[-1]
        elif t in cost_bases:
            # Fallback to cost basis if network/API temporarily unavailable
            price = cost_bases[t]
            
    if price is not None:
        current_equity += price * shares

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

sys.path.append(base_dir)
import market_analyzer
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
        
        ema_cross = next((l for l in lines if 'EMA Crossover' in l), None)
        
        if unrealized:
            pnl_line = unrealized[0].strip()
            match = re.search(r'\(([-+]\d+\.\d+)%\)', pnl_line)
            flag = ""
            if match:
                pct = float(match.group(1))
                if pct > 2.0:
                    flag = " 🚀 *(PROFIT TARGET: >2% gain! Move Stop Loss up to Breakeven)*"
                elif pct < -5.0:
                    flag = " 🛑 *(STOP LOSS ALERT)*"
                    sells.append(f"🔴 **SELL ALERT: {ticker} (Stop Loss Triggered @ -5%)**")
                elif pct < 0 and days_held > 4 and ema_cross and 'BEARISH' in ema_cross:
                    flag = " 📉 *(STAGNATION EXIT: Held > 4 days, Negative, Bearish Cross. SELL)*"
                    sells.append(f"🔴 **SELL ALERT: {ticker} (Stagnation Exit)**")
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
            
            # STANDARD BUYS ALLOWED BEFORE 11:30 AM
            is_restricted_time = False
            current_hour = datetime.now().hour
            current_minute = datetime.now().minute
            time_in_minutes = current_hour * 60 + current_minute
            
            if 690 <= time_in_minutes < 840:
                is_restricted_time = True
                
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
                    if is_commodity_aligned(ticker) and not is_restricted_time:
                        if vol_ratio > 1.25:
                            buys.append(f"🟢 **{ticker} [REGULAR BUY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`")
                        else:
                            buys.append(f"🟡 **{ticker} [LOW-VOLUME SCALED ENTRY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`\n  *(Recommended 25-50% position size due to low volume)*")
            
            # Capitulation Reversal
            if rsi < 35 and vol_ratio > 1.25:
                if is_commodity_aligned(ticker):
                    if not is_restricted_time:
                        buys.append(f"🟣 **{ticker} [CAPITULATION REVERSAL]**\n  - {rsi_line}\n  - {vol_line}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`")


pnl_sign = "+" if absolute_pnl >= 0 else ""
current_time = datetime.now().strftime('%I:%M %p')
msg = (
    f"⏱️ **{current_time} INTERVAL SCAN** ⏱️\n\n"
    f"**TOTAL UNREALIZED P&L:** `{pnl_sign}${absolute_pnl:,.2f}` (`{pnl_sign}{percentage_pnl:.2f}%`)\n\n"
    f"**Portfolio Status:**\n"
)
if owned:
    msg += '\n'.join(owned)
else:
    msg += f"- 100% Cash (${df.iloc[-1]['Cash_Balance']:,.2f}). No open positions."

msg += "\n\n**Actionable Alerts:**\n"
if sells:
    msg += '\n\n'.join(sells)
if buys:
    if sells:
        msg += '\n\n'
    msg += '\n\n'.join(buys)
if not sells and not buys:
    msg += "- Holding steady. No immediate technical setups or sell triggers."

chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "5286201039"))
entry = json.dumps({'chat_id': chat_id, 'text': msg}) + '\n'
queue_file = os.path.join(base_dir, 'outgoing_queue.jsonl')
with codecs.open(queue_file, 'a', encoding='utf-8') as f:
    f.write(entry)

print("Interval scan report sent!")
