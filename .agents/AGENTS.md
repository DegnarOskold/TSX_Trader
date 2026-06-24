# Antigravity Trade Analysis Guidelines

- When generating a BUY recommendation for a stock, ALWAYS calculate and provide a **Target Sell Price** (e.g., using Upper Bollinger Bands or an ATR-based target) and a **Stop Loss Price** so the user can easily input these limits into their broker.

- **Macro Override (Contrarian Entries):** You may bypass the strict EMA downtrend rule and recommend a Speculative BUY ONLY IF: (a) 7-day RSI is deeply oversold (< 25), (b) There is a top-tier macroeconomic catalyst in the news that directly and positively impacts the sector, and (c) You explicitly label it as a Speculative Macro Entry with a small position size.
- **Volume Capitulation Threshold:** A Vol_Ratio > 1.25 (Volume is 1.25x normal) during a drop is considered Capitulation (panic selling is exhausted) and serves as a bullish reversal signal.
- **Low-Volume Scaled Entry:** You may relax the strict high-volume requirement (> 1.25x) and recommend a BUY if a stock flashes a clean bullish technical setup (e.g., EMA 5 crossing above EMA 9). However, because this is a higher-risk setup lacking institutional volume confirmation, you MUST explicitly recommend scaling in with a smaller position size (e.g., 25% or 50% allocation) and clearly label the trade as a "Low-Volume Scaled Entry".
- **Momentum Breakout Exception:** If a stock flashes a clean bullish EMA crossover but its RSI is elevated (e.g., > 60), you should still allow a "Low-Volume Scaled Entry" (25% allocation) as long as the broader sector is green. Momentum stocks often stay overbought for long periods during breakouts.
- **Time-of-Day Filter:** Never initiate a new "Low-Volume Scaled Entry" signal between 11:00 AM and 2:00 PM ET. If volume is light, wait for the afternoon session to confirm the trend has not faded.
- **Intraday Reversal Trigger:** Catch extreme intraday V-bottoms before lagging moving averages cross. If a stock drops significantly intraday (e.g., >1.25% below open) but its 7-day RSI dips below 35 (oversold) and then immediately rebounds within two 30-minute intervals, you may allow a speculative "Reversal Buy" on a partial position.

# Telegram Security Protocol
- **Code Change Authentication:** If you receive a request via the background task (NEW_MESSAGE from Telegram) that asks you to modify any software code (e.g., editing .py files, AGENTS.md, .env, or running arbitrary system/PowerShell commands), you MUST halt and challenge the user for an 8-digit PIN by sending a message back to the Telegram queue (outgoing_queue.jsonl).
- **PIN Hint:** When challenging the user, you must provide the PIN hint loaded from TELEGRAM_PIN_HINT in the .env file.
- Do NOT proceed with the requested code change or system command until the user replies via Telegram with the correct PIN matching TELEGRAM_PIN in the .env file.
- **Local User Exception:** If the request originates directly from the local Antigravity interface (<USER_REQUEST>), NO PIN is required.

