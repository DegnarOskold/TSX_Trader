import yfinance as yf
import numpy as np
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
    from zoneinfo import ZoneInfo
    _ET_TZ = ZoneInfo("America/Toronto")
except Exception:
    _ET_TZ = None

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

def load_config():
    target_cfg = CONFIG_FILE if os.path.exists(CONFIG_FILE) else ("config.json" if os.path.exists("config.json") else None)
    if target_cfg:
        with open(target_cfg, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def normalize_ticker(ticker):
    """Normalizes TSX dual-class tickers (e.g. TECK.B.TO or TECK.B -> TECK-B.TO) while preserving futures/indices."""
    t = str(ticker).strip().upper()
    if not t or t in ("CASH", "CAD") or "=" in t or t.startswith("^"):
        return t
    base = t[:-3] if t.endswith(".TO") else t
    return f"{base.replace('.', '-')}.TO"


def _now_et():
    if _ET_TZ is not None:
        return datetime.datetime.now(_ET_TZ)
    return datetime.datetime.now()


def _is_tsx_regular_hours(now_et=None):
    dt = now_et or _now_et()
    if dt.weekday() >= 5:
        return False
    open_dt = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    close_dt = dt.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_dt <= dt < close_dt


def _expected_intraday_vol_fraction(minutes_passed):
    """TSX pre-MOC cumulative volume curve (~4.5% open cross + ~63.5% continuous + ~32% 4pm MOC)."""
    if minutes_passed <= 0.0 or minutes_passed >= 390.0:
        return 1.0
    return 0.045 + 0.635 * (max(minutes_passed, 5.0) / 390.0)


def _overlay_fresh_bar(df, df_5d=None, df_1m=None, today_date=None):
    """Overlays uncached 5d daily (MOC-settled) and intraday 1m OHLCV onto Yahoo's CDN-cached 6mo frame."""
    if df is None or df.empty:
        return df
    out = df.copy()
    ohlcv_cols = ("Open", "High", "Low", "Close", "Volume")

    if df_5d is not None and not df_5d.empty:
        clean_5d = df_5d.dropna(subset=["Close"])
        if not clean_5d.empty:
            r5 = clean_5d.iloc[-1]
            d5 = clean_5d.index[-1].date()
            last_d = out.index[-1].date()
            if d5 == last_d:
                for col in ohlcv_cols:
                    if col in r5 and col in out.columns and pd.notna(r5[col]):
                        out.iloc[-1, out.columns.get_loc(col)] = r5[col]
            elif d5 > last_d:
                new_idx = pd.Timestamp(d5, tz=out.index.tz)
                new_row = out.iloc[-1].copy()
                for col in ohlcv_cols:
                    if col in r5 and pd.notna(r5[col]):
                        new_row[col] = r5[col]
                out.loc[new_idx] = new_row

    if df_1m is not None and not df_1m.empty:
        clean_1m = df_1m.dropna(subset=["Close"])
        if not clean_1m.empty:
            d1 = clean_1m.index[-1].date()
            ref_today = today_date or _now_et().date()
            if d1 == ref_today:
                last_d = out.index[-1].date()
                c_px = float(clean_1m["Close"].iloc[-1])
                h_px = float(clean_1m["High"].dropna().max()) if "High" in clean_1m else c_px
                l_px = float(clean_1m["Low"].dropna().min()) if "Low" in clean_1m else c_px
                o_px = float(clean_1m["Open"].dropna().iloc[0]) if "Open" in clean_1m and not clean_1m["Open"].dropna().empty else c_px
                v_sum = float(clean_1m["Volume"].dropna().sum()) if "Volume" in clean_1m else 0.0
                if d1 > last_d:
                    new_idx = pd.Timestamp(d1, tz=out.index.tz)
                    new_row = out.iloc[-1].copy()
                    for col, val in (("Open", o_px), ("High", h_px), ("Low", l_px), ("Close", c_px), ("Volume", v_sum)):
                        if col in out.columns:
                            new_row[col] = val
                    out.loc[new_idx] = new_row
                elif d1 == last_d:
                    out.iloc[-1, out.columns.get_loc("Close")] = c_px
                    out.iloc[-1, out.columns.get_loc("High")] = max(float(out["High"].iloc[-1]), h_px)
                    out.iloc[-1, out.columns.get_loc("Low")] = min(float(out["Low"].iloc[-1]), l_px)
                    out.iloc[-1, out.columns.get_loc("Volume")] = max(float(out["Volume"].iloc[-1]), v_sum)

    return out


def prefetch_histories(tickers, period="6mo"):
    """Batch-downloads OHLCV histories via yfinance and overlays fresh 5d/1m bars to defeat 6mo CDN lag."""
    prefetched = {}
    if not tickers:
        return prefetched
    if len(tickers) == 1:
        t = tickers[0]
        try:
            tk = yf.Ticker(t)
            df = tk.history(period=period, timeout=10)
            if df is not None and not df.empty:
                now_et = _now_et()
                d5 = tk.history(period="5d", timeout=8)
                d1 = tk.history(period="1d", interval="1m", timeout=8) if _is_tsx_regular_hours(now_et) else None
                prefetched[t] = _overlay_fresh_bar(df, df_5d=d5, df_1m=d1, today_date=now_et.date())
        except Exception:
            pass
        return prefetched

    try:
        raw = yf.download(tickers, period=period, group_by="ticker", threads=True, timeout=15, progress=False)
        raw_5d = yf.download(tickers, period="5d", group_by="ticker", threads=True, timeout=10, progress=False)
        now_et = _now_et()
        raw_1m = (
            yf.download(tickers, period="1d", interval="1m", group_by="ticker", threads=True, timeout=10, progress=False)
            if _is_tsx_regular_hours(now_et)
            else None
        )
        for t in tickers:
            try:
                df = raw[t].dropna(how="all")
                if not df.empty:
                    d5 = raw_5d[t].dropna(how="all") if (raw_5d is not None and t in raw_5d) else None
                    d1 = raw_1m[t].dropna(how="all") if (raw_1m is not None and t in raw_1m) else None
                    prefetched[t] = _overlay_fresh_bar(df, df_5d=d5, df_1m=d1, today_date=now_et.date())
            except Exception:
                pass
    except Exception:
        pass
    return prefetched


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

def get_stock_data(ticker_symbol, mode="MEDIUM", prefetched_hist=None, cal_entry=None):
    try:
        ticker = yf.Ticker(ticker_symbol)
        req_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
        if prefetched_hist is not None and not prefetched_hist.empty and req_cols.issubset(prefetched_hist.columns):
            hist = prefetched_hist.copy()
        else:
            hist = ticker.history(period="6mo", timeout=10)
            if hist is not None and not hist.empty:
                now_et = _now_et()
                h5 = ticker.history(period="5d", timeout=8)
                h1 = ticker.history(period="1d", interval="1m", timeout=8) if _is_tsx_regular_hours(now_et) else None
                hist = _overlay_fresh_bar(hist, df_5d=h5, df_1m=h1, today_date=now_et.date())
        if hist is None or hist.empty:
            return None

        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        now_et = _now_et()
        bar_date = hist.index[-1].date() if hasattr(hist.index[-1], "date") else now_et.date()
        stale_intraday = bool(_is_tsx_regular_hours(now_et) and bar_date < now_et.date())
        prev_close = float(prev["Close"])
        gap_pct = ((float(latest["Open"]) - prev_close) / prev_close) * 100.0 if prev_close > 0 else 0.0
        pct_from_low = ((float(latest["Close"]) - float(latest["Low"])) / float(latest["Low"])) * 100.0 if float(latest["Low"]) > 0 else 0.0
        cal = cal_entry if cal_entry is not None else get_corporate_calendar([ticker_symbol]).get(ticker_symbol, {})

        if mode == "SHORT":
            hist.ta.ema(length=5, append=True)
            hist.ta.ema(length=9, append=True)
            hist.ta.sma(length=50, append=True)
            hist.ta.rsi(length=7, append=True)
            hist.ta.atr(length=5, append=True)
            hist.ta.bbands(length=20, std=2, append=True)
            hist.ta.adx(length=14, append=True)

            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest

            if len(hist) > 10:
                vol_sma_10 = float(hist["Volume"].iloc[:-1].tail(10).mean())
            else:
                vol_sma_10 = float(hist["Volume"].rolling(window=10).mean().iloc[-1])

            market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
            market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)

            if now_et < market_open:
                minutes_passed = 0.0
            elif now_et > market_close:
                minutes_passed = 390.0
            else:
                minutes_passed = (now_et - market_open).total_seconds() / 60.0

            adjusted_sma = vol_sma_10 * _expected_intraday_vol_fraction(minutes_passed)
            vol_ratio = (float(latest["Volume"]) / adjusted_sma) if adjusted_sma > 0 else 1.0

            price = float(latest["Close"])
            ema_5 = float(latest["EMA_5"]) if "EMA_5" in latest and pd.notna(latest["EMA_5"]) else 0.0
            ema_9 = float(latest["EMA_9"]) if "EMA_9" in latest and pd.notna(latest["EMA_9"]) else 0.0
            prev_ema_5 = float(prev["EMA_5"]) if "EMA_5" in prev and pd.notna(prev["EMA_5"]) else ema_5
            dmp_14 = float(latest["DMP_14"]) if "DMP_14" in latest and pd.notna(latest["DMP_14"]) else 0.0
            dmn_14 = float(latest["DMN_14"]) if "DMN_14" in latest and pd.notna(latest["DMN_14"]) else 0.0
            sma_50 = float(latest["SMA_50"]) if "SMA_50" in latest and pd.notna(latest["SMA_50"]) else 0.0
            if ema_5 > ema_9 and ema_5 > 0:
                sma50_ceiling = (sma_50 > 0 and ema_9 < sma_50 and abs(price - sma_50) / sma_50 <= 0.015)
                if price >= ema_5 and ema_5 > prev_ema_5 and dmp_14 > dmn_14 and (price - ema_5) / ema_5 <= 0.03 and not sma50_ceiling:
                    crossover = "BULLISH (EMA5 > EMA9)"
                else:
                    crossover = "NEUTRAL (FILTERED)"
            elif ema_5 < ema_9:
                crossover = "BEARISH (EMA5 < EMA9)"
            else:
                crossover = "NEUTRAL"

            bb_lower_col = next((c for c in hist.columns if c.startswith("BBL_")), None)
            bb_mid_col = next((c for c in hist.columns if c.startswith("BBM_")), None)
            bb_upper_col = next((c for c in hist.columns if c.startswith("BBU_")), None)

            return {
                "Bar_Date": bar_date.isoformat(),
                "Stale_Intraday": stale_intraday,
                "Prev_Close": round(prev_close, 2),
                "Gap_Pct": round(gap_pct, 2),
                "Pct_From_Low": round(pct_from_low, 2),
                "Open": round(float(latest["Open"]), 2),
                "High": round(float(latest["High"]), 2),
                "Low": round(float(latest["Low"]), 2),
                "Price": round(price, 2),
                "Volume": int(latest["Volume"]),
                "Vol_SMA_10": round(vol_sma_10, 0),
                "Intraday_Dollar_Vol": round(float(latest["Volume"]) * price, 2),
                "Vol_Ratio": round(vol_ratio, 2),
                "EMA_Crossover": crossover,
                "EMA_5": round(ema_5, 2) if ema_5 > 0 else "N/A",
                "EMA_9": round(ema_9, 2) if ema_9 > 0 else "N/A",
                "RSI_7": round(float(latest["RSI_7"]), 2) if "RSI_7" in latest and pd.notna(latest["RSI_7"]) else "N/A",
                "ATR_5": round(float(latest["ATRr_5"]), 2) if "ATRr_5" in latest and pd.notna(latest["ATRr_5"]) else "N/A",
                "ADX_14": round(float(latest["ADX_14"]), 2) if "ADX_14" in latest and pd.notna(latest["ADX_14"]) else "N/A",
                "BB_Lower": round(float(latest[bb_lower_col]), 2) if bb_lower_col and pd.notna(latest[bb_lower_col]) else "N/A",
                "BB_Mid": round(float(latest[bb_mid_col]), 2) if bb_mid_col and pd.notna(latest[bb_mid_col]) else "N/A",
                "BB_Upper": round(float(latest[bb_upper_col]), 2) if bb_upper_col and pd.notna(latest[bb_upper_col]) else "N/A",
                "earnings_date": cal.get("earnings_date", "N/A"),
                "days_to_earnings": cal.get("days_to_earnings"),
                "trading_days_to_earnings": cal.get("trading_days_to_earnings"),
                "ex_dividend_date": cal.get("ex_dividend_date", "N/A"),
                "days_to_ex_dividend": cal.get("days_to_ex_dividend")
            }
        else:
            hist.ta.rsi(length=14, append=True)
            hist.ta.sma(length=50, append=True)
            hist.ta.bbands(length=50, std=2, append=True)
            latest = hist.iloc[-1]

            bb_upper_col = next((c for c in hist.columns if c.startswith("BBU_")), None)
            ex_div_date = cal.get("ex_dividend_date", "N/A")

            return {
                "Bar_Date": bar_date.isoformat(),
                "Stale_Intraday": stale_intraday,
                "Prev_Close": round(prev_close, 2),
                "Gap_Pct": round(gap_pct, 2),
                "Pct_From_Low": round(pct_from_low, 2),
                "Open": round(float(latest["Open"]), 2),
                "High": round(float(latest["High"]), 2),
                "Low": round(float(latest["Low"]), 2),
                "Price": round(float(latest["Close"]), 2),
                "Volume": int(latest["Volume"]),
                "RSI_14": round(float(latest["RSI_14"]), 2) if "RSI_14" in latest and pd.notna(latest["RSI_14"]) else "N/A",
                "SMA_50": round(float(latest["SMA_50"]), 2) if "SMA_50" in latest and pd.notna(latest["SMA_50"]) else "N/A",
                "BB_Upper": round(float(latest[bb_upper_col]), 2) if bb_upper_col and pd.notna(latest[bb_upper_col]) else "N/A",
                "Ex_Div_Date": ex_div_date,
                "earnings_date": cal.get("earnings_date", "N/A"),
                "days_to_earnings": cal.get("days_to_earnings"),
                "trading_days_to_earnings": cal.get("trading_days_to_earnings"),
                "ex_dividend_date": ex_div_date,
                "days_to_ex_dividend": cal.get("days_to_ex_dividend")
            }
    except Exception:
        if mode == "SHORT":
            return {
                "Bar_Date": "N/A", "Stale_Intraday": False,
                "Prev_Close": "N/A", "Gap_Pct": "N/A", "Pct_From_Low": "N/A",
                "Open": "N/A", "High": "N/A", "Low": "N/A", "Price": "N/A",
                "Volume": 0, "Vol_SMA_10": "N/A", "Intraday_Dollar_Vol": 0.0,
                "Vol_Ratio": "N/A", "EMA_Crossover": "N/A", "EMA_5": "N/A", "EMA_9": "N/A",
                "RSI_7": "N/A", "ATR_5": "N/A", "ADX_14": "N/A", "BB_Lower": "N/A", "BB_Mid": "N/A", "BB_Upper": "N/A"
            }
        else:
            return {
                "Bar_Date": "N/A", "Stale_Intraday": False,
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


CALENDAR_CACHE_FILE = os.path.join(BASE_DIR, "corporate_calendar_cache.json")
CALENDAR_CACHE_TTL = 86400  # 24 hours


def _refresh_calendar_days(calendar_data, ref_date=None):
    """Dynamically recomputes calendar and trading-day deltas from cached ISO dates on every read."""
    today = ref_date or _now_et().date()
    today_iso = today.isoformat()
    out = {}
    for sym, entry in calendar_data.items():
        rec = dict(entry)
        ed_str = str(rec.get("earnings_date", "N/A"))
        if ed_str and ed_str != "N/A":
            try:
                ed_date = datetime.date.fromisoformat(ed_str[:10])
                rec["days_to_earnings"] = (ed_date - today).days
                rec["trading_days_to_earnings"] = int(np.busday_count(today_iso, ed_date.isoformat()))
            except ValueError:
                pass
        else:
            rec.setdefault("trading_days_to_earnings", None)

        ex_str = str(rec.get("ex_dividend_date", "N/A"))
        if ex_str and ex_str != "N/A":
            try:
                ex_date = datetime.date.fromisoformat(ex_str[:10])
                rec["days_to_ex_dividend"] = (ex_date - today).days
            except ValueError:
                pass
        out[sym] = rec
    return out


def get_corporate_calendar(tickers=None, ref_date=None):
    """Fetches and caches upcoming earnings and ex-dividend dates (24h cache, dynamic trading-day delta)."""
    cache_ts = 0.0
    calendar_data = {}

    if os.path.exists(CALENDAR_CACHE_FILE):
        try:
            with open(CALENDAR_CACHE_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            cache_ts = float(raw.get("_timestamp", 0.0))
            if time.time() - cache_ts < CALENDAR_CACHE_TTL and isinstance(raw.get("calendar"), dict):
                calendar_data = dict(raw["calendar"])
        except Exception:
            calendar_data = {}

    req_tickers = list(tickers or get_tickers())
    missing = [t for t in req_tickers if t not in calendar_data]
    if not missing and calendar_data:
        return _refresh_calendar_days(calendar_data, ref_date=ref_date)

    now_date = ref_date or _now_et().date()
    for t in missing:
        ed_str, days_to_ed, ex_div_str, days_to_ex_div = "N/A", None, "N/A", None
        try:
            cal = yf.Ticker(t).calendar
            if isinstance(cal, dict):
                ed = cal.get("Earnings Date")
                if isinstance(ed, list) and ed and isinstance(ed[0], datetime.date):
                    ed_date = ed[0]
                    ed_str = ed_date.strftime("%Y-%m-%d")
                    days_to_ed = (ed_date - now_date).days
                ex_div = cal.get("Ex-Dividend Date")
                if isinstance(ex_div, datetime.date):
                    ex_div_str = ex_div.strftime("%Y-%m-%d")
                    days_to_ex_div = (ex_div - now_date).days
        except Exception:
            pass

        calendar_data[t] = {
            "earnings_date": ed_str,
            "days_to_earnings": days_to_ed,
            "ex_dividend_date": ex_div_str,
            "days_to_ex_dividend": days_to_ex_div
        }

    new_ts = cache_ts if (cache_ts > 0 and time.time() - cache_ts < CALENDAR_CACHE_TTL) else time.time()
    try:
        with open(CALENDAR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"_timestamp": new_ts, "calendar": calendar_data}, f, indent=2)
    except Exception:
        pass

    return _refresh_calendar_days(calendar_data, ref_date=now_date)


def get_macro_alignment(macro_symbols=None):
    """Checks daily directional alignment for Gold (GC=F), Crude Oil (CL=F), Copper (HG=F), and ^VIX panic regime."""
    syms = list(macro_symbols or ["GC=F", "CL=F", "HG=F"])
    state = {s: True for s in syms}
    state.update({"VIX_PANIC": False, "VIX_Level": None, "details": {}})

    for sym in syms:
        try:
            hist = yf.Ticker(sym).history(period="5d", timeout=8)
            if hist is not None and len(hist) >= 2:
                cur = float(hist["Close"].iloc[-1])
                prev = float(hist["Close"].iloc[-2])
                chg_pct = ((cur - prev) / prev) * 100.0 if prev > 0 else 0.0
                state[sym] = cur >= prev
                state["details"][sym] = {"price": round(cur, 2), "chg_pct": round(chg_pct, 2), "green": cur >= prev}
        except Exception:
            pass

    try:
        vh = yf.Ticker("^VIX").history(period="5d", timeout=8)
        if vh is not None and len(vh) >= 2:
            v_cur, v_prev = float(vh["Close"].iloc[-1]), float(vh["Close"].iloc[-2])
            v_chg_pct = ((v_cur - v_prev) / v_prev) * 100.0 if v_prev > 0 else 0.0
            is_panic = v_cur >= 25.0 or (v_prev > 0 and v_chg_pct >= 10.0)
            state["VIX_PANIC"] = is_panic
            state["VIX_Level"] = round(v_cur, 2)
            state["details"]["^VIX"] = {"price": round(v_cur, 2), "chg_pct": round(v_chg_pct, 2), "panic": is_panic}
    except Exception:
        pass

    return state


def fetch_universe_snapshot(config=None):
    """Fetches a consolidated, CDN-fresh snapshot of portfolio holdings, 32-ticker universe, macro, and calendar."""
    cfg = config if config is not None else load_config()
    mode = get_current_mode(cfg)
    balances = get_acb_and_balances()
    positions = balances.get("positions", {})

    base_tickers = [normalize_ticker(t) for t in get_tickers(cfg)]
    held_extra = [
        normalize_ticker(t) for t, p in positions.items()
        if p.get("shares", 0) > 0 and normalize_ticker(t) not in base_tickers
    ]
    all_tickers = list(dict.fromkeys(base_tickers + held_extra))

    cal_map = get_corporate_calendar(all_tickers)
    prefetched = prefetch_histories(all_tickers, period="6mo")
    market_data = {}
    for t in all_tickers:
        sd = get_stock_data(t, mode=mode, prefetched_hist=prefetched.get(t), cal_entry=cal_map.get(t, {}))
        if sd is not None:
            market_data[t] = sd

    macro_topics = cfg.get("macro_commodities", ["CL=F", "GC=F", "HG=F"])
    macro_state = get_macro_alignment(macro_topics)

    return {
        "config": cfg,
        "mode": mode,
        "balances": balances,
        "tickers": all_tickers,
        "cal_map": cal_map,
        "market_data": market_data,
        "macro_state": macro_state,
    }

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

def generate_dossier(snapshot=None):
    snap = snapshot if snapshot is not None else fetch_universe_snapshot()
    config = snap.get("config") or load_config()
    mode = snap.get("mode") or get_current_mode(config)
    mode_display = "SHORT TERM (1-WEEK HORIZON)" if mode == "SHORT" else "MEDIUM TERM"

    dossier = f"=== CURRENT MODE: {mode_display} ===\n"
    dossier += f"Date: {_now_et().strftime('%Y-%m-%d %H:%M:%S')} ET\n\n"

    balances = snap.get("balances", {})
    positions = balances.get("positions", {})
    cash = balances.get("cash", 0.0)

    dossier += f"--- PORTFOLIO & PRICING ---\n"
    dossier += f"Available Free Cash: ${cash:.2f}\n\n"

    tickers = snap.get("tickers", [])
    stop_loss = get_stop_loss_pct(config)
    cal_map = snap.get("cal_map", {})
    all_market_data = snap.get("market_data", {})
    macro_state = snap.get("macro_state", {})
    macro_topics = config.get("macro_commodities", ["CL=F", "GC=F", "HG=F"])

    total_unrealized_pnl = 0.0
    has_open_positions = False

    for t in tickers:
        market_data = all_market_data.get(t)
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

        price_str = f"${current_price:.2f}" if isinstance(current_price, (int, float)) else str(current_price)

        dossier += f"{t}:\n"
        dossier += f"  - Shares Owned: {shares:.4f}\n"
        dossier += f"  - Avg Purchase Price: {acb_str}\n"
        dossier += f"  - Current Market Price: {price_str}\n"
        if isinstance(market_data, dict):
            if market_data.get("Stale_Intraday"):
                dossier += f"  - [⚠️ STALE INTRADAY BAR: Last bar {market_data.get('Bar_Date', 'N/A')} does not match today; suppress new buys.]\n"
            dossier += f"  - Previous Close: ${market_data.get('Prev_Close', 'N/A')} (Gap: {market_data.get('Gap_Pct', 0.0):+.2f}%)\n"
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
        td_to_ed = cal.get("trading_days_to_earnings")
        if td_to_ed is None:
            td_to_ed = cal.get("days_to_earnings")
        ex_div_date = cal.get("ex_dividend_date")
        td_to_ex_div = cal.get("trading_days_to_ex_dividend")
        if td_to_ex_div is None:
            td_to_ex_div = cal.get("days_to_ex_dividend")

        if ed_date and ed_date != "N/A":
            ed_txt = f"{ed_date} ({td_to_ed}td away)" if td_to_ed is not None else ed_date
            dossier += f"  - Upcoming Earnings Date: {ed_txt}\n"
            if td_to_ed is not None and 0 <= td_to_ed <= 3:
                dossier += f"  - [⚠️ EARNINGS RISK: Reporting in {td_to_ed} trading days on {ed_date}. High binary gap risk. Avoid new BUY.]\n"

        if ex_div_date and ex_div_date != "N/A":
            ex_txt = f"{ex_div_date} ({td_to_ex_div}td away)" if td_to_ex_div is not None else ex_div_date
            dossier += f"  - Next Ex-Dividend Date: {ex_txt}\n"
            if td_to_ex_div is not None and 0 <= td_to_ex_div <= 3:
                dossier += f"  - [📅 UPCOMING EX-DIVIDEND: Ex-date {ex_div_date}. Expect mechanical dividend price drop.]\n"

        dossier += "\n"

    if has_open_positions:
        dossier += f"--- TOTAL UNREALIZED P&L: ${total_unrealized_pnl:.2f} ---\n\n"

    # Macro commodities & VIX panic gauge
    details = macro_state.get("details", {})
    if macro_topics or "^VIX" in details:
        dossier += f"--- MACRO COMMODITIES ---\n"
        for macro in macro_topics:
            d = details.get(macro)
            if d:
                status = "GREEN" if d.get("green") else "RED"
                dossier += f"{macro}: ${d['price']:.2f} ({d['chg_pct']:+.2f}% vs Prev Close, {status})\n"
            else:
                dossier += f"{macro}: N/A\n"
        if "^VIX" in details:
            vd = details["^VIX"]
            panic_lbl = " [⚠️ VIX PANIC - CAPITULATION SUPPRESSED]" if vd.get("panic") else ""
            dossier += f"^VIX: {vd['price']:.2f} ({vd['chg_pct']:+.2f}%){panic_lbl}\n"
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
1. Macroeconomic Context (Canada, USA, World): Apply the single consolidated Macroeconomic Briefing across all stocks. Do NOT look for individual per-stock news feeds. Synthesize Canada, USA, and World macro developments into all stock assessments.
2. Capitulation Reversal & Anti-Knife Guard: If Vol_Ratio > 1.25x while 7-day RSI < 35 (oversold), treat as Capitulation ONLY IF Price > Open (green candle), Pct_From_Low is between +1.50% and +4.50% (chasing >4.50% is blocked), and ^VIX is not in PANIC (>=25 or +10% spike). Cap Capitulation entries at 15% tranche size.
3. Momentum Breakout (EMA 5 > EMA 9): Require Price > Open (intraday green candle), Vol_Ratio >= 1.00x, 7-day RSI <= 68.0, EMA5 extension <= 3.0% above EMA9, and 14-day ADX > 20.0.
4. No Double-Bypass & Overbought Rules: Allow ONE single bypass only with institutional volume >= 1.50x: either weak ADX (<= 20) OR slightly elevated RSI (65.0 < RSI <= 68.0), NEVER both at once. Never buy if 7-day RSI > 68.0.
5. Thin-Liquidity & Stale-Data Guards: Do not initiate buys if [⚠️ STALE INTRADAY BAR] is present or average 10-day daily volume is below 150,000 shares (unless intraday dollar volume >= $1,000,000 CAD).
6. Position Sizing & Portfolio Caps: Scale standard tranches dynamically between 15% and 35% of available cash (higher for Volume Boost >= 1.60x, RSI 40-62, ADX > 28; lower for low-volume 1.00-1.25x or stretched EMA). Enforce max 25% of total equity per ticker and max 35% of total equity per sector.
7. Scale-In & Cooldown Discipline: Allow at most 1 additional Scale-In buy (max 2 buys per position cycle) after at least 4 hours since the last buy, Price > Open, >= +0.5% above prior buy price, and >= +1.0% unrealized gain. Enforce a 4-hour post-stop cooldown after any losing SELL before re-entering the same ticker.
8. Risk Management (Stop Loss & 4-Tier Ratchet): Stop loss is -{stop_loss}% (-1% tighter to -{stop_loss - 1.0}% if Ex-Dividend is within 3 trading days), buffered by an extra 2.0% during Opening Chop (9:30-10:00 AM ET) unless down > 7% catastrophic loss. Apply the 4-tier ratchet: >= +2.0% cut risk in half; >= +2.5% move stop to breakeven; >= +3.5% trail +1.5%; >= +5.0% tighten trail to +3.0%.
9. Day-4 Stagnation Exit: If any position has been held >= 4 trading days (no ticker exemptions) and is negative with Price < min(EMA_5, EMA_9), recommend immediate SELL unless actively recovering intraday (Price > Open AND Price >= Prev_Close * 1.01) or EMA 5 > EMA 9 bullish alignment remains intact.
10. Target & Profit Hurdle: Target Sell Price = max(Mid-Bollinger, Price + 1.5 * ATR), subject to a minimum net +2.5% profit hurdle above entry price (accounting for any configured commission).
11. Earnings & Time-of-Day Gates: Block new buys within 3 trading days of earnings (`0 <= trading_days <= 3`). Suppress new buys during Opening Chop (9:30-10:00 AM ET) and Midday Fake-Out (11:30 AM-2:00 PM ET).
12. Commodity Macro Alignment: Verify GC=F (Precious Metals), CL=F (Energy), and HG=F (TECK-B.TO) are green before buying linked stocks. If you own 0 shares and do not buy, recommend AVOID or IGNORE. Never repeat a failed thesis from PREVIOUS ADVICE HISTORY.

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
