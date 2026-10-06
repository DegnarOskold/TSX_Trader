import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime
import urllib.request
import xml.etree.ElementTree as ET
import csv
import os
import sys
import json
import re
import time
import urllib.parse
from email.utils import parsedate_to_datetime
from datetime import timezone
from contextlib import contextmanager

try:
    if sys.stdout:
        sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
TRADES_FILE = os.path.join(BASE_DIR, "trades.csv")
ADVICE_FILE = os.path.join(BASE_DIR, "advice_history.txt")
LOCK_FILE = os.path.join(BASE_DIR, "advice.lock")
PRUNE_MARKER_FILE = os.path.join(BASE_DIR, ".advice_last_prune")

@contextmanager
def acquire_advice_lock():
    lock_file = LOCK_FILE
    max_retries = 50
    locked = False
    for _ in range(max_retries):
        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            locked = True
            break
        except FileExistsError:
            try:
                if os.path.getmtime(lock_file) < time.time() - 30:
                    os.remove(lock_file)
                    continue
            except OSError:
                pass
            time.sleep(0.1)
    if not locked:
        raise RuntimeError("Could not acquire advice lock after 50 retries")
    try:
        yield
    finally:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except OSError:
                pass

def log_advice(text):
    with acquire_advice_lock():
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(ADVICE_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}]\n{text}\n\n")

def get_current_mode(config=None):
    if config is not None:
        return config.get("mode", "SHORT").upper()
    target_cfg = CONFIG_FILE if os.path.exists(CONFIG_FILE) else ("config.json" if os.path.exists("config.json") else None)
    if target_cfg:
        with open(target_cfg, "r") as f:
            data = json.load(f)
            return data.get("mode", "SHORT").upper()
    return "SHORT"

def get_tickers(config=None):
    if config is not None:
        portfolio = config.get("portfolio", [])
        if isinstance(portfolio, dict):
            return list(portfolio.keys())
        elif isinstance(portfolio, list) and portfolio:
            return portfolio
        return ["CNQ.TO", "ABX.TO"]
    target_cfg = CONFIG_FILE if os.path.exists(CONFIG_FILE) else ("config.json" if os.path.exists("config.json") else None)
    if target_cfg:
        with open(target_cfg, "r") as f:
            data = json.load(f)
            portfolio = data.get("portfolio", [])
            if isinstance(portfolio, dict):
                return list(portfolio.keys())
            elif isinstance(portfolio, list) and portfolio:
                return portfolio
    return ["CNQ.TO", "ABX.TO"]

def get_stop_loss_pct(config=None):
    if config is not None:
        return config.get("stop_loss_pct", 5.0)
    target_cfg = CONFIG_FILE if os.path.exists(CONFIG_FILE) else ("config.json" if os.path.exists("config.json") else None)
    if target_cfg:
        with open(target_cfg, "r") as f:
            data = json.load(f)
            return data.get("stop_loss_pct", 5.0)
    return 5.0

def get_acb_and_balances():
    target_trades = TRADES_FILE if os.path.exists(TRADES_FILE) else ("trades.csv" if os.path.exists("trades.csv") else None)
    if not target_trades:
        return {"positions": {}, "cash": 0.0}
        
    positions = {}
    cash = 0.0
    with open(target_trades, "r") as f:
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
                    
    if cash < 0:
        print(f"WARNING: Negative cash balance detected: ${cash:.2f}")
    return {"positions": positions, "cash": round(cash, 2)}

def log_trade(date, ticker, action, quantity, price, shares_balance, cash_balance):
    """Append a trade to trades.csv with strict 7-column schema validation."""
    row = [date, ticker, action, quantity, price, shares_balance, cash_balance]
    if len(row) != 7:
        raise ValueError(f"Trade row must have exactly 7 columns, got {len(row)}")
    with open("trades.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

def get_stock_data(ticker_symbol, mode="MEDIUM", prefetched_hist=None):
    try:
        ticker = yf.Ticker(ticker_symbol)
        if prefetched_hist is not None and not prefetched_hist.empty:
            hist = prefetched_hist.copy()
            # Validate required columns; fall back to individual download if mismatched
            if not {'Open', 'High', 'Low', 'Close', 'Volume'}.issubset(hist.columns):
                hist = ticker.history(period="6mo", timeout=10)
        else:
            hist = ticker.history(period="6mo", timeout=10)
        if hist.empty:
            return None
            
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        prev_close = prev["Close"]
        gap_pct = ((latest["Open"] - prev_close) / prev_close) * 100 if prev_close > 0 else 0.0
        pct_from_low = ((latest["Close"] - latest["Low"]) / latest["Low"]) * 100 if latest["Low"] > 0 else 0.0
        
        if mode == "SHORT":
            hist.ta.ema(length=5, append=True)
            hist.ta.ema(length=9, append=True)
            hist.ta.rsi(length=7, append=True)
            hist.ta.atr(length=5, append=True)
            hist.ta.bbands(length=20, std=2, append=True)
            hist.ta.adx(length=14, append=True)
            
            latest = hist.iloc[-1]
            
            if len(hist) > 10:
                vol_sma_10 = hist["Volume"].iloc[:-1].tail(10).mean()
            else:
                vol_sma_10 = hist["Volume"].rolling(window=10).mean().iloc[-1]
                
            now_et = datetime.datetime.now(timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=-4)))
            market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
            
            if now_et < market_open:
                minutes_passed = 0
            elif now_et > market_close:
                minutes_passed = 390
            else:
                minutes_passed = (now_et - market_open).total_seconds() / 60.0
                
            if 0 < minutes_passed < 390:
                fraction_of_day = max(minutes_passed, 15.0) / 390.0
                adjusted_sma = vol_sma_10 * fraction_of_day
                vol_ratio = (latest["Volume"] / adjusted_sma) if adjusted_sma > 0 else 1.0
            else:
                vol_ratio = (latest["Volume"] / vol_sma_10) if vol_sma_10 > 0 else 1.0
            
            ema_5 = latest["EMA_5"] if "EMA_5" in latest else 0
            ema_9 = latest["EMA_9"] if "EMA_9" in latest else 0
            if ema_5 > ema_9:
                crossover = "BULLISH (EMA5 > EMA9)"
            elif ema_5 < ema_9:
                crossover = "BEARISH (EMA5 < EMA9)"
            else:
                crossover = "NEUTRAL"
            
            # The column names for BBands in pandas_ta can be quirky (e.g., BBL_20_2.0_2.0 or BBL_20_2.0)
            # Find them dynamically
            bb_lower_col = [c for c in hist.columns if c.startswith("BBL_")][0] if any(c.startswith("BBL_") for c in hist.columns) else None
            bb_mid_col = [c for c in hist.columns if c.startswith("BBM_")][0] if any(c.startswith("BBM_") for c in hist.columns) else None
            bb_upper_col = [c for c in hist.columns if c.startswith("BBU_")][0] if any(c.startswith("BBU_") for c in hist.columns) else None

            return {
                "Prev_Close": round(prev_close, 2),
                "Gap_Pct": round(gap_pct, 2),
                "Pct_From_Low": round(pct_from_low, 2),
                "Open": round(latest["Open"], 2),
                "High": round(latest["High"], 2),
                "Low": round(latest["Low"], 2),
                "Price": round(latest["Close"], 2),
                "Volume": int(latest["Volume"]),
                "Vol_Ratio": round(vol_ratio, 2),
                "EMA_Crossover": crossover,
                "EMA_5": round(latest["EMA_5"], 2) if "EMA_5" in latest else "N/A",
                "EMA_9": round(latest["EMA_9"], 2) if "EMA_9" in latest else "N/A",
                "RSI_7": round(latest["RSI_7"], 2) if "RSI_7" in latest else "N/A",
                "ATR_5": round(latest["ATRr_5"], 2) if "ATRr_5" in latest else "N/A",
                "ADX_14": round(latest["ADX_14"], 2) if "ADX_14" in latest else "N/A",
                "BB_Lower": round(latest[bb_lower_col], 2) if bb_lower_col else "N/A",
                "BB_Mid": round(latest[bb_mid_col], 2) if bb_mid_col else "N/A",
                "BB_Upper": round(latest[bb_upper_col], 2) if bb_upper_col else "N/A",
                "earnings_date": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("earnings_date", "N/A"),
                "days_to_earnings": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("days_to_earnings"),
                "ex_dividend_date": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("ex_dividend_date", "N/A"),
                "days_to_ex_dividend": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("days_to_ex_dividend")
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
                "Prev_Close": round(prev_close, 2),
                "Gap_Pct": round(gap_pct, 2),
                "Pct_From_Low": round(pct_from_low, 2),
                "Open": round(latest["Open"], 2),
                "High": round(latest["High"], 2),
                "Low": round(latest["Low"], 2),
                "Price": round(latest["Close"], 2),
                "Volume": int(latest["Volume"]),
                "RSI_14": round(latest["RSI_14"], 2) if "RSI_14" in latest else "N/A",
                "SMA_50": round(latest["SMA_50"], 2) if "SMA_50" in latest else "N/A",
                "BB_Upper": round(latest[bb_upper_col], 2) if bb_upper_col else "N/A",
                "Ex_Div_Date": ex_div_date,
                "earnings_date": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("earnings_date", "N/A"),
                "days_to_earnings": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("days_to_earnings"),
                "ex_dividend_date": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("ex_dividend_date", "N/A"),
                "days_to_ex_dividend": get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {}).get("days_to_ex_dividend")
            }
    except Exception as e:
        if mode == "SHORT":
            return {
                "Prev_Close": "N/A", "Gap_Pct": "N/A", "Pct_From_Low": "N/A",
                "Open": "N/A", "High": "N/A", "Low": "N/A", "Price": "N/A",
                "Volume": 0, "Vol_Ratio": "N/A", "EMA_Crossover": "N/A", "EMA_5": "N/A", "EMA_9": "N/A",
                "RSI_7": "N/A", "ATR_5": "N/A", "ADX_14": "N/A", "BB_Lower": "N/A", "BB_Mid": "N/A", "BB_Upper": "N/A"
            }
        else:
            return {
                "Prev_Close": "N/A", "Gap_Pct": "N/A", "Pct_From_Low": "N/A",
                "Open": "N/A", "High": "N/A", "Low": "N/A", "Price": "N/A",
                "Volume": 0, "RSI_14": "N/A", "SMA_50": "N/A", "BB_Upper": "N/A", "Ex_Div_Date": "N/A"
            }

NEWS_CACHE_FILE = "macro_news_cache.json"
NEWS_CACHE_TTL = 1800  # 30 minutes in seconds

def get_compartmentalized_news(config=None):
    # Check news cache first (avoid re-fetching within 30 minutes)
    if os.path.exists(NEWS_CACHE_FILE):
        try:
            with open(NEWS_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < NEWS_CACHE_TTL:
                return cache.get("news", "")
        except Exception:
            pass

    now_utc = datetime.datetime.now(timezone.utc)
    pillars = [
        ("CANADA MACRO (Bank of Canada, TSX, Inflation, Economy)", "Bank of Canada interest rate OR TSX composite OR Canadian inflation economy"),
        ("USA MACRO (Federal Reserve, US Economy, Rates, S&P 500)", "Federal Reserve OR US inflation OR Wall Street stocks"),
        ("WORLD MACRO (Geopolitics, Global Economy, Trade, Commodities)", "global economy OR world markets OR geopolitics OR oil prices")
    ]

    output_sections = []
    for pillar_name, query in pillars:
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=en-CA&gl=CA&ceid=CA:en"
        items = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                for item in root.findall('./channel/item')[:4]:
                    title_el = item.find('title')
                    pubdate_el = item.find('pubDate')
                    if title_el is None or pubdate_el is None or not title_el.text or not pubdate_el.text:
                        continue
                    title = title_el.text.strip()
                    try:
                        dt = parsedate_to_datetime(pubdate_el.text)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        hours_ago = int((now_utc - dt).total_seconds() / 3600)
                    except Exception:
                        hours_ago = 0
                    if hours_ago <= 48:
                        freshness = "NEW" if hours_ago < 6 else ("RECENT" if hours_ago < 24 else "OLD")
                        items.append(f"  - [{freshness} {hours_ago}h ago] {title}")
        except Exception:
            pass

        output_sections.append(f"[{pillar_name}]")
        if items:
            output_sections.extend(items)
        else:
            output_sections.append("  - No high-impact headlines in the past 48h.")
        output_sections.append("")

    full_news = "\n".join(output_sections)
    try:
        with open(NEWS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"timestamp": time.time(), "news": full_news}, f, indent=2)
    except Exception:
        pass

    return full_news


CALENDAR_CACHE_FILE = "corporate_calendar_cache.json"
CALENDAR_CACHE_TTL = 86400  # 24 hours

def get_corporate_calendar(tickers=None):
    """Fetches and caches upcoming earnings and ex-dividend dates (24h cache)."""
    if os.path.exists(CALENDAR_CACHE_FILE):
        try:
            with open(CALENDAR_CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
            if time.time() - cache.get("_timestamp", 0) < CALENDAR_CACHE_TTL:
                return cache.get("calendar", {})
        except Exception:
            pass

    if not tickers:
        tickers = get_tickers()

    now_date = datetime.date.today()
    calendar_data = {}

    for t in tickers:
        try:
            tk = yf.Ticker(t)
            cal = tk.calendar
            ed_str = "N/A"
            days_to_ed = None
            ex_div_str = "N/A"
            days_to_ex_div = None

            if isinstance(cal, dict):
                ed = cal.get("Earnings Date")
                if isinstance(ed, list) and ed:
                    ed_date = ed[0]
                    if isinstance(ed_date, datetime.date):
                        ed_str = ed_date.strftime("%Y-%m-%d")
                        days_to_ed = (ed_date - now_date).days
                ex_div = cal.get("Ex-Dividend Date")
                if isinstance(ex_div, datetime.date):
                    ex_div_str = ex_div.strftime("%Y-%m-%d")
                    days_to_ex_div = (ex_div - now_date).days

            calendar_data[t] = {
                "earnings_date": ed_str,
                "days_to_earnings": days_to_ed,
                "ex_dividend_date": ex_div_str,
                "days_to_ex_dividend": days_to_ex_div
            }
        except Exception:
            calendar_data[t] = {
                "earnings_date": "N/A",
                "days_to_earnings": None,
                "ex_dividend_date": "N/A",
                "days_to_ex_dividend": None
            }

    try:
        with open(CALENDAR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"_timestamp": time.time(), "calendar": calendar_data}, f, indent=2)
    except Exception:
        pass

    return calendar_data

def get_cleaned_advice_history():
    with acquire_advice_lock():
        target_advice = ADVICE_FILE if os.path.exists(ADVICE_FILE) else ("advice_history.txt" if os.path.exists("advice_history.txt") else None)
        if not target_advice:
            return "No previous advice recorded today."
            
        with open(target_advice, "r", encoding="utf-8") as f:
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
                
        # Only prune (rewrite) the file once per day to reduce I/O
        prune_marker = PRUNE_MARKER_FILE
        should_prune = True
        if os.path.exists(prune_marker):
            try:
                with open(prune_marker, "r") as pf:
                    if pf.read().strip() == today_str:
                        should_prune = False
            except Exception:
                pass
        
        if should_prune:
            with open(target_advice, "w", encoding="utf-8") as f:
                for timestamp, text in cleaned_entries:
                    f.write(f"[{timestamp}]\n{text}\n\n")
            try:
                with open(prune_marker, "w") as pf:
                    pf.write(today_str)
            except Exception:
                pass
            
        # Build string to return using bounded history
        history_entries = []
        for date_str in sorted(grouped.keys()):
            if date_str == today_str:
                history_entries.extend(grouped[date_str][-5:]) # Keep up to last 5 from today for the LLM
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
    target_cfg = CONFIG_FILE if os.path.exists(CONFIG_FILE) else ("config.json" if os.path.exists("config.json") else None)
    if target_cfg:
        with open(target_cfg, "r") as f:
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
    cal_map = get_corporate_calendar(tickers)
    
    # Pre-compute macro commodities list for batch download
    macro_topics = []
    if config is not None:
        if "macro_commodities" in config and isinstance(config["macro_commodities"], list):
            macro_topics = [m for m in config["macro_commodities"] if re.match(r'^[A-Z0-9=.-]+$', m)]
        else:
            portfolio = config.get("portfolio", {})
            if isinstance(portfolio, dict):
                for ticker_list in portfolio.values():
                    if isinstance(ticker_list, list):
                        for topic in ticker_list:
                            if topic not in tickers and topic not in macro_topics:
                                if re.match(r'^[A-Z0-9=.-]+$', topic):
                                    macro_topics.append(topic)
    if not macro_topics:
        macro_topics = ["CL=F", "GC=F", "HG=F"]
    
    # Batch download all ticker data in a single API call (instead of 22+ individual calls)
    all_download_tickers = tickers + [m for m in macro_topics if m not in tickers]
    prefetched = {}
    try:
        if len(all_download_tickers) > 1:
            raw = yf.download(all_download_tickers, period="6mo", group_by="ticker", threads=True, timeout=15)
            for t_dl in all_download_tickers:
                try:
                    prefetched[t_dl] = raw[t_dl].dropna(how='all')
                except (KeyError, Exception):
                    pass
        elif len(all_download_tickers) == 1:
            prefetched[all_download_tickers[0]] = yf.download(all_download_tickers[0], period="6mo", timeout=15)
    except Exception:
        pass  # Will fall back to individual downloads in get_stock_data()
    
    total_unrealized_pnl = 0.0
    has_open_positions = False
    
    for t in tickers:
        market_data = get_stock_data(t, mode, prefetched_hist=prefetched.get(t))
        pos = positions.get(t, {"shares": 0.0, "acb": 0.0})
        
        current_price = market_data.get('Price', "N/A") if isinstance(market_data, dict) else "N/A"
        shares = pos['shares']
        
        if shares > 0:
            has_open_positions = True
            acb = pos['acb']
            acb_str = f"${acb:.2f}"
            if isinstance(current_price, (int, float)):
                pnl_pct = ((current_price - acb) / acb) * 100 if acb > 0 else 0.0
                pnl_val = (current_price - acb) * shares
                total_unrealized_pnl += pnl_val
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
            dossier += f"  - Previous Close: ${market_data.get('Prev_Close', 'N/A')} (Gap: {market_data.get('Gap_Pct', 'N/A'):+.2f}%)\n"
            dossier += f"  - Today's Open: ${market_data.get('Open', 'N/A')} | High: ${market_data.get('High', 'N/A')} | Low: ${market_data.get('Low', 'N/A')}\n"
            dossier += f"  - Intraday Trend: {market_data.get('Pct_From_Low', 'N/A')}% above Low of Day\n"
        dossier += f"  - Unrealised P&L: {pnl_str}\n"
        
        if shares > 0 and pnl_pct < -stop_loss:
            dossier += f"  - [⚠️ STOP-LOSS TRIGGERED: Price is {abs(pnl_pct):.2f}% below ACB. You MUST recommend SELL.]\n"
        if isinstance(market_data, dict):
            if mode == "SHORT":
                dossier += f"  - Vol Ratio (10-day): {market_data.get('Vol_Ratio', 'N/A')}x\n"
                dossier += f"  - EMA Crossover: {market_data.get('EMA_Crossover', 'N/A')}\n"
                dossier += f"  - EMA (5-day): ${market_data.get('EMA_5', 'N/A')}\n"
                dossier += f"  - EMA (9-day): ${market_data.get('EMA_9', 'N/A')}\n"
                dossier += f"  - RSI (7-day): {market_data.get('RSI_7', 'N/A')}\n"
                dossier += f"  - ATR (5-day): ${market_data.get('ATR_5', 'N/A')}\n"
                dossier += f"  - ADX (14-day): {market_data.get('ADX_14', 'N/A')}\n"
                dossier += f"  - Bollinger Lower (20): ${market_data.get('BB_Lower', 'N/A')}\n"
                dossier += f"  - Bollinger Mid (20): ${market_data.get('BB_Mid', 'N/A')}\n"
                dossier += f"  - Bollinger Upper (20): ${market_data.get('BB_Upper', 'N/A')}\n"
            else:
                dossier += f"  - RSI (14-day): {market_data.get('RSI_14', 'N/A')}\n"
                dossier += f"  - SMA (50-day): ${market_data.get('SMA_50', 'N/A')}\n"

        cal = cal_map.get(t, {})
        ed_date = cal.get("earnings_date")
        days_to_ed = cal.get("days_to_earnings")
        ex_div_date = cal.get("ex_dividend_date")
        days_to_ex_div = cal.get("days_to_ex_dividend")

        if ed_date and ed_date != "N/A":
            ed_txt = f"{ed_date} ({days_to_ed}d away)" if days_to_ed is not None else ed_date
            dossier += f"  - Upcoming Earnings Date: {ed_txt}\n"
            if days_to_ed is not None and 0 <= days_to_ed <= 4:
                dossier += f"  - [⚠️ EARNINGS RISK: Reporting in {days_to_ed} days on {ed_date}. High binary gap risk. Avoid new BUY.]\n"

        if ex_div_date and ex_div_date != "N/A":
            ex_txt = f"{ex_div_date} ({days_to_ex_div}d away)" if days_to_ex_div is not None else ex_div_date
            dossier += f"  - Next Ex-Dividend Date: {ex_txt}\n"
            if days_to_ex_div is not None and 0 <= days_to_ex_div <= 4:
                dossier += f"  - [📅 UPCOMING EX-DIVIDEND: Ex-date {ex_div_date}. Expect mechanical dividend price drop.]\n"

        dossier += "\n"
    
    if has_open_positions:
        dossier += f"--- TOTAL UNREALIZED P&L: ${total_unrealized_pnl:.2f} ---\n\n"
    
    # Macro commodities (topics already extracted above for batch download)
    if macro_topics:
        dossier += f"--- MACRO COMMODITIES ---\n"
        for macro in macro_topics:
            m_data = get_stock_data(macro, mode="MEDIUM", prefetched_hist=prefetched.get(macro))
            if isinstance(m_data, dict):
                m_price = m_data.get('Price', 'N/A')
                m_open = m_data.get('Open', 'N/A')
                if isinstance(m_price, (int, float)) and isinstance(m_open, (int, float)) and m_open > 0:
                    chg_pct = ((m_price - m_open) / m_open) * 100
                    dossier += f"{macro}: ${m_price:.2f} (Daily Change vs Open: {chg_pct:+.2f}%)\n"
                else:
                    dossier += f"{macro}: ${m_price}\n"
        dossier += "\n"
    
    dossier += "--- CONSOLIDATED MACROECONOMIC BRIEFING (CANADA, USA, WORLD) ---\n"
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
2. Volume Shock: If Vol_Ratio is > 1.25 (Volume is 1.25x normal) during a drop, this is 'Capitulation' (panic selling is exhausted). This is a bullish reversal signal.
3. Opening Chop Guard (9:30 AM – 10:00 AM ET): DO NOT recommend new BUY orders during the first 30 minutes of the trading day. Allow the opening cross, wide bid-ask spreads, and retail emotional gaps to settle. True swing entry setups must be evaluated after 10:00 AM ET.
4. Tripartite Macroeconomic Context: You have a single consolidated Macroeconomic Briefing covering Canada, the USA, and the World. Do NOT look for, require, or expect individual per-stock news feeds. Instead, evaluate every stock through this top-down macroeconomic lens: (1) Canada Macro (BoC interest rate direction, domestic inflation, TSX strength), (2) USA Macro (Fed policy, US CPI/jobs, Wall Street momentum), and (3) World Macro (geopolitics, global supply chains, international trade, and global commodities). Ensure every recommendation aligns with these broader macroeconomic tides.
5. Anticipatory Macro Shifts (Buy the Rumor, Sell the News): Do not wait for a deal to be finalized or signed before adjusting your thesis. If the qualitative macro headlines or commodity trackers (CL=F, GC=F) strongly signal a high-probability calendar event, formal signing ceremony, or geopolitical shift within the next 24 to 48 hours, prioritize this upcoming macro momentum. If the impending event removes a market premium or changes commodity fundamentals, override short-term "oversold" technical indicators (like 7-day RSI and Bollinger Bands) and favor defensive capital preservation (HOLD or SELL) rather than assuming an immediate mean-reversion rally.
6. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash to purchase a meaningful position, you must NOT recommend a BUY action.
7. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once.
8. Protective Stop-Loss for Holds: If the current market price of an existing HOLD position drops more than {stop_loss}% below its Avg Purchase Price, you MUST explicitly recommend to SELL to cut losses, regardless of how 'oversold' it looks.
9. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position to lock in realized gains.
10. Zero-Share Holdings: If the user currently owns 0 shares of a stock and you do not recommend buying it, explicitly recommend AVOID or IGNORE instead of HOLD.
11. Acknowledge Failed Theses: Review the PREVIOUS ADVICE HISTORY. If your previous predictions were wrong and the stock continued to drop, explicitly acknowledge this instead of blindly repeating the same thesis.
12. Macro Override (Contrarian Entries): You may bypass the strict EMA downtrend rule and recommend a Speculative BUY ONLY IF: (a) 7-day RSI is deeply oversold (< 25), (b) There is a top-tier macroeconomic catalyst in the news that directly and positively impacts the sector, and (c) You explicitly label it as a "Speculative Macro Entry" with a small position size.
13. Intraday Catalyst Breakout: If a stock spikes significantly intraday (e.g., > 1.0% above previous close) alongside a highly positive, direct breaking news catalyst (e.g., major partnerships, earnings beats), you may recommend a Speculative Breakout BUY to ride the momentum, even if the lagging EMA crossover is still bearish. Size this as a partial tranche.
14. Intraday Reversal Trigger: Catch extreme intraday V-bottoms before lagging moving averages cross. If a stock drops significantly intraday (e.g., >1.25% below open) but its 7-day RSI dips below 35 (oversold) and then immediately rebounds (e.g. Intraday Trend > 1.5% above Low of Day), you may allow a speculative 'Reversal Buy' on a partial position.
15. ADX Trend Filter: Do not recommend a BUY based on an EMA crossover unless the 14-day ADX is > 20 (indicating a strong trend). EXCEPTION: If the Volume Ratio is exceptionally high (> 1.25x), indicating a sudden surge in interest, you may bypass the ADX constraint, as the trend indicator is lagging.
16. Target and Stop Loss: When generating a BUY recommendation, ALWAYS calculate and provide a Target Sell Price and a Stop Loss Price. To lock in short-term profits, use the Mid-Bollinger Band (20-day SMA) or a tighter +1.5 ATR target. A profit target must ALWAYS be higher than the purchase price. If Mid-Bollinger is below purchase price, default to +1.5 ATR.
17. Upcoming Earnings & Ex-Dividend Protection: Check the Upcoming Earnings Date and Next Ex-Dividend Date for every stock. Do NOT recommend a new BUY for any stock with an earnings report scheduled within the next 3 trading days due to unhedged binary event risk. For stocks trading ex-dividend within 3 days, note the ex-date and account for the mechanical price drop when calculating targets and stop-losses.
18. Low-Volume Scaled Entry: You may relax the strict high-volume requirement (> 1.25x) and recommend a BUY if a stock flashes a clean bullish technical setup (e.g., EMA 5 > EMA 9). However, you MUST explicitly recommend scaling in with a smaller position size (e.g., 25% or 50% allocation) and clearly label the trade as a "Low-Volume Scaled Entry".
19. Overbought Filter: If a stock flashes a bullish EMA crossover but its 7-day RSI is highly elevated (> 65), DO NOT recommend a buy UNLESS the Volume Ratio is > 1.25x. A strong volume surge validates a strong breakout, overriding the overbought warning.
20. Macro-Alignment: Before recommending any commodity-linked stock (e.g. Gold miners like AEM/ABX, Oil producers like CNQ), you MUST verify that the underlying commodity (e.g., GC=F for gold, CL=F for oil) is currently green/positive for the day. If the macro trend is actively selling off, suppress the buy signal.
21. Profit Target Flag: If an open position's current price has risen more than 2% above its purchase price (cost basis), you must explicitly flag it to the user and suggest they move their Stop Loss up to their breakeven purchase price to secure a risk-free trade.

Format your message precisely as follows:
1. Brief introduction.
2. A prioritized, ordered list of specific actions you recommend taking (e.g., 1. SELL TICKER, 2. BUY TICKER, 3. HOLD TICKER). Do NOT list AVOID or IGNORE in this list. If there are no actions to take, state "No immediate actions recommended".
3. Detailed stock-specific analysis ONLY for the stocks involved in your recommended actions. Do not provide detailed breakdowns for stocks you recommend avoiding or ignoring. CRITICAL: Keep your analysis extremely concise (maximum 3 sentences per stock). You must ALWAYS include the current price of each stock in your detailed breakdown. Do NOT list the technical indicators as bullet points; integrate them naturally into your reasoning."""
    else:
        return f"""You are an expert TSX trading advisor. Read the following live market dossier:
{dossier}

System Instructions:
1. Macroeconomic Context (Canada, USA, World): Apply the single consolidated Macroeconomic Briefing across all stocks. Do NOT look for individual per-stock news feeds. Synthesize Canada, USA, and World macro developments into all stock assessments.
2. Cash Constraint: You must check the Available Free Cash before recommending a BUY. If there is insufficient free cash, you must NOT recommend a BUY action.
3. Position Sizing (Tranching): If recommending an accumulation BUY, instruct the user to "Buy in Tranches" (e.g., deploy 25% of free cash) rather than buying all at once.
4. Protective Stop-Loss for Holds: If the current market price of an existing HOLD position drops more than {stop_loss}% below its Avg Purchase Price, you MUST explicitly recommend to SELL to cut losses.
5. Profit-Taking Mechanics: If an asset currently held touches its Upper Bollinger Band and RSI exceeds 70, you must explicitly recommend trimming the position to lock in realized gains.
6. Zero-Share Holdings: If the user currently owns 0 shares of a stock and you do not recommend buying it, explicitly recommend AVOID or IGNORE instead of HOLD.
7. Acknowledge Failed Theses: Review the PREVIOUS ADVICE HISTORY. If your previous predictions were wrong and the stock continued to drop, explicitly acknowledge this instead of blindly repeating the same thesis.

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
3. Outlook Ahead: 2-3 sentences on what to expect tomorrow based on today's price action, volume anomalies, and breaking macroeconomic news catalysts across Canada, the USA, and the world. 
Maintain a calm, objective, and highly professional tone at all times. Do not recommend new trades in this summary."""

if __name__ == "__main__":
    print(generate_dossier())
