import os
import csv
import json
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types
from market_analyzer import generate_dossier

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TRADES_FILE = "trades.csv"

# Initialize Gemini Client
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None

def get_latest_balances():
    if not os.path.exists(TRADES_FILE):
        return {"CNQ": 0.0, "ABX": 0.0, "Cash": 0.0}
    with open(TRADES_FILE, 'r') as f:
        reader = list(csv.DictReader(f))
        if len(reader) == 0:
            return {"CNQ": 0.0, "ABX": 0.0, "Cash": 0.0}
        last_row = reader[-1]
        return {
            "CNQ": float(last_row.get("CNQ_Balance", 0)),
            "ABX": float(last_row.get("ABX_Balance", 0)),
            "Cash": float(last_row.get("Cash_Balance", 0))
        }

def update_ledger(action, ticker, quantity, price):
    balances = get_latest_balances()
    cnq_bal = balances["CNQ"]
    abx_bal = balances["ABX"]
    cash_bal = balances["Cash"]
    
    cost = quantity * price
    ticker_clean = ticker.upper().replace(".TO", "")
    
    if action == "BUY":
        if cash_bal < cost:
            raise ValueError(f"Insufficient cash! Cost: ${cost:.2f}, Cash: ${cash_bal:.2f}")
        cash_bal -= cost
        if ticker_clean == "CNQ":
            cnq_bal += quantity
        elif ticker_clean == "ABX":
            abx_bal += quantity
    elif action == "SELL":
        if ticker_clean == "CNQ":
            if cnq_bal < quantity:
                raise ValueError(f"Insufficient shares of CNQ. Own: {cnq_bal}, Trying to sell: {quantity}")
            cnq_bal -= quantity
        elif ticker_clean == "ABX":
            if abx_bal < quantity:
                raise ValueError(f"Insufficient shares of ABX. Own: {abx_bal}, Trying to sell: {quantity}")
            abx_bal -= quantity
        cash_bal += cost
    else:
        raise ValueError("Invalid action. Must be BUY or SELL.")

    import datetime
    date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    with open(TRADES_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date_str, ticker.upper(), action, quantity, price, cnq_bal, abx_bal, cash_bal])
        
    return cnq_bal, abx_bal, cash_bal

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trading Daemon online. Tell me about your trades naturally (e.g., 'I sold 20 CNQ at 45.50').")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    if not client:
        await update.message.reply_text("Gemini API key not configured. Cannot parse message.")
        return
        
    try:
        current_dossier = generate_dossier()
    except Exception as e:
        current_dossier = f"Could not generate live dossier: {e}"
        
    prompt = f"""
    You are a financial AI assistant and trading extraction tool. 
    You have access to the following live market dossier:
    {current_dossier}
    
    The user has sent the following message: "{user_text}"
    
    Determine if the user is logging a TRADE execution or asking a QUESTION.
    Return ONLY a JSON object with the following keys, and nothing else:
    - intent: "TRADE" or "QUESTION"
    
    If intent is "TRADE", include:
    - action: "BUY" or "SELL"
    - ticker: "CNQ.TO" or "ABX.TO" (if user says CNQ, assume CNQ.TO)
    - quantity: float
    - price: float
    
    If intent is "QUESTION", include:
    - answer: "Your detailed response to the user's question, utilizing the data from the dossier."
    
    Examples: 
    {{"intent": "TRADE", "action": "SELL", "ticker": "CNQ.TO", "quantity": 20.0, "price": 45.50}}
    {{"intent": "QUESTION", "answer": "The discounted valuation opportunity for ABX is driven by recent analyst upgrades following the gold sector rotation..."}}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        
        intent = data.get('intent', 'TRADE')
        
        if intent == "QUESTION":
            answer = data.get('answer', "I'm sorry, I couldn't formulate an answer to that question.")
            await update.message.reply_text(f"🤖 {answer}")
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
        
        try:
            cnq_bal, abx_bal, cash_bal = update_ledger(action, ticker, quantity, price)
            msg = f"✅ Recorded: {action} {quantity} {ticker} @ ${price:.2f}\n"
            msg += f"Balances -> CNQ: {cnq_bal:.4f} | ABX: {abx_bal:.4f} | Cash: ${cash_bal:.2f}"
            await update.message.reply_text(msg)
        except ValueError as ve:
            await update.message.reply_text(f"❌ Error updating ledger: {str(ve)}")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to parse or process message: {str(e)}")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return
        
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Daemon listening for Telegram messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
