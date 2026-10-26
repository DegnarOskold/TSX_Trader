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
for sym in ['GC=F', 'CL=F', 'HG=F']:
    data = yf.Ticker(sym).history(period="2d")
    if len(data) >= 2:
        close_today = data['Close'].iloc[-1]
        close_yday = data['Close'].iloc[-2]
        macro_green[sym] = bool(close_today > close_yday)
    else:
        macro_green[sym] = True

def is_commodity_aligned(ticker):
    # Precious metals (Gold & Silver)
    if ticker in ['AEM.TO', 'ABX.TO', 'K.TO', 'FNV.TO', 'WPM.TO', 'PAAS.TO', 'AGI.TO']:
        return macro_green.get('GC=F', True)
    # Energy / Crude Oil
    if ticker in ['CNQ.TO', 'SU.TO', 'CVE.TO', 'TOU.TO', 'IMO.TO']:
        return macro_green.get('CL=F', True)
    # Diversified Base Metals / Copper
    if ticker in ['TECK-B.TO']:
        return macro_green.get('HG=F', True)
    return True

def get_cycle_days_held(trades_df, ticker_sym):
    ticker_trades = trades_df[trades_df['Ticker'] == ticker_sym].copy()
    if ticker_trades.empty:
        return 0
    zero_idx = ticker_trades[ticker_trades['Shares_Balance'] == 0].index
    if not zero_idx.empty:
        cycle_trades = ticker_trades.loc[zero_idx[-1] + 1:]
    else:
        cycle_trades = ticker_trades
    buy_trades = cycle_trades[cycle_trades['Action'] == 'BUY']
    if buy_trades.empty:
        return 0
    first_buy_str = buy_trades['Date'].iloc[0]
    try:
        first_buy_date = datetime.strptime(first_buy_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        first_buy_date = datetime.strptime(first_buy_str, '%Y-%m-%d')
    return (datetime.now() - first_buy_date).days

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
        
        # Technical & price parsing for owned positions
        price_val = None
        price_line = next((l for l in lines if 'Current Market Price' in l), None)
        if price_line and '$' in price_line:
            try:
                price_val = float(price_line.split('$')[1].strip())
            except Exception:
                pass

        open_val = None
        open_line = next((l for l in lines if "Today's Open:" in l), None)
        if open_line and "Today's Open: $" in open_line:
            try:
                open_val = float(open_line.split("Today's Open: $")[1].split(' |')[0].strip())
            except Exception:
                pass

        prev_close_val = None
        prev_close_line = next((l for l in lines if 'Previous Close:' in l), None)
        if prev_close_line and 'Previous Close: $' in prev_close_line:
            try:
                prev_close_val = float(prev_close_line.split('Previous Close: $')[1].split(' (')[0].strip())
            except Exception:
                pass

        ema_5_val = None
        ema_5_line = next((l for l in lines if 'EMA (5-day):' in l), None)
        if ema_5_line and '$' in ema_5_line:
            try:
                ema_5_val = float(ema_5_line.split('$')[1].strip())
            except Exception:
                pass

        ema_9_val = None
        ema_9_line = next((l for l in lines if 'EMA (9-day):' in l), None)
        if ema_9_line and '$' in ema_9_line:
            try:
                ema_9_val = float(ema_9_line.split('$')[1].strip())
            except Exception:
                pass

        ema_cross = next((l for l in lines if 'EMA Crossover' in l), "")
        days_held = get_cycle_days_held(df, ticker)
        
        if unrealized:
            pnl_line = unrealized[0].strip()
            match = re.search(r'\(([-+]\d+\.\d+)%\)', pnl_line)
            flag = ""
            if match:
                pct = float(match.group(1))
                if pct > 2.0:
                    flag = " 🚀 *(PROFIT TARGET: >2% gain! Move Stop Loss up to Breakeven)*"
                elif pct < -5.0:
                    if ticker in ['CLS.TO', 'CCO.TO']:
                        flag = " 🛡️ *(COMMITTED RECOVERY HOLD: Fundamentals intact, waiting for recovery)*"
                    else:
                        flag = " 🛑 *(STOP LOSS ALERT)*"
                        sells.append(f"🔴 **SELL ALERT: {ticker} (Stop Loss Triggered @ -5%)**")
                elif pct < 0 and days_held > 4:
                    # Stagnation rule evaluation:
                    # 1. Technical breakdown: Bearish cross OR price below both EMA-5 and EMA-9
                    tech_breakdown = ('BEARISH' in ema_cross) or (
                        price_val is not None and ema_5_val is not None and ema_9_val is not None and price_val < min(ema_5_val, ema_9_val)
                    )
                    
                    # 2. Green-Day Rally Deferral: Price > Open AND Price >= Prev_Close * 1.01 (+1% intraday gain)
                    is_recovering = (
                        price_val is not None and open_val is not None and price_val > open_val and
                        prev_close_val is not None and price_val >= (prev_close_val * 1.01)
                    )
                    
                    if is_recovering:
                        flag = " ⏳ *(STAGNATION DEFERRED: Held > 4d, but recovering intraday: Green candle & +1% above prev close)*"
                    elif tech_breakdown:
                        if ticker in ['CLS.TO', 'CCO.TO']:
                            flag = " 🛡️ *(COMMITTED RECOVERY HOLD: Stagnant but held for fundamental turnaround)*"
                        else:
                            flag = " 📉 *(STAGNATION EXIT: Held > 4 days, Negative, Technical Breakdown. SELL)*"
                            sells.append(f"🔴 **SELL ALERT: {ticker} (Stagnation Exit: Held > 4 days, Negative, Breakdown)**")
            owned.append(f"- **{ticker}:** {pnl_line.split(': ')[1]}{flag}")

    elif 'Shares Owned: 0.0000' in block:
        has_earnings_risk = ('EARNINGS RISK' in block)
        ema_cross = next((l for l in lines if 'EMA Crossover' in l), None)
        rsi_line = next((l for l in lines if 'RSI' in l), None)
        adx_line = next((l for l in lines if 'ADX' in l), None)
        vol_line = next((l for l in lines if 'Vol Ratio' in l), None)
        
        if rsi_line and adx_line and ema_cross and vol_line:
            cross = ema_cross.split(': ')[1]
            rsi = float(rsi_line.split(': ')[1])
            adx = float(adx_line.split(': ')[1])
            vol_ratio = float(vol_line.split(': ')[1].replace('x',''))
            
            # Technical parsing for target and reversal confirmation
            price_line = next((l for l in lines if 'Current Market Price' in l), None)
            bb_mid_line = next((l for l in lines if 'Bollinger Mid' in l), None)
            atr_line = next((l for l in lines if 'ATR (' in l), None)

            open_val = None
            open_line = next((l for l in lines if "Today's Open:" in l), None)
            if open_line and "Today's Open: $" in open_line:
                try:
                    open_val = float(open_line.split("Today's Open: $")[1].split(' |')[0].strip())
                except Exception:
                    pass

            pct_from_low = None
            trend_line = next((l for l in lines if 'Intraday Trend:' in l), None)
            if trend_line and '% above Low of Day' in trend_line:
                try:
                    pct_from_low = float(trend_line.split('Intraday Trend: ')[1].split('%')[0].strip())
                except Exception:
                    pass
            
            target = 0
            stop = 0
            if price_line and bb_mid_line and atr_line:
                try:
                    price = float(price_line.split('$')[1].strip())
                    bb_mid = float(bb_mid_line.split('$')[1].strip())
                    atr = float(atr_line.split('$')[1].strip())
                    
                    # Target calculation with minimum +2.5% hurdle
                    min_target = price * 1.025
                    if pd.notna(bb_mid) and bb_mid >= min_target:
                        target = bb_mid
                    else:
                        target = max(price + (1.5 * atr), min_target)
                    stop = price * 0.95
                except Exception:
                    continue
            
            if pd.isna(target) or pd.isna(stop) or target <= 0 or stop <= 0:
                continue
            
            # TIME RESTRICTIONS:
            # 1. Opening Chop Guard: 9:30 AM - 10:00 AM ET (< 600 mins) to avoid opening cross volatility
            # 2. Midday Fake-Out Window: 11:30 AM - 2:00 PM ET (690 <= mins < 840)
            is_restricted_time = False
            current_hour = datetime.now().hour
            current_minute = datetime.now().minute
            time_in_minutes = current_hour * 60 + current_minute
            
            if time_in_minutes < 600 or (690 <= time_in_minutes < 840):
                is_restricted_time = True
                
            if 'BULLISH' in cross and not has_earnings_risk:
                # STRICT OVERBOUGHT & ADX FILTER (No double-bypass on volume)
                rsi_pass = (rsi <= 65) or (rsi <= 75 and vol_ratio > 1.25 and adx > 20)
                adx_pass = (adx > 20) or (vol_ratio > 1.25 and rsi <= 65)
                
                if rsi_pass and adx_pass:
                    if is_commodity_aligned(ticker) and not is_restricted_time:
                        if vol_ratio > 1.25:
                            buys.append(f"🟢 **{ticker} [REGULAR BUY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`")
                        else:
                            buys.append(f"🟡 **{ticker} [LOW-VOLUME SCALED ENTRY]**\n  - {ema_cross}\n  - {rsi_line}\n  - {adx_line}\n  - {vol_line}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`\n  *(Recommended 25-50% position size due to low volume)*")
            
            # Capitulation Reversal:
            # Requires oversold RSI (<35), capitulation volume ratio (>1.25x),
            # commodity macro alignment, not in restricted trading window,
            # no impending earnings risk, AND Anti-Knife-Catch confirmation:
            # (intraday green candle Price > Open AND confirmed rebound >= 1.50% from Low of Day).
            if rsi < 35 and vol_ratio > 1.25 and not has_earnings_risk:
                rebound_confirmed = True
                if open_val is not None and price <= open_val:
                    rebound_confirmed = False
                if pct_from_low is not None and pct_from_low < 1.50:
                    rebound_confirmed = False
                
                if rebound_confirmed and is_commodity_aligned(ticker):
                    if not is_restricted_time:
                        trend_info = f"\n  - Intraday Trend: {pct_from_low:.2f}% above Low" if pct_from_low is not None else ""
                        buys.append(f"🟣 **{ticker} [CAPITULATION REVERSAL]**\n  - {rsi_line}\n  - {vol_line}{trend_info}\n  - Target: `${target:.2f}` | Stop Loss: `${stop:.2f}`")


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
