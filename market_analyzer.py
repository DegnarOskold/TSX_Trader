import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import csv
import os

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

def get_stock_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period="6mo")
        if hist.empty:
            return None
            
        hist.ta.rsi(length=14, append=True)
        hist.ta.sma(length=50, append=True)
        
        latest = hist.iloc[-1]
        
        return {
            "Price": round(latest["Close"], 2),
            "Volume": int(latest["Volume"]),
            "RSI_14": round(latest["RSI_14"], 2) if "RSI_14" in latest else "N/A",
            "SMA_50": round(latest["SMA_50"], 2) if "SMA_50" in latest else "N/A"
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
    dossier = "=== TSX TRADING ADVISOR DOSSIER ===\n"
    dossier += f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    positions = get_acb_and_balances()
    
    dossier += "--- PORTFOLIO & PRICING ---\n"
    tickers = ["CNQ.TO", "ABX.TO"]
    
    for t in tickers:
        market_data = get_stock_data(t)
        pos = positions.get(t, {"shares": 0.0, "acb": 0.0})
        
        current_price = market_data['Price'] if isinstance(market_data, dict) else "N/A"
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
