# TSX-Trader AI Assistant

**TSX-Trader** is an autonomous, agentic AI trading assistant designed specifically for the Toronto Stock Exchange (TSX). It actively monitors a curated watchlist of Canadian equities and provides real-time, actionable trading intelligence directly to the user via Telegram.

## Core Features
* **Automated Market Scans:** Executes on a strict 30-minute schedule (10:00 AM - 3:30 PM ET) to continuously evaluate the market.
* **Technical Analysis Engine:** Generates comprehensive dossiers for each watched stock, calculating critical indicators such as:
  * Exponential Moving Averages (EMA 5 & 9)
  * Relative Strength Index (RSI 7-day)
  * Average True Range (ATR)
  * Bollinger Bands (20-day)
  * Intraday pricing trends (Gap %, Distance from Low of Day, Volume Capitulation Ratios)
* **Qualitative Analysis:** Integrates real-time news headlines and macroeconomic commodity prices (Crude Oil, Gold) to add qualitative context to technical setups.
* **Strict Risk Management:** Enforces rigid entry/exit rules defined by the user (e.g., rejecting weak dead-cat bounces, requiring strict RSI triggers for V-bottom reversals, and enforcing time-of-day filters to avoid mid-day algorithmic chop).
* **Telegram Integration:** Seamlessly communicates all alerts, dossier summaries, and BUY/SELL recommendations to the operator through a secure Telegram daemon (`telegram_daemon.py`). It also supports interactive natural language queries from the user.
* **Security Protocol:** Implements a strict 8-digit PIN challenge for any remote commands that attempt to modify source code or execute system shell commands, ensuring operational security.

## Watchlist
The tool currently tracks the following TSX equities:
- **CNQ.TO** (Canadian Natural Resources)
- **ABX.TO** (Barrick Gold)
- **CP.TO** (Canadian Pacific Kansas City)
- **GIB-A.TO** (CGI Inc.)
- **WCN.TO** (Waste Connections)
- **CLS.TO** (Celestica)

## Architecture
- `market_analyzer.py`: The core engine that fetches data (via `yfinance`), computes technical indicators, and generates the text dossiers.
- `file_watcher.py`: A background daemon that monitors the `outgoing_queue.jsonl` file and dispatches new messages to Telegram.
- `telegram_daemon.py`: A daemon that listens for incoming Telegram messages and appends them to `incoming_queue.jsonl` for the AI agent to process.
- `.agents/AGENTS.md`: Contains the declarative rule-set and behavioral guidelines that govern the AI's trading logic and decision-making framework.
