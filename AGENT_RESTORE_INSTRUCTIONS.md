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
The `telegram_daemon.py` script listens to the user's Telegram messages, uses the Gemini API to parse natural language trades, and updates `trades.csv`.
* **To Start:** The user simply needs to double-click `start_daemon.bat` OR run:
  ```bash
  C:\Users\Aamir\miniforge3\python.exe telegram_daemon.py
  ```

## 3. Agent Scheduling Instructions (AI Agent Action)
The core analytical engine relies on the Antigravity Agent waking up, fetching the prompt from `market_analyzer.py`, formulating a trading recommendation, and sending it via `send_telegram.py`. 

**You MUST use your native `run_command` tool to start the File Watcher background listener:**
```bash
C:\Users\Aamir\miniforge3\python.exe file_watcher.py
```
This script acts as the bridge connecting the Telegram Daemon to your chat context!

**You MUST also use your native `schedule` tool to immediately recreate the following three background cron tasks:**

### Task 1: Hourly Market Scan
* **CronExpression:** `0 10-15 * * 1-5`
* **Prompt:** 
  > [Hourly Scan] Execute an hourly market analysis! Please read the live dossier by executing a python script to import and run `market_analyzer.generate_dossier()`. Write your trading analysis based on the dossier using your own brain, and push your response JSON to `outgoing_queue.jsonl` using a python script. Be sure to format your analysis correctly and concise!

### Task 2: Pre-Close Market Scan
* **CronExpression:** `30 15 * * 1-5`
* **Prompt:** 
  > [3:30 PM Scan] Execute a pre-close market analysis! Please read the live dossier by executing a python script to import and run `market_analyzer.generate_dossier()`. Write your trading analysis based on the dossier using your own brain, and push your response JSON to `outgoing_queue.jsonl` using a python script. Be sure to format your analysis correctly and concise!

### Task 3: End-of-Day Summary
* **CronExpression:** `5 16 * * 1-5`
* **Prompt:** 
  > [EOD Summary] Execute the End-of-Day summary! Please read the live dossier by executing a python script to import and run `market_analyzer.generate_dossier()`. Write your EOD summary based on the dossier using your own brain, and push your response JSON to `outgoing_queue.jsonl` using a python script.

## 4. Operational Notes
* **Native Antigravity Engine:** The scheduled tasks rely exclusively on Antigravity reading the dossier and generating the response natively to avoid external API limits.
