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

def get_current_mode():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            return data.get("mode", "MEDIUM").upper()
    return "MEDIUM"

def get_tickers():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            data = json.load(f)
            portfolio = data.get("portfolio", {})
            if portfolio:
                return list(portfolio.keys())
    return ["CNQ.TO", "ABX.TO"]

def get_acb_and_balances():
    if not os.path.exists("trades.csv"):
        return {"positions": {}, "cash": 0.0}
        
    positions = {}
    cash = 0.0
    with open("trades.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["Ticker"]
            action = row["Action"]
            qty = float(row["Quantity"])
            price = float(row["Price"])
            
            cash_bal = row.get("Cash_Balance")
            if cash_bal is not None:
                cash = float(cash_bal)
            
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
        hist = ticker.history(period="6mo")
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
            latest = hist.iloc[-1]
            
            info = ticker.info
            ex_div_timestamp = info.get("exDividendDate")
            if ex_div_timestamp:
                ex_div_date = datetime.datetime.fromtimestamp(ex_div_timestamp).strftime('%Y-%m-%d')
            else:
                ex_div_date = "N/A"
            
            return {
                "Price": round(latest["Close"], 2),
                "Volume": int(latest["Volume"]),
                "RSI_14": round(latest["RSI_14"], 2) if "RSI_14" in latest else "N/A",
                "SMA_50": round(latest["SMA_50"], 2) if "SMA_50" in latest else "N/A",
                "Ex_Div_Date": ex_div_date
            }
    except Exception as e:
        return f"Error fetching {ticker_symbol}: {e}"

def get_compartmentalized_news():
    topics = []
    
    # Read the portfolio from config.json to get all required news topics
    if os.path.exists("config.json"):
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
    
    news_output = ""
    for ticker in unique_topics:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        news_output += f"[{ticker}]\n"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                items = root.findall('./channel/item')[:10]
                if not items:
                    news_output += "- No recent news found.\n"
                for item in items:
                    title = item.find('title').text
                    pubDate = item.find('pubDate').text
                    news_output += f"- {title} ({pubDate})\n"
        except Exception as e:
            news_output += f"- Error fetching news: {e}\n"
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
        
    # Determine which past dates to keep (last 5 days max)
    past_dates = sorted([d for d in grouped.keys() if d != today_str])
    dates_to_keep = past_dates[-5:]
    
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
            
    # Build string to return
    if not cleaned_entries:
        return "No previous advice recorded."
        
    history_str = ""
    for timestamp, text in cleaned_entries:
        history_str += f"[{timestamp}]\n{text}\n\n"
        
    return history_str.strip()

def generate_dossier():
    mode = get_current_mode()
    mode_display = "SHORT TERM (1-WEEK HORIZON)" if mode == "SHORT" else "MEDIUM TERM"
    
    dossier = f"=== CURRENT MODE: {mode_display} ===\n"
    
    if mode == "SHORT":
        dossier += "=== SYSTEM AI INSTRUCTIONS (SHORT TERM MODE) ===\n"
        dossier += "1. Mean Reversion: If a stock is trading near or below its Lower Bollinger Band (BB_Lower), it is mathematically 'stretched'. Expect a short-term snap-back rally.\n"
        dossier += "2. Volume Shock: If Vol_Ratio is > 2.0 (Volume is 2x normal) during a drop, this is 'Capitulation' (panic selling is exhausted). This is a bullish reversal signal.\n"
        dossier += "3. Market Open Volatility: If the current time is before 9:30 AM ET, DO NOT recommend buying immediately at open. Retail panic and HFT bots cause massive, irrational gaps. Recommend waiting 30 minutes for the 'Gap and Snap-Back' or 'Gap and Crap' to settle before executing trades.\n"
        dossier += "4. Finalized Macro Events: If headlines indicate a deal is reached or finalized, anticipate that markets have already priced it in. Expect traders to take profits and the asset to move inversely to the immediate sentiment of the headline. Factor this into your reasoning naturally without explicitly quoting these instructions or using jargon like 'Sell the News'.\n\n"

    dossier += "=== TSX TRADING ADVISOR DOSSIER ===\n"
    dossier += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ET\n\n"
    
    balances = get_acb_and_balances()
    positions = balances.get("positions", {})
    cash = balances.get("cash", 0.0)
    
    dossier += f"--- PORTFOLIO & PRICING ---\n"
    dossier += f"Available Free Cash: ${cash:.2f}\n\n"
    tickers = get_tickers()
    
    for t in tickers:
        market_data = get_stock_data(t, mode)
        pos = positions.get(t, {"shares": 0.0, "acb": 0.0})
        
        current_price = market_data.get('Price', "N/A") if isinstance(market_data, dict) else "N/A"
        shares = pos['shares']
        
        if shares > 0:
            acb_str = f"${pos['acb']:.2f}"
        else:
            acb_str = "N/A"
        
        if isinstance(current_price, (int, float)):
            price_str = f"${current_price:.2f}"
        else:
            price_str = str(current_price)
        
        dossier += f"{t}:\n"
        dossier += f"  - Shares Owned: {shares:.4f}\n"
        dossier += f"  - Avg Purchase Price: {acb_str}\n"
        dossier += f"  - Current Market Price: {price_str}\n"
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
    
    dossier += "--- QUALITATIVE DATA (10 Recent Headlines per Topic) ---\n"
    news_items = get_compartmentalized_news()
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
    
    if mode == "SHORT":
        return f"""You are a highly professional, analytical short-term quantitative trading advisor. 
Read the following live market dossier:
{dossier}

Your objective is to identify short-term capital gains over a 5-to-7 day trading window using quantitative metrics. Ignore long-term valuation metrics. Base your analysis objectively on immediate momentum, volume anomalies, technical crossovers (EMA/Bollinger), and breaking macroeconomic news catalysts. Maintain a calm, objective, and highly professional tone at all times.
5. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash to purchase a meaningful position, you must NOT recommend a BUY action.
6. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once, to account for continued intraday volatility.
7. Invalidation Levels (Stop Losses): Whenever you recommend a BUY for a mean-reversion bounce, you MUST provide a strict technical invalidation level (a Stop Loss) where your thesis is proven wrong, to protect the user's downside.
8. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position (e.g., Sell 50%) to lock in realized gains.

Format your message precisely as follows:
1. Brief introduction.
2. A prioritized, ordered list of specific actions you recommend taking (e.g., 1. SELL TICKER, 2. BUY TICKER).
3. Detailed stock-specific analysis ONLY for the stocks involved in your recommended actions. Do not provide detailed breakdowns for stocks you recommend holding or avoiding. CRITICAL: Keep your analysis extremely concise (maximum 3 sentences per stock). Do NOT list the technical indicators as bullet points; integrate them naturally into your reasoning."""
    else:
        return f"""You are an expert TSX trading advisor. Read the following live market dossier:
{dossier}

System Instructions:
1. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash, you must NOT recommend a BUY action.
2. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once.
3. Invalidation Levels (Stop Losses): Whenever you recommend a BUY, you MUST provide a strict technical invalidation level (a Stop Loss) where your thesis is proven wrong.
4. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position to lock in realized gains.

Format your message precisely as follows:
1. Brief introduction.
2. A prioritized, ordered list of specific actions you recommend taking (e.g., 1. SELL TICKER, 2. BUY TICKER).
3. Detailed stock-specific analysis ONLY for the stocks involved in your recommended actions. Do not provide detailed breakdowns for stocks you recommend holding or avoiding. CRITICAL: Keep your analysis extremely concise (maximum 3 sentences per stock). Integrate Ex-Dividend Dates and SMAs naturally into your reasoning without using bullet points."""

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
