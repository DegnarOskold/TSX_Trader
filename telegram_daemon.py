import os
import csv
import json
import asyncio
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from market_analyzer import generate_dossier, get_analysis_prompt, get_tickers, get_acb_and_balances, log_advice

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRADES_FILE = "trades.csv"

# Initialize Gemini Client
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

# Global state for pending trades
pending_trades = {}

async def send_chunked_reply(update, text):
    """Telegram limits messages to 4096 characters. Chunk safely."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.message.reply_text(chunk)

def update_ledger(action, ticker, quantity, price):
    balances = get_acb_and_balances()
    positions = balances["positions"]
    cash_bal = balances["cash"]
    
    cost = round(quantity * price, 2)
    current_shares = positions.get(ticker, {}).get("shares", 0.0)
    
    if action == "BUY":
        if cash_bal < cost:
            raise ValueError(f"Insufficient cash! Cost: ${cost:.2f}, Cash: ${cash_bal:.2f}")
        cash_bal = round(cash_bal - cost, 2)
        current_shares += quantity
    elif action == "SELL":
        if current_shares < quantity:
            raise ValueError(f"Insufficient shares of {ticker}. Own: {current_shares}, Trying to sell: {quantity}")
        current_shares -= quantity
        cash_bal = round(cash_bal + cost, 2)
    else:
        raise ValueError("Invalid action. Must be BUY or SELL.")

    date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(TRADES_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date_str, ticker.upper(), action, quantity, price, round(current_shares, 4), cash_bal])
        
    return {"ticker": ticker, "shares": current_shares, "cash": cash_bal}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trading Daemon online. Tell me about your trades naturally (e.g., 'I sold 20 CNQ at 45.50'). Send /help for more info.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **TSX Trading Advisor Help** 🤖\n\n"
        "Here's what I can do:\n"
        "1. **Log Trades**: Just tell me naturally (e.g., 'Bought 100 ABX at 23.50').\n"
        "2. **Analysis**: Send `analyze` or `analysis` to get a full market breakdown and recommendation.\n"
        "3. **Change Mode**: Send `change mode` to switch between Short and Medium term horizons.\n"
        "4. **Q&A**: Ask any question about the market or your portfolio, and I'll answer based on the live dossier."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    if str(chat_id) != os.getenv("TELEGRAM_CHAT_ID"):
        print(f"Unauthorized access attempt from {chat_id}")
        return
        
    if not client:
        await update.message.reply_text("Gemini API key not configured. Cannot parse message.")
        return
        
    user_text_lower = user_text.strip().lower()
    
    # Handle pending trade confirmation
    if chat_id in pending_trades and user_text_lower in ["yes", "no"]:
        if user_text_lower == "no":
            del pending_trades[chat_id]
            await update.message.reply_text("❌ Trade cancelled.")
            return
        
        # User confirmed YES
        trade = pending_trades.pop(chat_id)
        try:
            result = update_ledger(trade['action'], trade['ticker'], trade['quantity'], trade['price'])
            msg = f"✅ Confirmed and Recorded: {trade['action']} {trade['quantity']} {trade['ticker']} @ ${trade['price']:.2f}\n"
            msg += f"{trade['ticker']}: {result['shares']:.4f} shares | Cash: ${result['cash']:.2f}"
            await update.message.reply_text(msg)
        except ValueError as ve:
            await update.message.reply_text(f"❌ Error updating ledger: {str(ve)}")
        return
    
    if user_text_lower == "change mode":
        await update.message.reply_text("⚙️ Please reply with either 'Short Term Mode' or 'Medium Term Mode'.")
        return
        
    if user_text_lower in ["short term mode", "medium term mode"]:
        new_mode = "SHORT" if user_text_lower == "short term mode" else "MEDIUM"
        # Read existing config to preserve other keys (e.g., tickers)
        config = {}
        if os.path.exists("config.json"):
            with open("config.json", "r") as f:
                config = json.load(f)
        config["mode"] = new_mode
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)
        await update.message.reply_text(f"✅ Operating mode successfully updated to: {new_mode} TERM.")
        return
        
    if user_text_lower in ["analyze", "analysis"]:
        await update.message.reply_text("🤖 Generating on-demand analysis. Please wait a moment...")
        
        try:
            prompt = get_analysis_prompt()
        except Exception as e:
            await update.message.reply_text(f"❌ Could not generate live dossier: {e}")
            return
        
        # Check market hours (M-F, 9:30 AM - 4:00 PM ET)
        now = datetime.datetime.now()
        is_weekend = now.weekday() >= 5
        market_open = 9 * 60 + 30
        market_close = 16 * 60
        current_mins = now.hour * 60 + now.minute
        is_market_hours = not is_weekend and (market_open <= current_mins <= market_close)
        
        warning_prefix = ""
        if not is_market_hours:
            warning_prefix = "⚠️ *Note: The market is currently closed. This analysis is based on the last session's closing data.*\n\n"
        
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            await send_chunked_reply(update, warning_prefix + response.text)
            
            # Log on-demand analysis
            log_advice(response.text)
                
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to generate analysis: {e}")
            
        return

        
    tickers = get_tickers()
    tickers_str = ", ".join(tickers)
    
    # Step 1: Lightweight Intent Extraction (Saves API Tokens)
    prompt_intent = f"""
    You are a trading extraction tool. 
    The user has sent the following message: "{user_text}"
    
    Determine if the user is logging a TRADE execution or asking a QUESTION.
    Return ONLY a JSON object with the following keys, and nothing else:
    - intent: "TRADE" or "QUESTION"
    
    If intent is "TRADE", include:
    - action: "BUY" or "SELL"
    - ticker: The ticker symbol with .TO suffix (valid tickers: {tickers_str}). If the user says just the name without .TO, append .TO.
    - quantity: float
    - price: float
    
    Examples: 
    {{"intent": "TRADE", "action": "SELL", "ticker": "CNQ.TO", "quantity": 20.0, "price": 45.50}}
    {{"intent": "QUESTION"}}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt_intent,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        
        intent = data.get('intent', 'TRADE')
        
        if intent == "QUESTION":
            await update.message.reply_text("🤖 Reading live market data to answer your question...")
            
            # Step 2: Heavyweight Dossier Generation (Only when needed)
            try:
                current_dossier = generate_dossier()
            except Exception as e:
                current_dossier = f"Could not generate live dossier: {e}"
                
            prompt_qa = f"""
            You are a financial AI assistant. 
            You have access to the following live market dossier:
            {current_dossier}
            
            The user has asked the following question: "{user_text}"
            
            Please provide a detailed response to the user's question, utilizing the data from the dossier. Keep it concise.
            """
            try:
                qa_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt_qa
                )
                await send_chunked_reply(update, f"🤖 {qa_response.text}")
            except Exception as e:
                await update.message.reply_text(f"❌ Failed to generate answer: {str(e)}")
            return
            
        # Check if the LLM successfully extracted the fields for TRADE
        action = data.get('action')
        ticker = data.get('ticker')
        quantity_raw = data.get('quantity')
        price_raw = data.get('price')
        
        if not action or not ticker or quantity_raw is None or price_raw is None:
            await update.message.reply_text("🤔 I couldn't quite understand that. If it was a trade, make sure to include the action, ticker, quantity, and price. If it was a question, please rephrase it clearly.")
            return
            
        quantity = float(quantity_raw)
        price = float(price_raw)
        
        # Store in pending_trades instead of executing immediately
        pending_trades[chat_id] = {
            "action": action,
            "ticker": ticker,
            "quantity": quantity,
            "price": price
        }
        
        await update.message.reply_text(f"Did you mean to **{action}** {quantity} shares of **{ticker}** @ **${price:.2f}**?\n\nReply YES to confirm or NO to cancel.")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse or process message: {str(e)}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return
        
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Daemon listening for Telegram messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
