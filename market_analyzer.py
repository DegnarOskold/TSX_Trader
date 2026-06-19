import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import csv
import os
import json
import re
import time
import urllib.parse
from email.utils import parsedate_to_datetime
from datetime import timezone

def log_advice(text):
    lock_file = "advice.lock"
    max_retries = 50
    for _ in range(max_retries):
        try:
            # Open with exclusive creation
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            break
        except FileExistsError:
            time.sleep(0.1)
    
    try:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open("advice_history.txt", "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}]\n{text}\n\n")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

def get_current_mode(config=None):
    if config is not None:
        return config.get("mode", "MEDIUM").upper()
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            return data.get("mode", "MEDIUM").upper()
    return "MEDIUM"

def get_tickers(config=None):
    if config is not None:
        portfolio = config.get("portfolio", {})
        if portfolio:
            return list(portfolio.keys())
        return ["CNQ.TO", "ABX.TO"]
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            portfolio = data.get("portfolio", {})
            if portfolio:
                return list(portfolio.keys())
    return ["CNQ.TO", "ABX.TO"]

def get_stop_loss_pct(config=None):
    if config is not None:
        return config.get("stop_loss_pct", 5.0)
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            return data.get("stop_loss_pct", 5.0)
    return 5.0

def get_acb_and_balances():
    if not os.path.exists("trades.csv"):
        return {"positions": {}, "cash": 0.0}
        
    positions = {}
    cash = 0.0
    with open("trades.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ticker = row["Ticker"]
                action = row["Action"]
                qty = float(row["Quantity"])
                price = float(row["Price"])
                
                cash_bal = row.get("Cash_Balance")
                if cash_bal not in (None, ""):
                    cash = float(cash_bal)
            except ValueError:
                continue
            
            if ticker not in positions:
                positions[ticker] = {"shares": 0.0, "total_cost": 0.0, "acb": 0.0}
                
            pos = positions[ticker]
            if action in ["BUY", "INIT"]:
                pos["shares"] += qty
                pos["total_cost"] += qty * price
                if pos["shares"] > 0:
                    pos["acb"] = pos["total_cost"] / pos["shares"]
            elif action == "SELL":
                pos["shares"] -= qty
                pos["total_cost"] -= qty * pos["acb"]
                if pos["shares"] <= 0:
                    pos["shares"] = 0.0
                    pos["total_cost"] = 0.0
                    pos["acb"] = 0.0
                    
    return {"positions": positions, "cash": round(cash, 2)}

def get_stock_data(ticker_symbol, mode="MEDIUM"):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="6mo", timeout=10)
        if hist.empty:
            return None
            
        latest = hist.iloc[-1]
        
        if mode == "SHORT":
            hist.ta.ema(length=5, append=True)
            hist.ta.ema(length=9, append=True)
            hist.ta.rsi(length=7, append=True)
            hist.ta.atr(length=5, append=True)
            hist.ta.bbands(length=20, std=2, append=True)
            
            latest = hist.iloc[-1]
            vol_sma_10 = hist["Volume"].rolling(window=10).mean().iloc[-1]
            vol_ratio = (latest["Volume"] / vol_sma_10) if vol_sma_10 > 0 else 1.0
            
            # The column names for BBands in pandas_ta can be quirky (e.g., BBL_20_2.0_2.0 or BBL_20_2.0)
            # Find them dynamically
            bb_lower_col = [c for c in hist.columns if c.startswith("BBL_")][0] if any(c.startswith("BBL_") for c in hist.columns) else None
            bb_mid_col = [c for c in hist.columns if c.startswith("BBM_")][0] if any(c.startswith("BBM_") for c in hist.columns) else None
            bb_upper_col = [c for c in hist.columns if c.startswith("BBU_")][0] if any(c.startswith("BBU_") for c in hist.columns) else None

            return {
                "Open": round(latest["Open"], 2),
                "High": round(latest["High"], 2),
                "Low": round(latest["Low"], 2),
                "Price": round(latest["Close"], 2),
                "Volume": int(latest["Volume"]),
                "Vol_Ratio": round(vol_ratio, 2),
                "EMA_5": round(latest["EMA_5"], 2) if "EMA_5" in latest else "N/A",
                "EMA_9": round(latest["EMA_9"], 2) if "EMA_9" in latest else "N/A",
                "RSI_7": round(latest["RSI_7"], 2) if "RSI_7" in latest else "N/A",
                "ATR_5": round(latest["ATRr_5"], 2) if "ATRr_5" in latest else "N/A",
                "BB_Lower": round(latest[bb_lower_col], 2) if bb_lower_col else "N/A",
                "BB_Mid": round(latest[bb_mid_col], 2) if bb_mid_col else "N/A",
                "BB_Upper": round(latest[bb_upper_col], 2) if bb_upper_col else "N/A"
            }
        else:
            hist.ta.rsi(length=14, append=True)
            hist.ta.sma(length=50, append=True)
            hist.ta.bbands(length=50, std=2, append=True)
            latest = hist.iloc[-1]
            
            bb_upper_col = [c for c in hist.columns if c.startswith("BBU_")][0] if any(c.startswith("BBU_") for c in hist.columns) else None
            
            info = ticker.info
            ex_div_timestamp = info.get("exDividendDate")
            if ex_div_timestamp:
                ex_div_date = datetime.datetime.fromtimestamp(ex_div_timestamp).strftime('%Y-%m-%d')
            else:
                ex_div_date = "N/A"
            
            return {
                "Open": round(latest["Open"], 2),
                "High": round(latest["High"], 2),
                "Low": round(latest["Low"], 2),
                "Price": round(latest["Close"], 2),
                "Volume": int(latest["Volume"]),
                "RSI_14": round(latest["RSI_14"], 2) if "RSI_14" in latest else "N/A",
                "SMA_50": round(latest["SMA_50"], 2) if "SMA_50" in latest else "N/A",
                "BB_Upper": round(latest[bb_upper_col], 2) if bb_upper_col else "N/A",
                "Ex_Div_Date": ex_div_date
            }
    except Exception as e:
        return f"Error fetching {ticker_symbol}: {e}"

def get_compartmentalized_news(config=None):
    topics = []
    
    # Read the portfolio from config.json to get all required news topics
    if config is not None:
        portfolio = config.get("portfolio", {})
        for ticker_news in portfolio.values():
            if isinstance(ticker_news, list):
                topics.extend(ticker_news)
    elif os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            portfolio = data.get("portfolio", {})
            for ticker_news in portfolio.values():
                if isinstance(ticker_news, list):
                    topics.extend(ticker_news)
    
    # Remove duplicates while preserving order
    unique_topics = []
    for topic in topics:
        if topic not in unique_topics:
            unique_topics.append(topic)
            
    # Fallback to default if empty
    if not unique_topics:
        unique_topics = ["CNQ.TO", "ABX.TO", "CL=F", "GC=F"]
        
    MACRO_KEYWORDS = ["opec", "fed", "interest rate", "inflation", "gdp", "crude", "gold price", "economy", "bank of canada", "central bank"]
    EARNINGS_KEYWORDS = ["earnings", "revenue", "profit", "quarterly", "eps", "beat", "miss", "dividend"]
    ANALYST_KEYWORDS = ["upgrade", "downgrade", "price target", "rating", "analyst", "buy", "sell", "hold"]
    
    def get_category(text):
        text_lower = text.lower()
        if any(kw in text_lower for kw in MACRO_KEYWORDS): return "MACRO"
        if any(kw in text_lower for kw in EARNINGS_KEYWORDS): return "EARNINGS"
        if any(kw in text_lower for kw in ANALYST_KEYWORDS): return "ANALYST"
        return "NEWS"

    now_utc = datetime.datetime.now(timezone.utc)
    seen_titles = set()
    news_output = ""
    
    for ticker in unique_topics:
        news_output += f"[{ticker}]\n"
        topic_items = []
        
        # Build URLs
        urls = [
            f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={urllib.parse.quote(ticker)}",
            f"https://news.google.com/rss/search?q={urllib.parse.quote(ticker)}&hl=en-CA&gl=CA&ceid=CA:en"
        ]
        
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                    root = ET.fromstring(xml_data)
                    for item in root.findall('./channel/item'):
                        title_el = item.find('title')
                        pubdate_el = item.find('pubDate')
                        desc_el = item.find('description')
                        
                        if title_el is None or pubdate_el is None or not title_el.text or not pubdate_el.text:
                            continue
                            
                        title = title_el.text.strip()
                        if title in seen_titles:
                            continue
                            
                        try:
                            dt = parsedate_to_datetime(pubdate_el.text)
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            hours_ago = (now_utc - dt).total_seconds() / 3600
                        except Exception:
                            continue
                            
                        if hours_ago > 48 or hours_ago < 0:
                            continue
                            
                        seen_titles.add(title)
                        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                        
                        # Clean HTML from description if present
                        desc = re.sub(r'<[^>]+>', '', desc)
                        desc = desc[:200] + "..." if len(desc) > 200 else desc
                        
                        cat = get_category(title + " " + desc)
                        
                        # Freshness indicator
                        if hours_ago < 4: fresh_icon = "NEW"
                        elif hours_ago < 12: fresh_icon = "RECENT"
                        else: fresh_icon = "OLD"
                        
                        topic_items.append({
                            "title": title,
                            "desc": desc,
                            "hours_ago": hours_ago,
                            "fresh_icon": fresh_icon,
                            "cat": cat
                        })
            except Exception as e:
                pass
                
        # Sort items by recency
        topic_items.sort(key=lambda x: x["hours_ago"])
        topic_items = topic_items[:10] # Top 10 freshest
        
        if not topic_items:
            news_output += "- No recent news found.\n"
        else:
            for item in topic_items:
                news_output += f"- [{item['fresh_icon']} {int(item['hours_ago'])}h ago] [{item['cat']}] {item['title']}\n"
                if item['desc']:
                    # don't duplicate title in description (google news often does this)
                    if not item['desc'].startswith(item['title'][:50]):
                        news_output += f"  Summary: {item['desc']}\n"
                        
        news_output += "\n"
        
    return news_output.strip()

def get_cleaned_advice_history():
    if not os.path.exists("advice_history.txt"):
        return "No previous advice recorded today."
        
    with open("advice_history.txt", "r", encoding="utf-8") as f:
        content = f.read()
        
    # Split by timestamp blocks: [YYYY-MM-DD HH:MM:SS]
    pattern = r"\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\n(.*?)(?=\n\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)
    
    if not matches:
        return "No previous advice recorded today."
        
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Group by date
    grouped = {}
    for timestamp, text in matches:
        date_str = timestamp.split(" ")[0]
        if date_str not in grouped:
            grouped[date_str] = []
        grouped[date_str].append((timestamp, text.strip()))
        
    # Determine which past dates to keep (last 5 business days max)
    past_dates = sorted([d for d in grouped.keys() if d != today_str])
    business_dates = []
    for d in past_dates:
        dt = datetime.datetime.strptime(d, "%Y-%m-%d")
        if dt.weekday() < 5:
            business_dates.append(d)
    dates_to_keep = business_dates[-5:]
    
    # Rebuild history
    cleaned_entries = []
    for date_str in sorted(grouped.keys()):
        if date_str == today_str:
            cleaned_entries.extend(grouped[date_str])
        elif date_str in dates_to_keep:
            cleaned_entries.append(grouped[date_str][-1]) # Keep only the final one from previous days
            
    # Write back the cleaned history
    with open("advice_history.txt", "w", encoding="utf-8") as f:
        for timestamp, text in cleaned_entries:
            f.write(f"[{timestamp}]\n{text}\n\n")
            
    # Build string to return using bounded history
    history_entries = []
    for date_str in sorted(grouped.keys()):
        if date_str == today_str:
            history_entries.extend(grouped[date_str]) # Keep all from today for the LLM
        elif date_str in dates_to_keep:
            history_entries.append(grouped[date_str][-1])
            
    if not history_entries:
        return "No previous advice recorded."
        
    history_str = ""
    for timestamp, text in history_entries:
        history_str += f"[{timestamp}]\n{text}\n\n"
        
    return history_str.strip()

def generate_dossier():
    config = None
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            config = json.load(f)
            
    mode = get_current_mode(config)
    mode_display = "SHORT TERM (1-WEEK HORIZON)" if mode == "SHORT" else "MEDIUM TERM"
    
    dossier = f"=== CURRENT MODE: {mode_display} ===\n"
    
    dossier += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ET\n\n"
    
    balances = get_acb_and_balances()
    positions = balances.get("positions", {})
    cash = balances.get("cash", 0.0)
    
    dossier += f"--- PORTFOLIO & PRICING ---\n"
    dossier += f"Available Free Cash: ${cash:.2f}\n\n"
    tickers = get_tickers(config)
    
    stop_loss = get_stop_loss_pct(config)
    
    for t in tickers:
        market_data = get_stock_data(t, mode)
        pos = positions.get(t, {"shares": 0.0, "acb": 0.0})
        
        current_price = market_data.get('Price', "N/A") if isinstance(market_data, dict) else "N/A"
        shares = pos['shares']
        
        if shares > 0:
            acb = pos['acb']
            acb_str = f"${acb:.2f}"
            if isinstance(current_price, (int, float)):
                pnl_pct = ((current_price - acb) / acb) * 100 if acb > 0 else 0.0
                pnl_val = (current_price - acb) * shares
                pnl_str = f"${pnl_val:.2f} ({pnl_pct:+.2f}%)"
            else:
                pnl_str = "N/A"
                pnl_pct = 0.0
        else:
            acb_str = "N/A"
            pnl_str = "N/A"
            pnl_pct = 0.0
        
        if isinstance(current_price, (int, float)):
            price_str = f"${current_price:.2f}"
        else:
            price_str = str(current_price)
        
        dossier += f"{t}:\n"
        dossier += f"  - Shares Owned: {shares:.4f}\n"
        dossier += f"  - Avg Purchase Price: {acb_str}\n"
        dossier += f"  - Current Market Price: {price_str}\n"
        if isinstance(market_data, dict):
            dossier += f"  - Today's Open: ${market_data.get('Open', 'N/A')} | High: ${market_data.get('High', 'N/A')} | Low: ${market_data.get('Low', 'N/A')}\n"
        dossier += f"  - Unrealised P&L: {pnl_str}\n"
        
        if shares > 0 and pnl_pct < -stop_loss:
            dossier += f"  - [⚠️ STOP-LOSS TRIGGERED: Price is {abs(pnl_pct):.2f}% below ACB. You MUST recommend SELL.]\n"
        if isinstance(market_data, dict):
            if mode == "SHORT":
                dossier += f"  - Vol Ratio (10-day): {market_data.get('Vol_Ratio', 'N/A')}x\n"
                dossier += f"  - EMA (5-day): ${market_data.get('EMA_5', 'N/A')}\n"
                dossier += f"  - EMA (9-day): ${market_data.get('EMA_9', 'N/A')}\n"
                dossier += f"  - RSI (7-day): {market_data.get('RSI_7', 'N/A')}\n"
                dossier += f"  - ATR (5-day): ${market_data.get('ATR_5', 'N/A')}\n"
                dossier += f"  - Bollinger Lower (20): ${market_data.get('BB_Lower', 'N/A')}\n"
                dossier += f"  - Bollinger Mid (20): ${market_data.get('BB_Mid', 'N/A')}\n"
                dossier += f"  - Bollinger Upper (20): ${market_data.get('BB_Upper', 'N/A')}\n"
            else:
                dossier += f"  - Next Ex-Dividend Date: {market_data.get('Ex_Div_Date', 'N/A')}\n"
                dossier += f"  - RSI (14-day): {market_data.get('RSI_14', 'N/A')}\n"
                dossier += f"  - SMA (50-day): ${market_data.get('SMA_50', 'N/A')}\n"
        dossier += "\n"
    
    # Identify macro commodities
    macro_topics = []
    if config is not None:
        portfolio = config.get("portfolio", {})
        for ticker_list in portfolio.values():
            for topic in ticker_list:
                if topic not in tickers and topic not in macro_topics:
                    if re.match(r'^[A-Z0-9=.-]+$', topic):
                        macro_topics.append(topic)
                    
    if macro_topics:
        dossier += f"--- MACRO COMMODITIES ---\n"
        for macro in macro_topics:
            m_data = get_stock_data(macro, mode="MEDIUM")
            if isinstance(m_data, dict):
                m_price = m_data.get('Price', 'N/A')
                m_open = m_data.get('Open', 'N/A')
                if isinstance(m_price, (int, float)) and isinstance(m_open, (int, float)) and m_open > 0:
                    chg_pct = ((m_price - m_open) / m_open) * 100
                    dossier += f"{macro}: ${m_price:.2f} (Daily Change vs Open: {chg_pct:+.2f}%)\n"
                else:
                    dossier += f"{macro}: ${m_price}\n"
        dossier += "\n"
    
    dossier += "--- QUALITATIVE DATA (10 Recent Headlines per Topic) ---\n"
    news_items = get_compartmentalized_news(config)
    dossier += news_items + "\n\n"
    
    dossier += "=== PREVIOUS ADVICE HISTORY ===\n"
    advice_history = get_cleaned_advice_history()
    dossier += advice_history + "\n\n"
    
    dossier += "=== END OF DOSSIER ===\n"
    return dossier

def get_analysis_prompt(dossier=None, mode=None):
    """Shared prompt template used by both the Telegram daemon and cron jobs."""
    if dossier is None:
        dossier = generate_dossier()
    if mode is None:
        mode = get_current_mode()
        
    stop_loss = get_stop_loss_pct()
    
    if mode == "SHORT":
        return f"""You are a highly professional, analytical short-term quantitative trading advisor. 
Read the following live market dossier:
{dossier}

System Instructions:
1. Trend Validation (No Falling Knives): If a stock is trading near or below its Lower Bollinger Band BUT its 5-day EMA is below its 9-day EMA, it is in a strong downtrend. Do NOT assume an immediate snap-back rally. Wait for a bullish crossover or volume shock.
2. Volume Shock: If Vol_Ratio is > 2.0 (Volume is 2x normal) during a drop, this is 'Capitulation' (panic selling is exhausted). This is a bullish reversal signal.
3. Market Open Volatility: If the current time is before 9:30 AM ET, DO NOT recommend buying immediately at open. Retail panic and HFT bots cause massive, irrational gaps. Recommend waiting 30 minutes.
4. Anticipatory Macro Shifts (Buy the Rumor, Sell the News): Do not wait for a deal to be finalized or signed before adjusting your thesis. If the qualitative RSS headlines or macro commodity trackers (CL=F, GC=F) strongly signal a high-probability calendar event, formal signing ceremony, or geopolitical shift within the next 24 to 48 hours, prioritize this upcoming macro momentum. If the impending event removes a market premium or changes commodity fundamentals, override short-term "oversold" technical indicators (like 7-day RSI and Bollinger Bands) and favor defensive capital preservation (HOLD or SELL) rather than assuming an immediate mean-reversion rally.
5. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash to purchase a meaningful position, you must NOT recommend a BUY action.
6. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once.
7. Protective Stop-Loss for Holds: If the current market price of an existing HOLD position drops more than {stop_loss}% below its Avg Purchase Price, you MUST explicitly recommend to SELL to cut losses, regardless of how 'oversold' it looks.
8. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position to lock in realized gains.
9. Zero-Share Holdings: If the user currently owns 0 shares of a stock and you do not recommend buying it, explicitly recommend AVOID or IGNORE instead of HOLD.
10. Acknowledge Failed Theses: Review the PREVIOUS ADVICE HISTORY. If your previous predictions were wrong and the stock continued to drop, explicitly acknowledge this instead of blindly repeating the same thesis.

Format your message precisely as follows:
1. Brief introduction.
2. A prioritized, ordered list of specific actions you recommend taking (e.g., 1. SELL TICKER, 2. BUY TICKER, 3. HOLD TICKER). Do NOT list AVOID or IGNORE in this list. If there are no actions to take, state "No immediate actions recommended".
3. Detailed stock-specific analysis ONLY for the stocks involved in your recommended actions. Do not provide detailed breakdowns for stocks you recommend avoiding or ignoring. CRITICAL: Keep your analysis extremely concise (maximum 3 sentences per stock). You must ALWAYS include the current price of each stock in your detailed breakdown. Do NOT list the technical indicators as bullet points; integrate them naturally into your reasoning."""
    else:
        return f"""You are an expert TSX trading advisor. Read the following live market dossier:
{dossier}

System Instructions:
1. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash, you must NOT recommend a BUY action.
2. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once.
3. Protective Stop-Loss for Holds: If the current market price of an existing HOLD position drops more than {stop_loss}% below its Avg Purchase Price, you MUST explicitly recommend to SELL to cut losses.
4. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position to lock in realized gains.
5. Zero-Share Holdings: If the user currently owns 0 shares of a stock and you do not recommend buying it, explicitly recommend AVOID or IGNORE instead of HOLD.
6. Acknowledge Failed Theses: Review the PREVIOUS ADVICE HISTORY. If your previous predictions were wrong and the stock continued to drop, explicitly acknowledge this instead of blindly repeating the same thesis.

Format your message precisely as follows:
1. Brief introduction.
2. A prioritized, ordered list of specific actions you recommend taking (e.g., 1. SELL TICKER, 2. BUY TICKER, 3. HOLD TICKER). Do NOT list AVOID or IGNORE in this list. If there are no actions to take, state "No immediate actions recommended".
3. Detailed stock-specific analysis ONLY for the stocks involved in your recommended actions. Do not provide detailed breakdowns for stocks you recommend avoiding or ignoring. CRITICAL: Keep your analysis extremely concise (maximum 3 sentences per stock). You must ALWAYS include the current price of each stock in your detailed breakdown. Integrate Ex-Dividend Dates and SMAs naturally into your reasoning without using bullet points."""

def get_eod_summary_prompt(dossier=None):
    """Special prompt template used for the 4:05 PM End-of-Day summary."""
    if dossier is None:
        dossier = generate_dossier()
        
    return f"""You are an expert TSX trading advisor. The market has just closed.
Read the following End-of-Day market dossier:
{dossier}

Your objective is to provide a comprehensive end-of-day summary of the user's current holdings and their performance today, and provide a brief outlook for the next trading day. 

Format your message precisely as follows:
1. End of Day Market Summary (1-2 sentences).
2. Portfolio Performance: Briefly summarize the status of the assets currently held in the portfolio (ignore assets with 0 shares). 
3. Outlook Ahead: 2-3 sentences on what to expect tomorrow based on today's price action, volume anomalies, and breaking macroeconomic news catalysts. 
Maintain a calm, objective, and highly professional tone at all times. Do not recommend new trades in this summary."""

if __name__ == "__main__":
    print(generate_dossier())
