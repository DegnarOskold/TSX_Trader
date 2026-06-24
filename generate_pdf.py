from fpdf import FPDF
from fpdf.enums import XPos, YPos
import datetime

VERSION = "1.0.1"
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
        "portfolio, fetches live market data and news, and delivers scheduled AI-generated "
        "BUY/SELL/HOLD recommendations via Telegram.\n\n"
        "The system runs entirely locally on a Windows machine using Python. There are no cloud "
        "services, no subscription fees, and no external AI API keys. All AI reasoning is performed "
        "natively by the Antigravity agent session."
    )
    pdf.section_title("Key Characteristics")
    pdf.bullet("Horizon: SHORT TERM (1-week momentum and mean-reversion)")
    pdf.bullet("Data: Live prices, technical indicators, and news fetched every 30 minutes")
    pdf.bullet("Delivery: Telegram Bot messages to the operator's phone")
    pdf.bullet("Control: Operator logs trades via natural language text messages to the bot")
    pdf.bullet("Portfolio: Configurable tickers in config.json")
    pdf.bullet("Scheduling: 30-minute scans (10:00 AM - 3:30 PM ET) + EOD summary (4:05 PM ET)")
    pdf.ln(2)
    pdf.section_title("What the System Does NOT Do")
    pdf.bullet("It does NOT execute trades automatically. All trades must be placed manually.")
    pdf.bullet("It does NOT access broker APIs or brokerage accounts.")
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
        "an AI Reasoning Layer, and a Telegram Delivery Layer. These communicate via local "
        "JSONL queue files, creating a clean, fault-tolerant bridge."
    )
    pdf.code_block(
        "  [Telegram User]\n"
        "       |\n"
        "       v  (sends message)\n"
        "  [telegram_daemon.py]  <--- Runs 24/7 via start_daemon.bat\n"
        "       |\n"
        "       v  (writes to)\n"
        "  [incoming_queue.jsonl]\n"
        "       |\n"
        "       v  (monitored by)\n"
        "  [file_watcher.py]  <--- Background process, loops continuously\n"
        "       |\n"
        "       v  (prints NEW_MESSAGE to stdout, wakes)\n"
        "  [Antigravity Agent]  <--- The AI brain\n"
        "       |\n"
        "       +--> runs market_analyzer.generate_dossier()\n"
        "       +--> reasons natively, writes analysis\n"
        "       |\n"
        "       v  (writes to)\n"
        "  [outgoing_queue.jsonl]\n"
        "       |\n"
        "       v  (polled every 2s by)\n"
        "  [telegram_daemon.py]  ---> [Telegram User]\n"
        "                         +-> log_advice(advice_history.txt)"
    )
    pdf.section_title("2.2 Scheduled Analysis Flow")
    pdf.table_header([("Task", 55), ("Cron Expression", 65), ("Description", 70)])
    sched = [
        ("30-min Market Scan", "0,30 10-15 * * 1-5", "Full dossier + BUY/SELL/HOLD"),
        ("End-of-Day Summary", "5 16 * * 1-5", "Portfolio recap + next-day outlook"),
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
        ("market_analyzer.py", "Core data engine: prices, indicators, dossier, advice history, prompt templates"),
        ("telegram_daemon.py", "Telegram bot relay: receives messages, polls queue, sends responses, logs all advice"),
        ("file_watcher.py", "Queue bridge: loops continuously, watches incoming_queue.jsonl, wakes agent on new messages"),
        ("generate_pdf.py", "Documentation generator: produces this PDF from source"),
        ("quiet_watchdog.py", "Optional: monitors file_watcher.py process and restarts it if it crashes (checks every 10 min)"),
    ]
    for i, (a, b) in enumerate(files):
        pdf.table_row([(a, 58), (b, 132)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("3.2 Configuration and Data Files")
    pdf.table_header([("File", 58), ("Purpose", 132)])
    configs = [
        ("config.json", "Portfolio tickers, news search terms, operating mode (SHORT/MEDIUM), stop-loss %"),
        ("trades.csv", "Trade ledger: BUY/SELL history, Adjusted Cost Base, running cash balance"),
        ("advice_history.txt", "Rolling log of all AI advice sent to Telegram"),
        (".env", "Secrets: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_PIN, TELEGRAM_PIN_HINT"),
        (".gitignore", "Excludes .env, *.lock, __pycache__, queue files from git"),
        ("requirements.txt", "Python dependencies for pip installation (includes psutil)"),
        ("start_daemon.bat", "Windows launcher: double-click to start telegram_daemon.py"),
        ("AGENT_RESTORE_INSTRUCTIONS.md", "Step-by-step AI session restore guide"),
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
    pdf.note_box("Queue files are ephemeral and not committed to git. Created automatically at runtime.")

    # CHAPTER 4: CONFIG.JSON
    pdf.add_page()
    pdf.chapter_title("4", "Configuration Reference (config.json)")
    pdf.body("config.json is the single control plane for the system.")
    pdf.code_block(
        "{\n"
        "  \"mode\": \"SHORT\",\n"
        "  \"stop_loss_pct\": 5.0,\n"
        "  \"portfolio\": {\n"
        "    \"CNQ.TO\": [\n"
        "      \"CNQ.TO\",\n"
        "      \"CL=F\",\n"
        "      \"canadian+oil+sector\",\n"
        "      \"OPEC+oil+production\"\n"
        "    ],\n"
        "    \"CLS.TO\": [\n"
        "      \"CLS.TO\",\n"
        "      \"Celestica+electronics\",\n"
        "      \"electronics+manufacturing+services\",\n"
        "      \"supply+chain+hardware\"\n"
        "    ]\n"
        "  }\n"
        "}"
    )
    pdf.section_title("Fields")
    pdf.table_header([("Field", 50), ("Type", 30), ("Description", 110)])
    flds = [
        ("mode", "string", "\"SHORT\" (1-week momentum) or \"MEDIUM\" (2-4 week swing). Controls indicators used."),
        ("stop_loss_pct", "float", "If a position drops this % below ACB, a mandatory SELL directive is injected into the dossier."),
        ("portfolio", "object", "Keys are ticker symbols. Values are arrays of news search topics."),
    ]
    for i, (a, b, c) in enumerate(flds):
        pdf.table_row([(a, 50), (b, 30), (c, 110)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("Portfolio News Topics (per-ticker array)")
    pdf.body(
        "Each entry in the array can be:\n"
        "  - A ticker symbol (e.g. \"CNQ.TO\") - fetched from Yahoo Finance RSS\n"
        "  - A commodity symbol (e.g. \"CL=F\") - used as a macro price tracker\n"
        "  - A plain-text search term (e.g. \"canadian+oil+sector\") - searched on Google News"
    )
    pdf.warn_box(
        "Use full company names for Google News terms, not bare tickers. "
        "\"Canadian+Pacific+Kansas+City\" returns far more relevant results than \"CP\"."
    )

    # CHAPTER 5: DOSSIER STRUCTURE
    pdf.add_page()
    pdf.chapter_title("5", "Market Dossier Structure")
    pdf.body(
        "The dossier is a structured plain-text document generated by market_analyzer.generate_dossier() "
        "on every scheduled scan or manual analysis request. It contains five sections."
    )
    pdf.section_title("Section 1: Mode and Timestamp")
    pdf.code_block(
        "=== CURRENT MODE: SHORT TERM (1-WEEK HORIZON) ===\n"
        "Date: 2026-06-23 14:30:01 ET"
    )
    pdf.section_title("Section 2: Portfolio and Pricing (per ticker)")
    pdf.table_header([("Field", 70), ("Description", 120)])
    dossier_fields = [
        ("Shares Owned", "From trades.csv ledger"),
        ("Avg Purchase Price (ACB)", "Adjusted Cost Base computed from trade history"),
        ("Current Market Price", "Live price from yfinance"),
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
    pdf.note_box("In MEDIUM mode: RSI (14-day), SMA (50-day), BB (50-period), Ex-Dividend Date are used instead.")
    pdf.section_title("Section 3: Macro Commodities")
    pdf.body("Commodity symbols (e.g. CL=F, GC=F) are shown as a standalone macro context with current price and daily % change vs open.")
    pdf.section_title("Section 4: Qualitative News (up to 10 headlines per topic)")
    pdf.bullet("[NEW] = published within the last 4 hours")
    pdf.bullet("[RECENT] = published 4-12 hours ago")
    pdf.bullet("[OLD] = published 12-48 hours ago")
    pdf.bullet("[MACRO], [EARNINGS], [ANALYST], or [NEWS] category label")
    pdf.bullet("200-character summary from the RSS description field")
    pdf.section_title("Section 5: Previous Advice History")
    pdf.body(
        "A rolling window of past AI analysis. The LLM receives up to the last 5 entries from "
        "today plus the final entry from the preceding 5 calendar days. Weekends are NOT filtered."
    )

    # CHAPTER 6: TRADING RULES
    pdf.add_page()
    pdf.chapter_title("6", "AI Trading Rules and Logic")
    pdf.body(
        "Trading rules live in two locations: system prompt instructions in "
        "market_analyzer.get_analysis_prompt() and persistent override rules in .agents/AGENTS.md. "
        "AGENTS.md takes precedence."
    )
    pdf.section_title("6.1 System Prompt Rules (SHORT mode)")
    rules = [
        ("1. No Falling Knives", "EMA5 < EMA9 means a downtrend is active. Do not assume snap-back. Wait for crossover or volume shock before BUY."),
        ("2. Volume Capitulation", "Vol_Ratio > 1.25 during a drop = panic selling exhausted. Bullish reversal signal."),
        ("3. Market Open Rule", "Before 9:30 AM ET, never recommend buying. Wait 30 minutes for HFT volatility to settle."),
        ("4. Buy the Rumour", "Anticipate macro events within 24-48h. Override oversold technicals with HOLD/SELL if event removes a market premium."),
        ("5. Cash Constraint", "Check Available Free Cash before every BUY. No cash = no BUY."),
        ("6. Tranching", "Deploy free cash in tranches (e.g. 25%) instead of all at once."),
        ("7. Stop-Loss Enforcement", "Position > stop_loss_pct% below ACB = MUST SELL, regardless of RSI."),
        ("8. Profit-Taking", "Position touches Upper Bollinger Band AND RSI > 70 = trim position."),
        ("9. Zero-Share Rule", "0 shares + no BUY = AVOID or IGNORE (not HOLD)."),
        ("10. Acknowledge Failures", "If previous advice was wrong, explicitly say so. Do not repeat a failed thesis."),
        ("11. Macro Override", "RSI < 25 + top-tier macro catalyst = Speculative Macro Entry allowed (small position)."),
    ]
    for title, desc in rules:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"  Rule {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_x(pdf.get_x() + 10)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(1)

    pdf.section_title("6.2 AGENTS.md Persistent Override Rules")
    agent_rules = [
        ("Target Sell Price on BUY", "Every BUY must include a Target Sell Price (Upper BB or ATR-based) and Stop Loss Price for the broker."),
        ("Low-Volume Scaled Entry", "Bullish EMA crossover without high volume: recommend BUY at 25-50% position size, labeled 'Low-Volume Scaled Entry'."),
        ("Momentum Breakout Exception", "Bullish EMA crossover + RSI > 60 + green sector: Low-Volume Scaled Entry at 25% allocation still allowed."),
        ("Time-of-Day Filter", "Never initiate Low-Volume Scaled Entry between 11:00 AM and 2:00 PM ET."),
        ("Intraday Reversal Trigger", "Drop >1.25% below open + RSI < 35 + rebounds within two 30-min intervals: speculative Reversal Buy on partial position."),
    ]
    for title, desc in agent_rules:
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 6, f"  - {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("helvetica", "", 10)
        pdf.set_x(pdf.get_x() + 12)
        pdf.multi_cell(0, 5.5, desc)
        pdf.ln(1)

    # CHAPTER 7: PROMPT SYSTEM
    pdf.add_page()
    pdf.chapter_title("7", "Trading Prompt System Instructions")
    pdf.body(
        "The AI receives one of two prompt templates selected by config.json mode. "
        "Both embed the full dossier and all system rules inline."
    )
    pdf.section_title("7.1 SHORT Mode Output Format")
    pdf.bullet("Brief introduction (1 sentence)")
    pdf.bullet("Prioritised action list: e.g. '1. SELL CNQ.TO, 2. BUY ABX.TO' or 'No immediate actions recommended'")
    pdf.bullet("Detailed breakdown ONLY for action stocks (max 3 sentences per stock, must include current price)")
    pdf.ln(2)
    pdf.section_title("7.2 EOD Summary Output Format")
    pdf.bullet("End-of-Day Market Summary (1-2 sentences)")
    pdf.bullet("Portfolio Performance: status of all held assets (ignore 0-share positions)")
    pdf.bullet("Outlook Ahead: 2-3 sentences on tomorrow based on price action, volume, and macro news")
    pdf.note_box("The EOD prompt explicitly instructs the AI NOT to recommend new trades.")

    # CHAPTER 8: SECURITY
    pdf.add_page()
    pdf.chapter_title("8", "Telegram Security Protocol")
    pdf.body(
        "Because the Telegram bot relays messages directly to the AI agent which can run commands "
        "and edit files, a PIN challenge protocol is enforced to prevent unauthorized remote code execution."
    )
    pdf.section_title("8.1 Triggers Requiring PIN Verification")
    pdf.bullet("Editing any .py source file")
    pdf.bullet("Editing .agents/AGENTS.md or .env")
    pdf.bullet("Running arbitrary system or PowerShell commands")
    pdf.bullet("Any action modifying the codebase or host system")
    pdf.ln(2)
    pdf.section_title("8.2 PIN Challenge Flow")
    pdf.code_block(
        "  [Telegram: code change request]\n"
        "         |\n"
        "         v\n"
        "  AI writes PIN challenge to outgoing_queue.jsonl\n"
        "  (includes TELEGRAM_PIN_HINT from .env)\n"
        "         |\n"
        "         v\n"
        "  [User replies with 8-digit PIN]\n"
        "         |\n"
        "         v\n"
        "  AI validates against TELEGRAM_PIN in .env\n"
        "  Correct: proceed  |  Wrong: refuse and log"
    )
    pdf.section_title("8.3 Local User Exception")
    pdf.body("Requests from the local Antigravity interface (USER_REQUEST tags) are fully trusted. No PIN required.")
    pdf.section_title("8.4 Environment Variables")
    pdf.table_header([("Variable", 70), ("Description", 120)])
    env_rows = [
        ("TELEGRAM_BOT_TOKEN", "API token from @BotFather. Authenticates with the Telegram API."),
        ("TELEGRAM_CHAT_ID", "Numeric chat ID of the operator. All other chat IDs are rejected."),
        ("TELEGRAM_PIN", "8-digit PIN for remote code change authentication."),
        ("TELEGRAM_PIN_HINT", "Hint phrase sent to user when PIN challenge is issued."),
    ]
    for i, (a, b) in enumerate(env_rows):
        pdf.table_row([(a, 70), (b, 120)], shade=(i % 2 == 1))
    pdf.warn_box("NEVER commit .env to git. Listed in .gitignore. Back up your bot token and PIN securely.")

    # CHAPTER 9: SESSION RESTORE
    pdf.add_page()
    pdf.chapter_title("9", "Session Restore Procedure")
    pdf.body("If the Antigravity agent session is lost (reboot, context expiry), restore in this order:")
    pdf.section_title("Step 1: Start the Telegram Daemon (User Action)")
    pdf.body("Double-click start_daemon.bat, or run:")
    pdf.code_block("C:\\Users\\Aamir\\miniforge3\\python.exe telegram_daemon.py")
    pdf.section_title("Step 2: Start the File Watcher (Agent Action)")
    pdf.body("The agent starts file_watcher.py as a background task:")
    pdf.code_block("C:\\Users\\Aamir\\miniforge3\\python.exe file_watcher.py")
    pdf.note_box("file_watcher.py now runs in a continuous loop and does NOT exit after one message (fixed in v1.0.1).")
    pdf.section_title("Step 3: Recreate Cron Schedules (Agent Action)")
    pdf.table_header([("Task", 55), ("CronExpression", 60), ("Prompt Summary", 75)])
    cron = [
        ("30-min Market Scan", "0,30 10-15 * * 1-5", "[30-min Scan] Dossier + analysis -> outgoing_queue.jsonl"),
        ("EOD Summary", "5 16 * * 1-5", "[EOD Summary] Dossier + EOD summary -> outgoing_queue.jsonl"),
    ]
    for i, (a, b, c) in enumerate(cron):
        pdf.table_row([(a, 55), (b, 60), (c, 75)], shade=(i % 2 == 1))
    pdf.ln(3)
    pdf.section_title("Step 4: Verify")
    pdf.bullet("Send 'Analyze' via Telegram - agent should respond within 30 seconds")
    pdf.bullet("Send '/status' via Telegram - daemon replies with uptime and queue sizes")
    pdf.bullet("Check advice_history.txt is being updated after each analysis")

    # CHAPTER 10: LIMITATIONS
    pdf.add_page()
    pdf.chapter_title("10", "Known Limitations and Operational Notes")
    pdf.section_title("10.1 Market Data")
    pdf.bullet("yfinance prices are delayed approximately 15 minutes for TSX equities.")
    pdf.bullet("EMA, RSI, ATR indicators lag by one bar (prior day's close). The live price is current but indicators are historical.")
    pdf.bullet("Intraday High/Low/Open reflect the current trading day only.")
    pdf.section_title("10.2 News Quality")
    pdf.bullet("Google News RSS is keyword-based. Use specific company names to minimize irrelevant results.")
    pdf.bullet("Yahoo Finance RSS is limited to the ticker's own headlines.")
    pdf.bullet("News older than 48 hours is automatically filtered.")
    pdf.section_title("10.3 Advice History")
    pdf.bullet("LLM context window receives last 5 entries from today + final entry from prior 5 calendar days.")
    pdf.bullet("Weekends are NOT filtered (fixed in v1.0.1). Friday advice is preserved into Monday.")
    pdf.bullet("advice_history.txt retains full history for human audit.")
    pdf.section_title("10.4 Operational Constraints")
    pdf.bullet("System requires the Antigravity agent session to be active during market hours.")
    pdf.bullet("If the session is lost, incoming_queue.jsonl will accumulate unprocessed messages until restored.")
    pdf.bullet("quiet_watchdog.py monitors file_watcher.py only - does NOT monitor the daemon or AI session.")
    pdf.bullet("Very long AI responses are automatically chunked at 4,000 characters per Telegram message.")
    pdf.section_title("10.5 Trade Logging")
    pdf.bullet("All trades are logged manually via natural language Telegram messages.")
    pdf.bullet("Cash balance is always read from the Cash_Balance column of the LAST row in trades.csv.")
    pdf.bullet("ACB is computed by rolling forward every row in trades.csv from the beginning.")
    pdf.bullet("Do not insert rows in the middle of trades.csv - this will corrupt the cash balance.")

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
