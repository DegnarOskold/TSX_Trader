from fpdf import FPDF
from fpdf.enums import XPos, YPos
import datetime

VERSION = "1.1.0"
GENERATED = datetime.datetime.now().strftime("%B %d, %Y")

class PDF(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 10)
        self.set_fill_color(20, 25, 40)
        self.set_text_color(200, 210, 230)
        self.cell(0, 8, f"TSX Trading Advisor  |  Technical Reference Manual  |  v{VERSION}",
                  fill=True, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(8)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(140, 140, 160)
        self.cell(0, 10, f"Page {self.page_no()}  |  TSX Trading Advisor v{VERSION}  |  Confidential", align="C")
        self.set_text_color(0, 0, 0)

    def chapter_title(self, num, title):
        self.set_font("helvetica", "B", 13)
        self.set_fill_color(20, 25, 40)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, f"  {num}.  {title}", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section_title(self, title):
        self.set_font("helvetica", "B", 11)
        self.set_text_color(20, 70, 160)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body(self, text):
        self.set_font("helvetica", "", 10)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("helvetica", "", 10)
        self.set_x(self.get_x() + 8)
        self.multi_cell(0, 5.5, f"  -  {text}")
        self.ln(0.5)

    def code_block(self, code):
        self.set_font("courier", "", 9)
        self.set_fill_color(238, 240, 248)
        self.set_draw_color(170, 175, 200)
        self.multi_cell(0, 5, code, fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)
        self.ln(3)

    def table_header(self, cols):
        self.set_font("helvetica", "B", 9)
        self.set_fill_color(40, 50, 80)
        self.set_text_color(255, 255, 255)
        for text, w in cols:
            self.cell(w, 6.5, text, border=1, fill=True)
        self.ln()
        self.set_text_color(0, 0, 0)

    def table_row(self, cols, shade=False):
        self.set_font("helvetica", "", 9)
        self.set_fill_color(242, 244, 252) if shade else self.set_fill_color(255, 255, 255)
        for text, w in cols:
            self.multi_cell(w, 6.5, text, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.ln()
        self.set_fill_color(255, 255, 255)

    def note_box(self, text, color=(230, 240, 255)):
        self.set_fill_color(*color)
        self.set_draw_color(120, 150, 200)
        self.set_font("helvetica", "I", 9)
        self.multi_cell(0, 5.5, f"  (i)  {text}", fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)
        self.ln(2)

    def warn_box(self, text):
        self.note_box(text, color=(255, 245, 220))

    def divider(self):
        self.set_draw_color(180, 185, 210)
        self.line(self.get_x(), self.get_y(), self.get_x() + 190, self.get_y())
        self.set_draw_color(0, 0, 0)
        self.ln(4)


def create_pdf():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)

    # COVER PAGE
    pdf.add_page()
    pdf.ln(35)
    pdf.set_font("helvetica", "B", 32)
    pdf.set_text_color(20, 25, 40)
    pdf.cell(0, 16, "TSX Trading Advisor", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)
    pdf.set_font("helvetica", "", 18)
    pdf.set_text_color(60, 80, 130)
    pdf.cell(0, 10, "Technical Reference Manual", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_font("helvetica", "I", 12)
    pdf.set_text_color(110, 120, 150)
    pdf.cell(0, 8, "Architecture, Configuration, Data Flow, AI Logic and Trading Rules",
             align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(30)
    pdf.set_fill_color(235, 240, 255)
    pdf.set_draw_color(150, 170, 220)
    pdf.set_font("helvetica", "", 11)
    pdf.set_text_color(40, 50, 90)
    pdf.multi_cell(0, 8,
        f"  Version:    {VERSION}\n"
        f"  Generated:  {GENERATED}\n"
        f"  Author:     Antigravity AI Agent\n"
        f"  Repository: TSX-Trader (OneDrive)\n"
        f"  Mode:       SHORT TERM (1-Week Momentum)",
        fill=True, border=1)
    pdf.set_draw_color(0, 0, 0)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(12)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(160, 165, 180)
    pdf.multi_cell(0, 5,
        "This document is auto-generated and reflects the live codebase. "
        "It is intended for the system operator only.")
    pdf.set_text_color(0, 0, 0)

    # TABLE OF CONTENTS
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.set_text_color(20, 25, 40)
    pdf.cell(0, 10, "Table of Contents", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.divider()
    toc = [
        ("1.", "System Overview"),
        ("2.", "Architecture and Data Flow"),
        ("3.", "File Inventory"),
        ("4.", "Configuration Reference (config.json)"),
        ("5.", "Market Dossier Structure"),
        ("6.", "AI Trading Rules and Logic"),
        ("7.", "Trading Prompt System Instructions"),
        ("8.", "Telegram Security Protocol"),
        ("9.", "Session Restore Procedure"),
        ("10.", "Known Limitations and Operational Notes"),
    ]
    for num, title in toc:
        pdf.set_font("helvetica", "", 11)
        pdf.set_text_color(20, 25, 40)
        pdf.cell(20, 7, num)
        pdf.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # CHAPTER 1: SYSTEM OVERVIEW
    pdf.add_page()
    pdf.chapter_title("1", "System Overview")
    pdf.body(
        "TSX Trading Advisor is a zero-cost, single-user autonomous stock trading assistant "
        "for Canadian equities on the Toronto Stock Exchange. It continuously monitors a user-defined "
        "portfolio, fetches live market data and macro news, and delivers scheduled AI-generated "
        "BUY/SELL/HOLD recommendations and End-of-Day recaps via Telegram.\n\n"
        "The system runs entirely locally on a Windows machine using Python (Miniforge). There are no cloud "
        "services, no subscription fees, and no external AI API keys. All AI reasoning is performed "
        "natively by the Antigravity agent session."
    )
    pdf.section_title("Key Characteristics")
    pdf.bullet("Horizon: SHORT TERM (1-week momentum and mean-reversion setups)")
    pdf.bullet("Data: Live prices, indicators, and macro context fetched at 30-minute intervals")
    pdf.bullet("Delivery: Telegram Bot notifications directly to the operator's phone")
    pdf.bullet("Control: Operator logs trades via natural language text messages to the bot")
    pdf.bullet("Portfolio: Configurable list of TSX tickers and commodity monitors in config.json")
    pdf.bullet("Scheduling: 30-minute scans (9:30 AM - 4:00 PM ET) + EOD summary (4:05 PM ET)")
    pdf.ln(2)
    pdf.section_title("What the System Does NOT Do")
    pdf.bullet("It does NOT execute trades automatically. All trades must be placed manually by the operator.")
    pdf.bullet("It does NOT access broker APIs or hold private brokerage credentials.")
    pdf.warn_box(
        "IMPORTANT: This tool provides AI-generated trading suggestions only. "
        "All investment decisions are the sole responsibility of the operator."
    )

    # CHAPTER 2: ARCHITECTURE
    pdf.add_page()
    pdf.chapter_title("2", "Architecture and Data Flow")
    pdf.section_title("2.1 High-Level Architecture")
    pdf.body(
        "The system is split into three distinct layers: a deterministic Data Engine, "
        "an AI Reasoning Layer, and a Telegram Delivery Layer. Communication is mediated via local "
        "JSONL queue files and standard output streams, creating a clean, fault-tolerant bridge."
    )
    pdf.code_block(
        "  [Telegram User]\n"
        "       |\n"
        "       v  (sends message)\n"
        "  [telegram_daemon.py]  <--- One-Shot Mode (streams NEW_MESSAGE to stdout)\n"
        "       |\n"
        "       +--------------------+ (wakes agent session directly or via queue)\n"
        "       v                    v\n"
        "  [Antigravity Agent]  <--- The AI brain\n"
        "       |\n"
        "       +--> runs send_interval_scan.py / market_analyzer.py\n"
        "       +--> reasons natively, evaluates rules & macro context\n"
        "       |\n"
        "       v  (writes response)\n"
        "  [outgoing_queue.jsonl]\n"
        "       |\n"
        "       v  (polled every 2s by)\n"
        "  [telegram_daemon.py]  ---> [Telegram User]\n"
        "                         +-> log_advice(advice_history.txt)"
    )
    pdf.section_title("2.2 Scheduled Analysis Flow")
    pdf.table_header([("Task", 55), ("Cron Expression", 65), ("Description", 70)])
    sched = [
        ("30-min Market Scan", "*/30 9-16 * * 1-5", "Full portfolio scan, true P&L, BUY/SELL signals"),
        ("End-of-Day Summary", "5 16 * * 1-5", "Portfolio recap, realized trades, next-day watchlist"),
    ]
    for i, (a, b, c) in enumerate(sched):
        pdf.table_row([(a, 55), (b, 65), (c, 70)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("2.3 Advice History and Memory")
    pdf.body(
        "Every message sent through outgoing_queue.jsonl is automatically logged to "
        "advice_history.txt by telegram_daemon.py. This provides the AI with rolling "
        "memory of its own prior advice. The get_cleaned_advice_history() function "
        "trims the file on each dossier generation to retain: up to the last 5 entries "
        "from today plus the final entry from the prior 5 calendar days."
    )
    pdf.note_box(
        "An OS-level file lock (advice.lock) prevents corruption from concurrent writes. "
        "Stale lock files older than 30 seconds are automatically removed."
    )

    # CHAPTER 3: FILE INVENTORY
    pdf.add_page()
    pdf.chapter_title("3", "File Inventory")
    pdf.section_title("3.1 Core Python Scripts")
    pdf.table_header([("File", 58), ("Role", 132)])
    files = [
        ("market_analyzer.py", "Core data engine: prices, indicators, tripartite macro news, dossier generator"),
        ("send_interval_scan.py", "30-min interval scan script: calculates equity/P&L, checks signals, dispatches to Telegram"),
        ("send_eod_summary.py", "EOD summary script: cumulative realized P&L, trade recap, commodity wrap, watchlist"),
        ("telegram_daemon.py", "Telegram bot relay: one-shot listener, polls outgoing queue, sends messages, logs advice"),
        ("file_watcher.py", "Daemon monitor bridge: loops continuously, watches incoming messages to wake agent"),
        ("generate_pdf.py", "Documentation generator: produces this technical manual from source"),
        ("queue_reply.py", "Utility script: quickly queues responses into outgoing_queue.jsonl"),
    ]
    for i, (a, b) in enumerate(files):
        pdf.table_row([(a, 58), (b, 132)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("3.2 Configuration and Data Files")
    pdf.table_header([("File", 58), ("Purpose", 132)])
    configs = [
        ("config.json", "Portfolio ticker list, macro commodities (CL=F, GC=F, HG=F), mode (SHORT), stop-loss %"),
        ("trades.csv", "Trade ledger: BUY/SELL/DEPOSIT/DIVIDEND history, Adjusted Cost Base, running cash balance"),
        ("advice_history.txt", "Rolling log of all AI advice sent to Telegram"),
        (".env", "Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_PIN, TELEGRAM_PIN_HINT"),
        (".gitignore", "Excludes .env, *.lock, *.log, __pycache__, cache JSONs, queue files from git"),
        ("requirements.txt", "Python dependencies for pip installation (yfinance, pandas, fpdf2, python-dotenv)"),
        ("AGENT_RESTORE_INSTRUCTIONS.md", "Step-by-step AI session restore guide for agent restarts"),
        (".agents/AGENTS.md", "Persistent agent rules: trading strategy overrides and security protocol"),
    ]
    for i, (a, b) in enumerate(configs):
        pdf.table_row([(a, 58), (b, 132)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("3.3 Runtime Queue Files (transient)")
    pdf.table_header([("File", 58), ("Purpose", 132)])
    queues = [
        ("incoming_queue.jsonl", "Telegram messages from user, waiting for AI processing"),
        ("incoming_processing.jsonl", "Atomic rename during processing (prevents double-read)"),
        ("outgoing_queue.jsonl", "AI responses queued for Telegram delivery"),
        ("outgoing_processing.jsonl", "Atomic rename during daemon polling"),
        ("advice.lock", "OS-level mutex protecting advice_history.txt writes"),
    ]
    for i, (a, b) in enumerate(queues):
        pdf.table_row([(a, 58), (b, 132)], shade=(i % 2 == 1))
    pdf.note_box("Queue files and cache JSON files are ephemeral and excluded by .gitignore.")

    # CHAPTER 4: CONFIG.JSON
    pdf.add_page()
    pdf.chapter_title("4", "Configuration Reference (config.json)")
    pdf.body("config.json provides a streamlined configuration structure:")
    pdf.code_block(
        "{\n"
        "  \"mode\": \"SHORT\",\n"
        "  \"portfolio\": [\n"
        "    \"CNQ.TO\",\n"
        "    \"ABX.TO\",\n"
        "    \"CP.TO\",\n"
        "    \"CLS.TO\",\n"
        "    \"SHOP.TO\",\n"
        "    \"CNR.TO\"\n"
        "  ],\n"
        "  \"macro_commodities\": [\n"
        "    \"CL=F\",\n"
        "    \"GC=F\",\n"
        "    \"HG=F\"\n"
        "  ],\n"
        "  \"stop_loss_pct\": 5.0\n"
        "}"
    )
    pdf.section_title("Fields")
    pdf.table_header([("Field", 50), ("Type", 30), ("Description", 110)])
    flds = [
        ("mode", "string", "\"SHORT\" (1-week momentum) or \"MEDIUM\" (2-4 week swing). Controls indicators used."),
        ("portfolio", "array", "Array of equity ticker symbols on the TSX to actively track and analyze."),
        ("macro_commodities", "array", "Key commodities (Crude Oil, Gold, Copper) tracked for sector sentiment."),
        ("stop_loss_pct", "float", "Baseline stop-loss threshold percentage (typically 5.0%)."),
    ]
    for i, (a, b, c) in enumerate(flds):
        pdf.table_row([(a, 50), (b, 30), (c, 110)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("Consolidated Tripartite Macro Briefing")
    pdf.body(
        "Instead of spamming individual news feeds for dozens of stocks, the engine synthesizes "
        "a single high-level tripartite macroeconomic briefing across:\n"
        "  1. Canada Macro: Bank of Canada policy, TSX composite trends, domestic CPI/inflation.\n"
        "  2. USA Macro: Federal Reserve rate expectations, US labor/inflation data, S&P 500 sentiment.\n"
        "  3. World / Global Macro: Geopolitical events, global trade dynamics, central banks, and commodity supplies."
    )

    # CHAPTER 5: DOSSIER STRUCTURE
    pdf.add_page()
    pdf.chapter_title("5", "Market Dossier Structure")
    pdf.body(
        "The dossier is a structured plain-text document generated by market_analyzer.generate_dossier() "
        "on every scheduled scan or manual analysis request. It contains five key sections."
    )
    pdf.section_title("Section 1: Mode and Timestamp")
    pdf.code_block(
        "=== CURRENT MODE: SHORT TERM (1-WEEK HORIZON) ===\n"
        "Date: 2026-10-05 15:30:00 ET"
    )
    pdf.section_title("Section 2: Portfolio and Pricing (per ticker)")
    pdf.table_header([("Field", 70), ("Description", 120)])
    dossier_fields = [
        ("Shares Owned", "From trades.csv ledger"),
        ("Avg Purchase Price (ACB)", "Adjusted Cost Base computed from trade history"),
        ("Current Market Price", "Live price with multi-tier fallback (1d -> 5d -> ACB)"),
        ("Previous Close", "Prior day closing price"),
        ("Gap %", "Overnight gap: (Open - PrevClose) / PrevClose"),
        ("Open / High / Low", "Intraday OHLC from yfinance"),
        ("Intraday Trend %", "How far current price is above the Low of Day"),
        ("Unrealised P&L", "Dollar and % profit/loss on current position"),
        ("STOP-LOSS Alert", "Injected if price is > stop_loss_pct% below ACB"),
        ("Vol Ratio (10-day)", "Volume divided by 10-day average volume"),
        ("EMA Crossover", "Explicit BULLISH / BEARISH / NEUTRAL label (EMA5 vs EMA9)"),
        ("EMA (5-day)", "5-day Exponential Moving Average"),
        ("EMA (9-day)", "9-day Exponential Moving Average"),
        ("RSI (7-day)", "7-period Relative Strength Index"),
        ("ATR (5-day)", "Average True Range (5-period)"),
        ("Bollinger Lower/Mid/Upper", "20-period Bollinger Bands (2 std deviations)"),
    ]
    for i, (a, b) in enumerate(dossier_fields):
        pdf.table_row([(a, 70), (b, 120)], shade=(i % 2 == 1))
    pdf.ln(2)
    pdf.section_title("Section 3: Macro Commodities")
    pdf.body("Commodity symbols (CL=F, GC=F, HG=F) are displayed with current price and daily % change to align sector entries.")
    pdf.section_title("Section 4: Tripartite Macroeconomic News Briefing")
    pdf.bullet("Structured into Canada, USA, and World news pillars.")
    pdf.bullet("[NEW] (<=4h), [RECENT] (4-12h), [OLD] (12-48h) publication badges.")
    pdf.bullet("Category badges: [MACRO], [CENTRAL_BANK], [COMMODITY], [TRADE].")
    pdf.section_title("Section 5: Previous Advice History")
    pdf.body(
        "A rolling window of past AI analysis. The LLM receives up to the last 5 entries from "
        "today plus the final entry from the preceding 5 calendar days. Preserves cross-session continuity."
    )

    # CHAPTER 6: TRADING RULES
    pdf.add_page()
    pdf.chapter_title("6", "AI Trading Rules and Logic")
    pdf.body(
        "Trading rules are defined across system prompt templates in market_analyzer.py and "
        "persistent overrides in .agents/AGENTS.md. AGENTS.md rules take strict precedence."
    )
    pdf.section_title("6.1 Core Antigravity Execution Guidelines")
    rules = [
        ("Target Sell & Stop Loss on BUY", "Every BUY must provide a Target Sell Price (Mid-BB or +1.5 ATR target, whichever is > purchase price) and -5% Stop Loss."),
        ("Macro-Alignment Rule", "Before buying commodity-linked stocks (AEM, CNQ), the underlying commodity (GC=F, CL=F) MUST be green on the day."),
        ("Strict Overbought Filter", "If 7-day RSI > 75, NEVER BUY. If RSI is 65-75, only buy if Vol Ratio > 1.25x."),
        ("ADX Trend Filter", "BUY requires 14-day ADX > 20 unless Vol Ratio > 1.25x (volume surge exception)."),
        ("Low-Volume Scaled Entry", "Bullish EMA crossover with Vol Ratio <= 1.25x: allowed only with scaled position (25-50% allocation)."),
        ("Stagnation Exit", "Position held >4 trading days, negative, and flashes bearish EMA crossover: SELL immediately to recycle capital."),
        ("Profit Target Breakeven Flag", "If an open position gains >2.0% above purchase price, flag to user to raise Stop Loss to Breakeven."),
        ("Time-of-Day Filter", "Never initiate new BUY signals between 11:30 AM and 2:00 PM ET (lunch fake-out zone)."),
        ("Volume Capitulation", "Vol Ratio > 1.25x during a drop indicates panic selling exhausted; valid reversal signal."),
        ("Intraday Reversal Trigger", "Intraday drop >1.25% below open + RSI < 35 with immediate 2-interval rebound: allows speculative entry."),
    ]
    for title, desc in rules:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"  - {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_x(pdf.get_x() + 10)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(1)

    # CHAPTER 7: PROMPT SYSTEM
    pdf.add_page()
    pdf.chapter_title("7", "Trading Prompt System Instructions")
    pdf.body(
        "The AI formats responses concisely for mobile Telegram consumption, with dedicated "
        "scan and summary structures."
    )
    pdf.section_title("7.1 30-Minute Interval Scan Format")
    pdf.bullet("Unrealized P&L: Single summary line total at the top of the scan.")
    pdf.bullet("Portfolio Status: Quick bullet for each open position showing ACB, current price, and gain/loss.")
    pdf.bullet("Actionable Signals: BUY/SELL alerts with precise Target Price and Stop Loss calculations.")
    pdf.bullet("Position Sizing: Explicit labeling of Low-Volume Scaled Entries (25-50% allocation).")
    pdf.ln(2)
    pdf.section_title("7.2 End-of-Day (EOD) Summary Format")
    pdf.bullet("Total Unrealized P&L and Portfolio Equity.")
    pdf.bullet("Today's Realized Activity: Profit/loss from any closed trades.")
    pdf.bullet("Cumulative Performance: Active guidance realized P&L, trade count, and win rate.")
    pdf.bullet("Commodity & Macro Wrap: Gold, Crude Oil, and copper daily status.")
    pdf.bullet("Next-Day Watchlist: Actionable setups identified for the following morning's open.")

    # CHAPTER 8: SECURITY
    pdf.add_page()
    pdf.chapter_title("8", "Telegram Security Protocol")
    pdf.body(
        "Because the Telegram bot relays messages directly to the AI agent which has filesystem "
        "and command capabilities, a cryptographic PIN authentication protocol prevents remote code execution."
    )
    pdf.section_title("8.1 Remote Modification Challenges")
    pdf.bullet("Editing any Python (.py) source file.")
    pdf.bullet("Modifying .agents/AGENTS.md, config.json, or .env.")
    pdf.bullet("Running arbitrary shell, system, or PowerShell commands.")
    pdf.bullet("EXCLUSION: Appending or updating trades.csv for user trade logging is exempt.")
    pdf.ln(2)
    pdf.section_title("8.2 Challenge & Verification Workflow")
    pdf.code_block(
        "  [Telegram User asks for code/system change]\n"
        "         |\n"
        "         v\n"
        "  AI halts & writes PIN Challenge to Telegram\n"
        "  (includes TELEGRAM_PIN_HINT from .env)\n"
        "         |\n"
        "         v\n"
        "  [User replies with 8-digit PIN]\n"
        "         |\n"
        "         v\n"
        "  AI verifies against TELEGRAM_PIN in .env\n"
        "  Match: Executes change  |  Mismatch: Rejects request"
    )
    pdf.section_title("8.3 Local User Exception")
    pdf.body("Requests originating directly from the local Antigravity chat interface are fully authenticated and exempt from PIN challenges.")
    pdf.section_title("8.4 Environment Secrets (.env)")
    pdf.table_header([("Variable", 70), ("Description", 120)])
    env_rows = [
        ("TELEGRAM_BOT_TOKEN", "Bot authentication token issued by @BotFather."),
        ("TELEGRAM_CHAT_ID", "Authorized Telegram user ID. All unauthorized IDs are rejected."),
        ("TELEGRAM_PIN", "8-digit secret PIN required for remote code changes."),
        ("TELEGRAM_PIN_HINT", "Hint phrase displayed when requesting the PIN challenge."),
    ]
    for i, (a, b) in enumerate(env_rows):
        pdf.table_row([(a, 70), (b, 120)], shade=(i % 2 == 1))
    pdf.warn_box("NEVER commit .env to git. Always verify .gitignore contains .env.")

    # CHAPTER 9: SESSION RESTORE
    pdf.add_page()
    pdf.chapter_title("9", "Session Restore Procedure")
    pdf.body("When restarting or restoring an agent session, follow this streamlined procedure:")
    pdf.section_title("Step 1: Start Telegram Daemon")
    pdf.body("Run in the background via run_command:")
    pdf.code_block("C:\\Users\\Aamir\\miniforge3\\python.exe telegram_daemon.py")
    pdf.section_title("Step 2: Start File Watcher")
    pdf.body("Ensure file_watcher.py is active as a daemon process:")
    pdf.code_block("C:\\Users\\Aamir\\miniforge3\\python.exe file_watcher.py")
    pdf.section_title("Step 3: Setup Automated Cron Schedules")
    pdf.table_header([("Task", 55), ("Cron Expression", 60), ("Script Executed", 75)])
    cron = [
        ("30-min Market Scan", "*/30 9-16 * * 1-5", "send_interval_scan.py"),
        ("End-of-Day Summary", "5 16 * * 1-5", "send_eod_summary.py"),
    ]
    for i, (a, b, c) in enumerate(cron):
        pdf.table_row([(a, 55), (b, 60), (c, 75)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("Step 4: Operational Health Check")
    pdf.bullet("Run manage_task(Action='list') to verify daemons and schedules are running.")
    pdf.bullet("Send /status via Telegram to verify daemon connectivity and queue readiness.")

    # CHAPTER 10: LIMITATIONS
    pdf.add_page()
    pdf.chapter_title("10", "Known Limitations and Operational Notes")
    pdf.section_title("10.1 Market Data & API Fallbacks")
    pdf.bullet("yfinance TSX quotes have ~15-minute standard market delay.")
    pdf.bullet("Empty 1-day history frames at open are protected by automated 5-day and cost-basis fallbacks.")
    pdf.bullet("Intraday High/Low/Open reflect the current day's active bar.")
    pdf.section_title("10.2 Trade Ledger Integrity (trades.csv)")
    pdf.bullet("All trades are logged in chronological order.")
    pdf.bullet("Cash balance is derived from the latest row's Cash_Balance column.")
    pdf.bullet("Adjusted Cost Base (ACB) is rolled forward cumulatively across all buy/sell transactions.")
    pdf.section_title("10.3 Background Daemons")
    pdf.bullet("file_watcher.py runs continuously to bridge queue changes.")
    pdf.bullet("telegram_daemon.py processes incoming user instructions and flushes outgoing responses.")
    pdf.bullet("Long Telegram messages are automatically chunked at 4,000 characters to comply with API limits.")

    pdf.divider()
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(150, 155, 170)
    pdf.multi_cell(0, 5,
        f"Auto-generated by generate_pdf.py on {GENERATED}.\n"
        f"TSX Trading Advisor v{VERSION}  |  For operator use only.")
    pdf.set_text_color(0, 0, 0)

    pdf.output("TSX_Assistant_Guide_Final.pdf")
    print("PDF generated successfully: TSX_Assistant_Guide_Final.pdf")


if __name__ == "__main__":
    create_pdf()
