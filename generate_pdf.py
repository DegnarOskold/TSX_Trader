from fpdf import FPDF
from fpdf.enums import XPos, YPos

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 10)
        self.set_fill_color(30, 30, 40)
        self.set_text_color(200, 200, 200)
        self.cell(0, 8, 'TSX Trading Advisor - Technical Reference Manual', fill=True, align='C',
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f'Page {self.page_no()}  |  TSX Trading Advisor  |  Confidential', align='C')
        self.set_text_color(0, 0, 0)

    def chapter_title(self, title):
        self.set_font('helvetica', 'B', 14)
        self.set_fill_color(30, 30, 40)
        self.set_text_color(255, 255, 255)
        self.cell(0, 9, title, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def section_title(self, title):
        self.set_font('helvetica', 'B', 11)
        self.set_text_color(30, 80, 150)
        self.cell(0, 7, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body(self, text):
        self.set_font('helvetica', '', 10)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_block(self, code):
        self.set_font('courier', '', 9)
        self.set_fill_color(240, 240, 245)
        self.set_draw_color(180, 180, 200)
        self.multi_cell(0, 5, code, fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)
        self.ln(3)

    def table_row(self, col1, col2, col3='', header=False):
        self.set_font('helvetica', 'B' if header else '', 9)
        if header:
            self.set_fill_color(60, 60, 80)
            self.set_text_color(255, 255, 255)
            fill = True
        else:
            self.set_fill_color(248, 248, 252)
            self.set_text_color(0, 0, 0)
            fill = True
        w1 = 50
        w2 = 70
        w3 = 0 if not col3 else 70
        if col3:
            self.cell(w1, 6, col1, border=1, fill=fill)
            self.cell(w2, 6, col2, border=1, fill=fill)
            self.cell(w3, 6, col3, border=1, fill=fill, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.cell(w1, 6, col1, border=1, fill=fill)
            self.cell(0, 6, col2, border=1, fill=fill, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.set_fill_color(255, 255, 255)

    def bullet(self, text, indent=5):
        self.set_font('helvetica', '', 10)
        self.set_x(self.get_x() + indent)
        self.multi_cell(0, 5.5, f'  -  {text}')
        self.ln(0.5)


def create_pdf():
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # ============================================================
    # COVER PAGE
    # ============================================================
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('helvetica', 'B', 28)
    pdf.set_text_color(30, 30, 40)
    pdf.cell(0, 14, 'TSX Trading Advisor', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font('helvetica', '', 16)
    pdf.set_text_color(80, 80, 100)
    pdf.cell(0, 10, 'Technical Reference Manual', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)
    pdf.set_font('helvetica', 'I', 11)
    pdf.set_text_color(130, 130, 150)
    pdf.cell(0, 8, 'Architecture, Configuration, Data Flow, and AI Logic', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(20)

    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(100, 100, 120)
    pdf.set_fill_color(245, 245, 252)
    pdf.cell(0, 8, 'Classification: Confidential  |  Environment: Production  |  Platform: Windows / Python 3',
             align='C', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(25)

    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(30, 30, 40)
    pdf.cell(0, 7, 'Table of Contents', new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
    pdf.ln(3)

    toc = [
        ('1.', 'System Architecture Overview'),
        ('2.', 'File Structure & Roles'),
        ('3.', 'Configuration Reference  (config.json / .env)'),
        ('4.', 'Data Engine  (market_analyzer.py)'),
        ('5.', 'Technical Indicator Reference'),
        ('6.', 'AI Prompt System & Trading Rules'),
        ('7.', 'Telegram Daemon  (telegram_daemon.py)'),
        ('8.', 'Scheduled Cron Jobs & Automated Tasks'),
        ('9.', 'Trade Ledger  (trades.csv)'),
        ('10.', 'Advice History System  (advice_history.txt)'),
        ('11.', 'Dependency Reference  (requirements.txt)'),
        ('12.', 'Security Hardening'),
        ('13.', 'Operational Runbook'),
        ('14.', 'Troubleshooting Guide'),
    ]
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(40, 40, 60)
    for num, title in toc:
        pdf.cell(15, 6, num)
        pdf.cell(0, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ============================================================
    # PAGE 1: SYSTEM ARCHITECTURE OVERVIEW
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('1. System Architecture Overview')

    pdf.body(
        'The TSX Trading Advisor is a locally-running, fully automated stock analysis and portfolio management system. '
        'It is built entirely on free, open-source Python libraries and requires no paid brokerage API. It connects '
        'to Yahoo Finance for real-time market data and uses the Google Gemini Large Language Model (LLM) to synthesize '
        'quantitative and qualitative signals into plain-language trading recommendations delivered via Telegram.'
    )

    pdf.section_title('1.1 Core Execution Paths')
    pdf.body(
        'The system runs along two independent, concurrent execution paths:'
    )
    pdf.bullet('PATH A - Telegram Daemon (telegram_daemon.py): A long-running foreground process started manually '
               'via start_daemon.bat. It listens for Telegram messages, handles natural-language trade logging, '
               'mode switching, on-demand analysis (/analyze), and general Q&A.')
    pdf.bullet('PATH B - Scheduled Cron Agent (Antigravity Agent): An external AI agent (this same session) '
               'wakes up on a cron schedule (hourly, 3:30 PM, 4:05 PM ET on weekdays). It calls market_analyzer.py '
               'to build a live dossier, feeds it to Gemini, and sends the resulting recommendation via send_telegram.py.')
    pdf.ln(2)

    pdf.section_title('1.2 Data Flow Diagram')
    pdf.code_block(
        'config.json ----------------------------------------------------------+\n'
        'trades.csv  ----------------------------------------------------------+\n'
        '                                                                      |\n'
        '                                                             market_analyzer.py\n'
        '                                       +-----------------------------+\n'
        '                                       |  log_advice()               -> advice_history.txt (w/lock)\n'
        '                                       |  get_acb_and_balances()     -> ACB, cash, P&L, stop-loss flag\n'
        '                                       |  get_stock_data()           -> OHLC, price, indicators\n'
        '                                       |  get_compartmentalized_news()-> RSS headlines\n'
        '                                       |  get_cleaned_advice_history()-> rolling advice log (pruned)\n'
        '                                       |  generate_dossier()         -> assembled text blob\n'
        '                                       |  get_analysis_prompt()      -> prompt for LLM\n'
        '                                       |  get_eod_summary_prompt()   -> EOD prompt for LLM\n'
        '                                       +-------------+----------------+\n'
        '                                                     |\n'
        '                                    +----------------+------------------+\n'
        '                                    |                                   |\n'
        '                           telegram_daemon.py              run_scheduled_analysis.py\n'
        '                           (interactive/trades)            (scheduled cron tasks)\n'
        '                                    |                                   |\n'
        '                               Gemini API                         Gemini API\n'
        '                                    |                                   |\n'
        '                            Telegram reply                   send_telegram.py\n'
        '                                    |                                   |\n'
        '                                    +-----------+-----------------------+\n'
        '                                                |\n'
        '                                      log_advice() -> advice_history.txt (w/lock)'
    )

    pdf.section_title('1.3 Technology Stack')
    pdf.table_row('Component', 'Technology / Library', 'Version', header=True)
    pdf.table_row('Market Data', 'yfinance (Yahoo Finance)', '1.4.1')
    pdf.table_row('Technical Indicators', 'pandas-ta', '0.4.71b0')
    pdf.table_row('Data Frames', 'pandas', '3.0.1')
    pdf.table_row('AI Reasoning', 'Google Gemini 2.5 Flash (via google-genai)', '2.8.0')
    pdf.table_row('Telegram Messaging', 'python-telegram-bot', '22.8')
    pdf.table_row('Secrets Management', 'python-dotenv', '1.2.2')
    pdf.table_row('HTTP Requests', 'requests', 'latest')
    pdf.table_row('PDF Generation', 'fpdf2', '2.8.7')
    pdf.table_row('Runtime', 'Python (Miniforge)', '3.x')
    pdf.ln(3)

    # ============================================================
    # PAGE 2: FILE STRUCTURE
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('2. File Structure & Roles')

    pdf.table_row('File', 'Role', header=True)
    pdf.table_row('market_analyzer.py', 'Core data engine. Computes indicators, fetches news, builds dossier, and generates all LLM prompts. Also owns log_advice().')
    pdf.table_row('telegram_daemon.py', 'Long-running bot server. Handles all user interaction: trade logging, analysis, Q&A, mode switching, /help command.')
    pdf.table_row('run_scheduled_analysis.py', 'Standalone script invoked by cron tasks. Calls market_analyzer.py, sends result to Gemini, and delivers via send_telegram.py.')
    pdf.table_row('send_telegram.py', 'Standalone CLI utility. Sends a text string via Telegram Bot API. Used by run_scheduled_analysis.py.')
    pdf.table_row('generate_pdf.py', 'Generates this PDF documentation from source.')
    pdf.table_row('config.json', 'Runtime configuration. Controls active mode (SHORT/MEDIUM), portfolio-to-news-topic mapping, and stop_loss_pct.')
    pdf.table_row('trades.csv', 'Source of truth for all holdings. Records every trade; used to calculate ACB and cash balance.')
    pdf.table_row('advice_history.txt', 'Rolling log of AI-generated advice. Injected into every new dossier for context continuity.')
    pdf.table_row('.env', 'Secrets file. Contains TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and GEMINI_API_KEY.')
    pdf.table_row('.gitignore', 'Excludes .env, trades.csv, advice_history.txt, and *.lock files from version control.')
    pdf.table_row('start_daemon.bat', 'Windows batch file to launch telegram_daemon.py from the correct working directory.')
    pdf.table_row('requirements.txt', 'Pinned Python dependency list for reproducible installs.')
    pdf.table_row('AGENT_RESTORE_INSTRUCTIONS.md', 'Instructions for an AI agent to restore the system if the session is lost.')
    pdf.table_row('test_llm.py', 'Manual test script for validating the Gemini trade-extraction prompt against live dynamic tickers.')
    pdf.ln(3)

    # ============================================================
    # PAGE 3: CONFIGURATION REFERENCE
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('3. Configuration Reference')

    pdf.section_title('3.1  config.json')
    pdf.body(
        'This file controls the operating mode and portfolio composition. It is read at runtime by market_analyzer.py '
        'on every dossier generation. The user can modify the mode via Telegram by sending "Short Term Mode" or "Medium Term Mode".'
    )
    pdf.code_block(
        '{\n'
        '    "mode": "SHORT",           // "SHORT" or "MEDIUM"\n'
        '    "portfolio": {\n'
        '        "CNQ.TO": ["CNQ.TO", "CL=F"],   // Ticker -> list of RSS news topics\n'
        '        "ABX.TO": ["ABX.TO", "GC=F"]    // Ticker -> list of RSS news topics\n'
        '    },\n'
        '    "stop_loss_pct": 5.0       // % drop below ACB that triggers a mandatory SELL directive\n'
        '}'
    )
    pdf.bullet('"mode": Controls which technical indicators are computed and which AI system instructions are used.')
    pdf.bullet('"portfolio": Keys are TSX ticker symbols. Values are lists of Yahoo Finance RSS symbols '
               'whose headlines will be fetched as qualitative context for each holding. Ticker symbols '
               'listed as values that are NOT in the portfolio keys are treated as Macro Commodity trackers '
               '(e.g. CL=F, GC=F) and have their live price/daily change injected into the dossier.')
    pdf.bullet('"stop_loss_pct": The maximum acceptable loss percentage before the system injects a hard '
               'STOP-LOSS TRIGGERED directive into the dossier. Default is 5.0%.')
    pdf.bullet('To add a new stock, add a new key-value pair to "portfolio". The system will automatically '
               'fetch data and news for it on the next run. No code changes required.')
    pdf.ln(3)

    pdf.section_title('3.2  .env  (Secrets)')
    pdf.body(
        'All credentials are stored in a .env file in the project root. This file is excluded from version control '
        'by .gitignore. Never commit this file.'
    )
    pdf.code_block(
        'TELEGRAM_BOT_TOKEN=xxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\n'
        'TELEGRAM_CHAT_ID=xxxxxxxxx    # Used by BOTH send_telegram.py AND telegram_daemon.py\n'
        'GEMINI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    )
    pdf.bullet('TELEGRAM_BOT_TOKEN: BotFather API token. Required by both the daemon and send_telegram.py.')
    pdf.bullet('TELEGRAM_CHAT_ID: Your numeric Telegram chat ID. Used by send_telegram.py to push outbound messages, '
               'and by telegram_daemon.py to authorize inbound messages. A single key serves both purposes.')
    pdf.bullet('GEMINI_API_KEY: Google AI Studio API key for the Gemini 2.5 Flash model.')
    pdf.ln(3)

    pdf.section_title('3.3  Changing Operating Mode')
    pdf.body(
        'Mode can be changed at runtime without restarting the daemon by sending a message to the Telegram bot.'
    )
    pdf.code_block(
        'User sends:  "change mode"\n'
        'Bot replies: "Please reply with Short Term Mode or Medium Term Mode"\n'
        'User sends:  "Short Term Mode"\n'
        'Bot replies: "Operating mode successfully updated to: SHORT TERM"'
    )

    # ============================================================
    # PAGE 4: DATA ENGINE
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('4. Data Engine (market_analyzer.py)')

    pdf.body(
        'market_analyzer.py is the central data and prompt generation engine. All other components '
        'import from it. It now loads config.json exactly ONCE per generate_dossier() call and passes '
        'the parsed config object to all sub-functions, eliminating any risk of a mid-generation '
        'config race condition.'
    )

    pdf.section_title('4.1  Function Reference')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'log_advice(text)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Centralized writer for advice_history.txt. Acquires a filesystem lockfile (advice.lock) before '
             'writing, retrying up to 50 times (5s total) if the lock is already held by another process. '
             'Releases the lock in a finally block. Used by both send_telegram.py and telegram_daemon.py.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_current_mode(config=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Returns "SHORT" or "MEDIUM". Accepts an optional pre-loaded config dict to avoid a redundant file read. Falls back to reading config.json directly if no config is passed.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_tickers(config=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Returns a list of ticker symbols from the portfolio keys. Accepts an optional pre-loaded config dict. '
             'Falls back to ["CNQ.TO", "ABX.TO"] if the file is absent.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_stop_loss_pct(config=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Returns the stop_loss_pct value from config.json (default 5.0). Accepts an optional pre-loaded config dict.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_acb_and_balances()', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Reads trades.csv row by row and computes: (1) Adjusted Cost Base (ACB) per ticker. '
        '(2) Available Cash from the last Cash_Balance column value. '
        'Malformed rows with non-numeric values are silently skipped via try/except ValueError. '
        'Returns: {"positions": {"CNQ.TO": {"shares": 100.0, "total_cost": 6012.0, "acb": 60.12}}, "cash": 5230.00}'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_stock_data(ticker_symbol, mode)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Fetches 6 months of OHLCV history via yfinance (timeout=10s). Now returns Open, High, and Low '
        'in addition to Close, for all modes. Computes technical indicators via pandas-ta. '
        'Wraps everything in try/except; returns an error string if the ticker is invalid.'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_compartmentalized_news(config=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Reads portfolio from config (or config.json directly), builds a unique list of RSS topic symbols, then fetches '
        'the 10 most recent Yahoo Finance RSS headlines for each topic (timeout=10s). '
        'This is the Qualitative Analysis section of the dossier.'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_cleaned_advice_history()', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Reads advice_history.txt, parses entries by [YYYY-MM-DD HH:MM:SS] timestamp headers, and applies '
        'two separate policies: (1) PHYSICAL FILE: Rewrites the file retaining ALL entries for today + the '
        'last entry for each of the last 5 business days. Weekend entries are silently discarded. '
        '(2) LLM CONTEXT STRING: Returns only the LAST 5 entries from today + the last entry from each '
        'prior day. This keeps the LLM prompt token-efficient while the local log remains complete.'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'generate_dossier()', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'The main assembler. Loads config.json once, then calls all sub-functions passing the config object. '
        'New sections added in v2: Unrealised P&L per holding, deterministic STOP-LOSS TRIGGERED directives, '
        'Today Open/High/Low per ticker, and a Macro Commodities section with live price and daily change '
        'for non-portfolio symbols (e.g. CL=F, GC=F) found in the portfolio news mapping.'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_analysis_prompt(dossier=None, mode=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Wraps the dossier in the appropriate system instructions and output format rules for either SHORT '
        'or MEDIUM mode. Used by both the Telegram daemon (for /analyze and Q&A) and run_scheduled_analysis.py '
        '(for scheduled hourly and 3:30 PM recommendations).'
    )

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'get_eod_summary_prompt(dossier=None)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body(
        'Wraps the dossier in special end-of-day instructions that suppress active trading advice '
        'and instead request a narrative summary of portfolio performance and next-day outlook. '
        'Used exclusively by the 4:05 PM cron task.'
    )

    # ============================================================
    # PAGE 5: TECHNICAL INDICATOR REFERENCE
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('5. Technical Indicator Reference')

    pdf.section_title('5.1  SHORT Mode Indicators  (mode = "SHORT")')
    pdf.body('Designed for a 5-to-7 day momentum trading horizon. Optimized for mean-reversion signals.')

    pdf.table_row('Indicator', 'Parameters', 'Interpretation', header=True)
    pdf.table_row('EMA (Exponential Moving Average)', '5-day, 9-day', 'Short-term momentum direction. EMA_5 crossing above EMA_9 is bullish.')
    pdf.table_row('RSI (Relative Strength Index)', '7-day', 'Overbought >70, Oversold <30. Faster than standard 14-day for short-term.')
    pdf.table_row('ATR (Average True Range)', '5-day', 'Measures raw volatility. Used to set stop-loss distances.')
    pdf.table_row('Bollinger Bands', '20-day, 2 std devs', 'Price below BB_Lower = oversold/compressed. Price above BB_Upper = overbought.')
    pdf.table_row('Vol_Ratio', '10-day rolling avg', 'Volume / 10-day average. >2.0 during a drop signals capitulation (exhausted sellers).')
    pdf.ln(3)

    pdf.section_title('5.2  MEDIUM Mode Indicators  (mode = "MEDIUM")')
    pdf.body('Designed for a 2-to-4 week swing trading horizon. Emphasizes mean price and income events.')

    pdf.table_row('Indicator', 'Parameters', 'Interpretation', header=True)
    pdf.table_row('RSI (Relative Strength Index)', '14-day', 'Standard 14-day RSI. Overbought >70, Oversold <30.')
    pdf.table_row('SMA (Simple Moving Average)', '50-day', 'Key support/resistance level. Price above SMA_50 is structurally bullish.')
    pdf.table_row('Bollinger Bands (Upper)', '50-day, 2 std devs', 'Profit-taking trigger. AI instructed to recommend trimming when price touches BB_Upper and RSI > 70.')
    pdf.table_row('Ex-Dividend Date', 'from ticker.info', 'Upcoming ex-div dates affect entry timing. Holding before ex-date captures the dividend.')
    pdf.ln(3)

    pdf.section_title('5.3  ACB (Adjusted Cost Base) Calculation')
    pdf.body(
        'The system computes ACB from scratch on every run using a pure roll-forward method over trades.csv. '
        'It does NOT rely on the stored Shares_Balance or Cash_Balance columns for ACB computation (only cash '
        'reads from the column, for simplicity). The ACB formula:'
    )
    pdf.code_block(
        'On BUY or INIT:\n'
        '    shares += quantity\n'
        '    total_cost += quantity * price\n'
        '    acb = total_cost / shares\n'
        '\n'
        'On SELL:\n'
        '    total_cost -= quantity * acb  # Reduce cost at current ACB, not sell price\n'
        '    shares -= quantity\n'
        '    # If shares drop to 0, reset total_cost and acb to 0.0'
    )

    # ============================================================
    # PAGE 6: AI PROMPT SYSTEM
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('6. AI Prompt System & Trading Rules')

    pdf.body(
        'The AI prompt system is the decision-making core of the advisor. The system instructions embedded '
        'in the prompts constitute a formal rule set that the Gemini model must follow. These rules are '
        'different depending on the active mode.'
    )

    pdf.section_title('6.1  Dossier Structure (Input to LLM)')
    pdf.body('The dossier is a structured plain-text document assembled by generate_dossier(). It contains:')
    pdf.bullet('Section 1: Current Mode header (SHORT or MEDIUM)')
    pdf.bullet('Section 2: Date and timestamp')
    pdf.bullet('Section 3: Portfolio & Pricing -- shares owned, ACB, current price, Today Open/High/Low, '
               'Unrealised P&L, any STOP-LOSS TRIGGERED directives, and all technical indicators per ticker')
    pdf.bullet('Section 4: Macro Commodities -- live price and daily % change (vs Open) for commodity symbols '
               'configured as news topics (e.g. CL=F for oil, GC=F for gold)')
    pdf.bullet('Section 5: Qualitative Data -- 10 recent Yahoo Finance RSS headlines per configured news topic')
    pdf.bullet('Section 6: Previous Advice History -- last 5 entries from today + final entry from each of '
               'the last 5 business days (weekend entries discarded)')
    pdf.ln(2)

    pdf.section_title('6.2  SHORT Mode System Instructions (all 10 rules)')
    pdf.table_row('Rule #', 'Name', 'Description', header=True)
    pdf.table_row('1', 'Trend Validation (No Falling Knives)', 'Do not assume a snap-back rally if EMA_5 < EMA_9. Wait for volume shock or crossover.')
    pdf.table_row('2', 'Volume Shock / Capitulation', 'Vol_Ratio > 2.0 during a price drop = panic selling exhausted. Bullish reversal signal.')
    pdf.table_row('3', 'Market Open Volatility', 'Before 9:30 AM ET, do NOT recommend buying. Wait 30 mins for irrational gaps to settle.')
    pdf.table_row('4', 'Finalized Macro Events', 'If news confirms a deal is done, anticipate the asset moves inversely ("buy the rumour, sell the news").')
    pdf.table_row('5', 'Cash Constraint', 'If free cash < cost of purchase, BUY is strictly forbidden.')
    pdf.table_row('6', 'Position Sizing (Tranching)', 'Recommend buying in tranches (e.g., 25% of free cash) to mitigate intraday volatility.')
    pdf.table_row('7', 'Protective Stop-Loss for Holds', 'Explicitly recommend to SELL if price drops more than the configured stop_loss_pct (default 5%) below ACB.')
    pdf.table_row('8', 'Profit-Taking Mechanics', 'Price at BB_Upper AND RSI > 70 = recommend trimming position (e.g., sell 50%).')
    pdf.table_row('9', 'Zero-Share Holdings', 'If 0 shares owned and not recommending BUY, use AVOID or IGNORE, not HOLD.')
    pdf.table_row('10', 'Acknowledge Failed Theses', 'If previous predictions failed and the stock continues dropping, acknowledge this instead of blindly repeating the thesis.')
    pdf.ln(3)

    pdf.section_title('6.3  MEDIUM Mode System Instructions (6 rules)')
    pdf.body('Medium mode uses rules 5-10 from above (Cash Constraint, Tranching, Protective Stop-Loss, Profit-Taking, Zero-Share, Failed Theses). '
             'Rules 1-4 are omitted because Bollinger-based mean-reversion and volume shock are short-term signals '
             'not relevant to a multi-week swing trading thesis. The SMA_50 and RSI_14 take their place as primary indicators.')
    pdf.ln(2)

    pdf.section_title('6.4  AI Output Format')
    pdf.body('Both modes require the LLM to structure its response in exactly three sections:')
    pdf.bullet('Section 1: A brief 1-2 sentence introduction summarizing the market environment.')
    pdf.bullet('Section 2: A numbered list of priority actions (BUY, SELL, HOLD). AVOID and IGNORE are never listed here.')
    pdf.bullet('Section 3: Stock-specific analysis for actioned stocks only. Maximum 3 sentences per stock. '
               'Indicators integrated naturally into prose (not as bullet points).')
    pdf.ln(2)

    pdf.section_title('6.5  EOD Summary Prompt (4:05 PM Only)')
    pdf.body(
        'get_eod_summary_prompt() uses a different instruction set that suppresses active trading advice. '
        'The AI is instructed to produce a 3-section response: (1) End-of-Day market summary, '
        '(2) Portfolio performance for currently held positions only, (3) 2-3 sentence outlook for tomorrow '
        'based on today\'s price action, volume, and breaking news.'
    )

    pdf.section_title('6.6  Two-Step Intent Detection (Q&A Optimization)')
    pdf.body(
        'When a user sends a free-form message to the Telegram bot (not "analyze" or a trade), the daemon '
        'runs a two-step process to avoid wasting tokens:'
    )
    pdf.bullet('Step 1 (Lightweight): A micro-prompt is sent to Gemini asking only whether the message is a '
               '"TRADE" or a "QUESTION". The prompt requests a JSON response. No dossier is included.')
    pdf.bullet('Step 2A (TRADE path): If intent = TRADE, the extracted JSON (action, ticker, quantity, price) '
               'is parsed and staged in memory as a pending_trade, awaiting YES/NO confirmation.')
    pdf.bullet('Step 2B (QUESTION path): If intent = QUESTION, the full dossier is generated, appended to a '
               'Q&A prompt, and sent to Gemini for a detailed response. This is the expensive path.')

    # ============================================================
    # PAGE 7: TELEGRAM DAEMON
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('7. Telegram Daemon (telegram_daemon.py)')

    pdf.body(
        'The Telegram daemon is a persistent Python process built on the python-telegram-bot library. '
        'It uses long-polling (not webhooks) to receive messages. It must be started manually and runs '
        'in the foreground.'
    )

    pdf.section_title('7.1  Message Routing Logic')
    pdf.body('Incoming messages are routed through the following priority-ordered decision tree:')
    pdf.code_block(
        'Incoming message\n'
        '   |\n'
        '   +-- Is chat_id authorized? (matches TELEGRAM_CHAT_ID in .env)\n'
        '   |       NO  -> Silently drop message (print to console only)\n'
        '   |      YES  -> Continue\n'
        '   |\n'
        '   +-- Is there a pending_trade for this chat_id AND message is "yes"/"no"?\n'
        '   |       YES -> Confirm or cancel staged trade -> update_ledger() -> done\n'
        '   |\n'
        '   +-- Message is "change mode"?\n'
        '   |       YES -> Ask user to specify Short or Medium term mode\n'
        '   |\n'
        '   +-- Message is "short term mode" or "medium term mode"?\n'
        '   |       YES -> Write new mode to config.json -> done\n'
        '   |\n'
        '   +-- Message is "analyze" or "analysis"?\n'
        '   |       YES -> get_analysis_prompt() -> Gemini -> send_chunked_reply() -> log_advice()\n'
        '   |\n'
        '   +-- Everything else -> Two-step intent extraction\n'
        '           TRADE intent    -> stage in pending_trades -> ask for confirmation\n'
        '           QUESTION intent -> generate_dossier() -> Gemini Q&A -> reply'
    )
    pdf.ln(2)

    pdf.section_title('7.1a  Available Commands')
    pdf.table_row('Command / Message', 'Response', header=True)
    pdf.table_row('/start', 'Welcome message with brief instructions.')
    pdf.table_row('/help', 'Full capability list: trade logging, analyze, change mode, Q&A.')
    pdf.table_row('analyze (or analysis)', 'Generates a full live market analysis with trading recommendations.')
    pdf.table_row('change mode', 'Prompts to switch between Short Term and Medium Term modes.')
    pdf.table_row('Short Term Mode', 'Sets mode to SHORT in config.json immediately.')
    pdf.table_row('Medium Term Mode', 'Sets mode to MEDIUM in config.json immediately.')
    pdf.table_row('Natural trade (e.g. I bought 100 CNQ at 61)', 'Two-step confirm-then-commit trade logging flow.')
    pdf.table_row('Any question', 'Generates a live-dossier-backed Q&A response from Gemini.')
    pdf.ln(2)

    pdf.section_title('7.2  Trade Logging Flow')
    pdf.body('Trades go through a two-phase confirm-then-commit process to prevent accidental ledger writes:')
    pdf.bullet('Phase 1 (Stage): Gemini extracts action, ticker, quantity, and price from the message. '
               'The trade dict is stored in the in-memory pending_trades{chat_id} dict.')
    pdf.bullet('Phase 2 (Commit): User replies YES. The daemon calls update_ledger(action, ticker, qty, price). '
               'This function calls get_acb_and_balances() for current state, validates cash/share sufficiency, '
               'and appends a new row to trades.csv.')
    pdf.bullet('Limitation: pending_trades is in-memory only. If the daemon restarts between Phase 1 and Phase 2, '
               'the staged trade is lost and must be re-entered.')
    pdf.ln(2)

    pdf.section_title('7.3  update_ledger() Function')
    pdf.body('This function writes new trade rows to trades.csv. It validates before writing:')
    pdf.bullet('BUY validation: if cash_bal < cost, raises ValueError("Insufficient cash!")')
    pdf.bullet('SELL validation: if current_shares < quantity, raises ValueError("Insufficient shares")')
    pdf.bullet('Appends a CSV row: [Date, Ticker, Action, Quantity, Price, Shares_Balance, Cash_Balance]')
    pdf.ln(2)

    pdf.section_title('7.4  Market Hours Warning')
    pdf.body(
        'When the user sends "analyze" outside of trading hours (9:30 AM to 4:00 PM ET, Mon-Fri), '
        'the response is prefixed with a warning: "The market is currently closed. This analysis is based '
        'on the last session\'s closing data." Note: the time check uses local system time and assumes '
        'the machine is in the ET timezone.'
    )

    pdf.section_title('7.5  Message Chunking')
    pdf.body(
        'Telegram enforces a hard 4096-character limit per message. The send_chunked_reply() async function '
        'splits any response into 4000-character chunks and sends them sequentially to avoid truncation.'
    )

    # ============================================================
    # PAGE 8: SCHEDULED CRON JOBS
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('8. Scheduled Cron Jobs & Automated Tasks')

    pdf.body(
        'The three scheduled tasks are managed by the Antigravity AI agent using its native schedule tool. '
        'Each task fires a cron-based wake-up that runs run_scheduled_analysis.py as a subprocess. '
        'That script directly calls market_analyzer.py, sends the dossier to the Gemini API, '
        'and delivers the response via send_telegram.py. This architecture was adopted to eliminate '
        'shell buffer truncation that previously caused the agent to hallucinate stale prices.'
    )

    pdf.section_title('8.1  Task 1: Hourly Market Scan')
    pdf.table_row('Parameter', 'Value', header=True)
    pdf.table_row('Cron Expression', '0 10-15 * * 1-5')
    pdf.table_row('Schedule', 'Every hour on the hour, 10 AM to 3 PM ET, Monday to Friday')
    pdf.table_row('Prompt Source', 'get_analysis_prompt() from market_analyzer.py')
    pdf.table_row('Output', 'SHORT or MEDIUM mode trading recommendation sent via Telegram')
    pdf.ln(3)

    pdf.section_title('8.2  Task 2: Pre-Close Market Scan (3:30 PM)')
    pdf.table_row('Parameter', 'Value', header=True)
    pdf.table_row('Cron Expression', '30 15 * * 1-5')
    pdf.table_row('Schedule', 'Every weekday at 3:30 PM ET')
    pdf.table_row('Prompt Source', 'get_analysis_prompt() from market_analyzer.py')
    pdf.table_row('Output', 'Final intraday recommendation before market close. The last advice logged to advice_history.txt for the day.')
    pdf.ln(3)

    pdf.section_title('8.3  Task 3: End-of-Day Summary (4:05 PM)')
    pdf.table_row('Parameter', 'Value', header=True)
    pdf.table_row('Cron Expression', '5 16 * * 1-5')
    pdf.table_row('Schedule', 'Every weekday at 4:05 PM ET (5 minutes after market close)')
    pdf.table_row('Prompt Source', 'get_eod_summary_prompt() from market_analyzer.py')
    pdf.table_row('Output', 'Holistic EOD summary: portfolio performance for the day and next-day outlook.')
    pdf.ln(3)

    pdf.section_title('8.4  Advice History: Intraday vs File Retention Policy')
    pdf.body(
        'Throughout the day, every recommendation generated by the cron tasks or /analyze command is appended '
        'to advice_history.txt via the centralized log_advice() function. When get_cleaned_advice_history() runs '
        '(on every dossier generation), it applies a two-layer retention policy:'
    )
    pdf.bullet('PHYSICAL FILE retention: ALL entries for today are preserved. Only the last entry from each '
               'of the past 5 business days is kept. Weekend entries are silently discarded.')
    pdf.bullet('LLM CONTEXT passed to Gemini: Only the LAST 5 entries from today (not all of them). '
               'This keeps the prompt token-efficient while the local log remains complete for review.')
    pdf.bullet('History limit: Maximum 5 previous business days. Older entries are permanently deleted from the file.')

    # ============================================================
    # PAGE 9: TRADE LEDGER
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('9. Trade Ledger (trades.csv)')

    pdf.body(
        'trades.csv is the single source of truth for all financial positions. It is an append-only CSV '
        'file. The daemon appends new rows via update_ledger(). Manual edits are possible but must preserve '
        'the column schema exactly.'
    )

    pdf.section_title('9.1  Schema')
    pdf.table_row('Column', 'Type', 'Description', header=True)
    pdf.table_row('Date', 'YYYY-MM-DD HH:MM:SS', 'Timestamp of the trade (local system time).')
    pdf.table_row('Ticker', 'String', 'TSX ticker symbol, e.g., "CNQ.TO". Always uppercase.')
    pdf.table_row('Action', 'String', '"BUY", "SELL", or "INIT" (initial portfolio seeding). INIT is treated identically to BUY for ACB purposes.')
    pdf.table_row('Quantity', 'Float', 'Number of shares traded.')
    pdf.table_row('Price', 'Float', 'Per-share price at time of trade.')
    pdf.table_row('Shares_Balance', 'Float', 'Running shares balance for this ticker after the trade. Stored for reference; not used by ACB calculation.')
    pdf.table_row('Cash_Balance', 'Float', 'Total available free cash after the trade. This is the canonical cash source used by get_acb_and_balances().')
    pdf.ln(3)

    pdf.section_title('9.2  Example')
    pdf.code_block(
        'Date,Ticker,Action,Quantity,Price,Shares_Balance,Cash_Balance\n'
        '2026-06-14 09:00:00,INIT,INIT,0,0,0,20000.00\n'
        '2026-06-14 10:30:00,CNQ.TO,BUY,100,62.50,100.0,13750.00\n'
        '2026-06-15 14:00:00,CNQ.TO,BUY,50,60.12,150.0,10756.00\n'
        '2026-06-16 11:00:00,CNQ.TO,SELL,30,64.00,120.0,12676.00'
    )

    pdf.section_title('9.3  Important Notes')
    pdf.bullet('INIT action: The very first row is typically an INIT action used to seed the initial cash balance. '
               'The Ticker column value for INIT rows is ignored by the ACB calculation.')
    pdf.bullet('Cash_Balance is the canonical cash figure: get_acb_and_balances() reads the last Cash_Balance '
               'value from the file. If this column is ever manually set incorrectly, the cash constraint '
               'logic will be wrong.')
    pdf.bullet('The file uses UTF-8 encoding and should use consistent line endings (LF or CRLF). '
               'Python\'s csv module with newline="" handles this transparently on append.')

    # ============================================================
    # PAGE 10: ADVICE HISTORY
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('10. Advice History System (advice_history.txt)')

    pdf.body(
        'advice_history.txt provides the AI with rolling memory of its own recommendations. '
        'Without it, the AI would have no context about what it said earlier in the day and could '
        'give contradictory advice. The file uses a simple timestamp-keyed format.'
    )

    pdf.section_title('10.1  File Format')
    pdf.code_block(
        '[2026-06-16 10:00:15]\n'
        'The TSX market opened with moderate volatility...\n'
        '1. HOLD CNQ.TO\n'
        '\n'
        '[2026-06-16 11:00:22]\n'
        'Oil prices have recovered slightly...\n'
        '1. HOLD CNQ.TO\n'
        '\n'
        '[2026-06-15 15:30:07]\n'
        '(Final advice from previous business day)\n'
        '1. BUY CNQ.TO\n'
    )

    pdf.section_title('10.2  Writers')
    pdf.bullet('log_advice(text) in market_analyzer.py: The single canonical writer. Both send_telegram.py '
               'and telegram_daemon.py import and call this function. It acquires a filesystem lockfile '
               '(advice.lock) before writing to prevent concurrent write corruption.')
    pdf.ln(2)

    pdf.section_title('10.3  Pruning (get_cleaned_advice_history)')
    pdf.body(
        'On every call, the function: (1) Parses all timestamp blocks via regex. '
        '(2) Groups entries by calendar date. (3) Rewrites the physical file retaining ALL entries for today '
        'and only the last entry per day for the last 5 business days. '
        '(4) Returns a bounded LLM context string with only the last 5 entries from today '
        '(not all) plus the last prior-day entry per retained date.'
    )

    pdf.section_title('10.4  Concurrency Safety')
    pdf.body(
        'All writes to advice_history.txt now route through log_advice(), which uses OS-level lockfile '
        'semantics (os.O_CREAT | os.O_EXCL) to guarantee exclusive write access. The lock is released in a '
        'finally block to prevent stale locks. In the event of a very long lock wait (>5 seconds), '
        'the write proceeds anyway to prevent advice from being permanently lost.'
    )

    # ============================================================
    # PAGE 11: DEPENDENCY REFERENCE
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('11. Dependency Reference (requirements.txt)')

    pdf.table_row('Package', 'Pinned Version', 'Purpose', header=True)
    pdf.table_row('yfinance', '1.4.1', 'Fetches OHLCV price history and ticker metadata (ex-div dates) from Yahoo Finance.')
    pdf.table_row('pandas', '3.0.1', 'DataFrame manipulation for price history and indicator computation.')
    pdf.table_row('pandas-ta', '0.4.71b0', 'Technical Analysis library. Computes EMA, RSI, ATR, SMA, and Bollinger Bands on DataFrames.')
    pdf.table_row('python-telegram-bot', '22.8', 'Async Telegram Bot API wrapper. Powers the daemon\'s polling loop and message handling.')
    pdf.table_row('google-genai', '2.8.0', 'Google Gemini API client. Used to call gemini-2.5-flash for all LLM reasoning.')
    pdf.table_row('python-dotenv', '1.2.2', 'Reads the .env file and injects variables into os.environ.')
    pdf.table_row('requests', 'latest', 'HTTP client. Used by send_telegram.py to call the Telegram sendMessage API endpoint.')
    pdf.table_row('fpdf2', '2.8.7', 'PDF generation library. Used exclusively by generate_pdf.py to produce this document.')
    pdf.ln(3)

    pdf.section_title('11.1  Installation')
    pdf.code_block(
        '# Install all dependencies:\n'
        'C:\\Users\\Aamir\\miniforge3\\python.exe -m pip install -r requirements.txt'
    )

    # ============================================================
    # PAGE 12: SECURITY HARDENING
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('12. Security Hardening')

    pdf.section_title('12.1  Telegram Bot Authorization')
    pdf.body(
        'The daemon compares every incoming message\'s chat_id against the TELEGRAM_CHAT_ID value in .env. '
        'If they do not match, the message is silently dropped (no reply) and a warning is logged to the console. '
        'This prevents unauthorized users from logging trades or extracting portfolio data even if they '
        'discover the bot token.'
    )
    pdf.code_block(
        '# In handle_message():\n'
        'if str(chat_id) != os.getenv("TELEGRAM_CHAT_ID"):\n'
        '    print(f"Unauthorized access attempt from {chat_id}")\n'
        '    return'
    )
    pdf.ln(2)

    pdf.section_title('12.2  Secrets Management')
    pdf.bullet('.env is excluded from version control by .gitignore.')
    pdf.bullet('trades.csv and advice_history.txt are also excluded, as they contain sensitive financial data.')
    pdf.bullet('No credentials are hardcoded in any .py file. All secrets are read from os.getenv().')
    pdf.ln(2)

    pdf.section_title('12.3  Input Validation')
    pdf.bullet('Trade quantity and price are parsed by the Gemini model and then cast to float() with '
               'explicit error handling. A ValueError terminates processing safely.')
    pdf.bullet('Ticker validation: The intent-extraction prompt is given the list of valid tickers from config.json, '
               'instructing the model to only extract trades for configured symbols.')
    pdf.bullet('Cash and share sufficiency checks in update_ledger() prevent the ledger from entering a '
               'negative balance state.')

    # ============================================================
    # PAGE 13: OPERATIONAL RUNBOOK
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('13. Operational Runbook')

    pdf.section_title('13.1  Daily Startup')
    pdf.code_block(
        'Step 1: Open File Explorer and navigate to c:\\Users\\Aamir\\OneDrive\\TSX-Trader\n'
        'Step 2: Double-click start_daemon.bat\n'
        '        (This runs: C:\\Users\\Aamir\\miniforge3\\python.exe telegram_daemon.py)\n'
        'Step 3: Verify the console shows: "Daemon listening for Telegram messages..."\n'
        'Step 4: The Antigravity Agent will automatically send its first\n'
        '        analysis at 10:00 AM ET via the cron schedule.'
    )
    pdf.ln(2)

    pdf.section_title('13.2  Logging a Trade via Telegram')
    pdf.code_block(
        'You:  I bought 50 CNQ at 60.50\n'
        'Bot:  Did you mean to BUY 50.0 shares of CNQ.TO @ $60.50?\n'
        '      Reply YES to confirm or NO to cancel.\n'
        'You:  yes\n'
        'Bot:  Confirmed and Recorded: BUY 50.0 CNQ.TO @ $60.50\n'
        '      CNQ.TO: 150.0 shares | Cash: $10,681.00'
    )
    pdf.ln(2)

    pdf.section_title('13.3  Requesting On-Demand Analysis')
    pdf.code_block(
        'You:  analyze\n'
        'Bot:  Generating on-demand analysis. Please wait...\n'
        '      [Returns full SHORT or MEDIUM mode recommendation]'
    )
    pdf.ln(2)

    pdf.section_title('13.4  Asking a Market Question')
    pdf.code_block(
        'You:  What is the current RSI on CNQ?\n'
        'Bot:  Reading live market data to answer your question...\n'
        '      [Returns dossier-backed answer from Gemini]'
    )
    pdf.ln(2)

    pdf.section_title('13.5  Switching Trading Mode')
    pdf.code_block(
        'You:  change mode\n'
        'Bot:  Please reply with either Short Term Mode or Medium Term Mode.\n'
        'You:  Medium Term Mode\n'
        'Bot:  Operating mode successfully updated to: MEDIUM TERM.'
    )
    pdf.ln(2)

    pdf.section_title('13.6  Restoring the Agent After Session Loss')
    pdf.body(
        'If the Antigravity agent session is lost (e.g., browser closed, session expired), the '
        'AGENT_RESTORE_INSTRUCTIONS.md file in the project root contains the exact cron expressions '
        'and prompt text needed to recreate all three scheduled tasks. Open a new session, share the file '
        'with the agent, and follow its instructions.'
    )

    # ============================================================
    # PAGE 14: TROUBLESHOOTING
    # ============================================================
    pdf.add_page()
    pdf.chapter_title('14. Troubleshooting Guide')

    pdf.section_title('14.1  Common Issues')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Bot is not responding to Telegram messages', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause 1: telegram_daemon.py is not running. Check for the console window or re-run start_daemon.bat.\n'
             'Cause 2: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env is wrong. Verify with BotFather and your Telegram account.\n'
             'Cause 3: chat_id mismatch. Check the console for "Unauthorized access attempt" log lines.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Analysis shows "Error fetching [TICKER]"', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause: Yahoo Finance is temporarily unavailable or the ticker symbol is invalid. '
             'Wait a few minutes and retry, or verify the ticker in config.json is a valid Yahoo Finance symbol.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Cron-scheduled messages have stopped arriving', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause: The Antigravity agent session has been lost or the schedule tasks were cancelled. '
             'Open a new session and use AGENT_RESTORE_INSTRUCTIONS.md to recreate the three cron tasks.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, '"Insufficient cash" error when logging a BUY', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause: The Cash_Balance in trades.csv shows insufficient funds for the trade. '
             'Check the most recent Cash_Balance value in trades.csv. '
             'If incorrect due to a manual edit, fix the last row\'s Cash_Balance column.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'ValueError: Invalid action when logging a trade', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause: The Gemini intent-extraction returned an unexpected action value. '
             'This can happen if the user\'s message is ambiguous. Rephrase the trade clearly: '
             '"I bought 100 CNQ at 60.12".')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Telegram messages are being truncated', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('Cause: A very long analysis is being sent by a code path that does not use chunking. '
             'The daemon\'s send_chunked_reply() handles this for /analyze and Q&A. '
             'The CLI send_telegram.py also chunks to 4000 characters. If truncation occurs, '
             'check that the calling code is routing through one of these handlers.')

    pdf.set_font('helvetica', 'B', 10)
    pdf.cell(0, 6, 'Advice history is empty on first run of the day', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.body('This is expected behaviour. advice_history.txt is populated throughout the day '
             'as scheduled and on-demand analyses are sent. By the second hourly analysis, '
             'the AI will have its first advice entry available as context.')

    pdf.output("TSX_Assistant_Guide_Final.pdf")
    print("PDF generated successfully.")


if __name__ == "__main__":
    create_pdf()
