import os
import json
import asyncio
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRADES_FILE = "trades.csv"

# Global state for pending trades (if handled by external agent, but we can leave this here just in case, or remove it. Better to remove pending trades since Antigravity handles the conversation flow)


async def send_chunked_reply(update, text):
    """Telegram limits messages to 4096 characters. Chunk safely."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.message.reply_text(chunk)


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
        
    try:
        os.rename("outgoing_queue.jsonl", "outgoing_processing.jsonl")
    except Exception:
        return
        
    lines = []
    with open("outgoing_processing.jsonl", "r") as f:
        lines = f.readlines()
        
    failed_lines = []
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
            failed_lines.append(line)
            
    if failed_lines:
        with open("outgoing_queue.jsonl", "a") as f:
            for line in failed_lines:
                f.write(line)
                
    try:
        os.remove("outgoing_processing.jsonl")
    except Exception:
        pass


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
