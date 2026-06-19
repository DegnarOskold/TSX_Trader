import os
import csv
import json
import asyncio
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from market_analyzer import get_tickers, get_acb_and_balances

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRADES_FILE = "trades.csv"

# Global state for pending trades (if handled by external agent, but we can leave this here just in case, or remove it. Better to remove pending trades since Antigravity handles the conversation flow)


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
        if quantity == 999999.9:
            quantity = current_shares
            cost = round(quantity * price, 2)
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
        
    msg_id = update.message.message_id
    data = {
        "chat_id": chat_id,
        "msg_id": msg_id,
        "text": user_text,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    with open("incoming_queue.jsonl", "a") as f:
        f.write(json.dumps(data) + "\n")

async def poll_outgoing_queue(context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists("outgoing_queue.jsonl"):
        return
        
    lines = []
    with open("outgoing_queue.jsonl", "r") as f:
        lines = f.readlines()
        
    if not lines:
        return
        
    # Clear the file since we read the contents
    open("outgoing_queue.jsonl", "w").close()
    
    for line in lines:
        if not line.strip(): continue
        try:
            data = json.loads(line)
            chat_id = data['chat_id']
            text = data['text']
            
            # Telegram limits messages to 4096 characters. Chunk safely.
            text = text.replace('$', 'CAD ')
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk)
        except Exception as e:
            print("Error sending queued message:", e)


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        return
        
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling job for outgoing messages
    app.job_queue.run_repeating(poll_outgoing_queue, interval=2.0)
    
    print("Daemon listening for Telegram messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
