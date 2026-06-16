import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import csv
import os
import json

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
            return data.get("tickers", ["CNQ.TO", "ABX.TO"])
    return ["CNQ.TO", "ABX.TO"]

def get_acb_and_balances():
    if not os.path.exists("trades.csv"):
        return {}
        
    positions = {}
    with open("trades.csv", "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row["Ticker"]
            action = row["Action"]
            qty = float(row["Quantity"])
            price = float(row["Price"])
            
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
                    
    return positions

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
    topics = {
        "CNQ.TO": "Canadian Natural Resources",
        "ABX.TO": "Barrick Gold",
        "CL=F": "WTI Crude Oil",
        "GC=F": "Gold"
    }
    
    news_output = ""
    for ticker, name in topics.items():
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        news_output += f"[{ticker} - {name}]\n"
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
    
    positions = get_acb_and_balances()
    
    dossier += "--- PORTFOLIO & PRICING ---\n"
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
        
        dossier += f"{t}:\n"
        dossier += f"  - Shares Owned: {shares:.4f}\n"
        dossier += f"  - Avg Purchase Price: {acb_str}\n"
        dossier += f"  - Current Market Price: ${current_price:.2f}\n"
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
    
    dossier += "=== END OF DOSSIER ===\n"
    return dossier

if __name__ == "__main__":
    print(generate_dossier())
