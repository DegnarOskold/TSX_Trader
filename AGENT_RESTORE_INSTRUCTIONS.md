# TSX Trading Advisor: System State & Restore Instructions

> [!IMPORTANT]  
> **ATTENTION AI AGENT:** If you are reading this file, the user has likely lost their previous chat session and needs you to restore the automated TSX Trading Advisor. Follow the instructions below to immediately bring the system back online exactly as it was configured.

## 1. System Overview & Architecture
This project is an autonomous stock trading advisor tracking the user's dynamic portfolio configured in `config.json`. It operates at $0 cost using local Python, the `yfinance` library, and the Telegram Bot API. 
* **Project Directory:** `c:\Users\Aamir\OneDrive\TSX-Trader`
* **Python Environment:** Miniforge must be used to execute scripts to avoid path issues: `C:\Users\Aamir\miniforge3\python.exe`
* **Local Ledger:** `trades.csv` tracks the user's trades, portfolio balances, and calculates Adjusted Cost Base (ACB).
* **Environment Variables:** Credentials (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`) are stored in `.env`.

## 2. Background Listener (User Action)
The `telegram_daemon.py` script listens to the user's Telegram messages, relays them to `incoming_queue.jsonl` for the Antigravity AI agent to process, and delivers AI-generated responses from `outgoing_queue.jsonl` back to Telegram.
* **To Start:** The user simply needs to double-click `start_daemon.bat` OR run:
  ```bash
  C:\Users\Aamir\miniforge3\python.exe telegram_daemon.py
  ```

## 3. Agent Scheduling Instructions (AI Agent Action)
The core analytical engine relies on the Antigravity Agent waking up, fetching the prompt from `market_analyzer.py`, formulating a trading recommendation, and pushing it to `outgoing_queue.jsonl` to be sent by the daemon.

**You MUST use your native `run_command` tool to start the File Watcher background listener:**
```bash
C:\Users\Aamir\miniforge3\python.exe file_watcher.py
```
This script acts as the bridge connecting the Telegram Daemon to your chat context!

**You MUST also use your native `schedule` tool to immediately recreate the following two background cron tasks:**

### Task 1: 30-Minute Interval Market Scan
* **CronExpression:** `*/30 9-16 * * 1-5`
* **Prompt:** 
  > Trigger: Interval Scan. Please run the `send_interval_scan.py` script to generate market updates. Also, as per AGENTS.md, check your running tasks using `manage_task(Action='list')` and restart `file_watcher.py` if it is not actively running.

### Task 2: End-of-Day (EOD) Summary
* **CronExpression:** `5 16 * * 1-5`
* **Prompt:** 
  > Trigger: End-of-Day (EOD) Summary. Please run the `send_eod_summary.py` script to generate the EOD summary. Also, as per AGENTS.md, check your running tasks using `manage_task(Action='list')` and restart `file_watcher.py` if it is not actively running.

## 4. Operational Notes
* **Native Antigravity Engine:** The scheduled tasks rely exclusively on Antigravity reading the dossier and generating the response natively to avoid external API limits.
