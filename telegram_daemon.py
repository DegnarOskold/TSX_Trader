import os
import json
import asyncio
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from market_analyzer import log_advice

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TRADES_FILE = "trades.csv"
DAEMON_START_TIME = datetime.datetime.now()


async def send_chunked_reply(update, text):
    """Telegram limits messages to 4096 characters. Chunk safely."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        await update.message.reply_text(chunk)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Trading Daemon online. I am a relay for the Antigravity AI agent. Send /help for more info.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 **TSX Trading Advisor Help** 🤖\n\n"
        "I am a message relay for the Antigravity AI agent. Any message you send will be processed by the AI.\n"
        "You can:\n"
        "1. **Log Trades**: Naturally (e.g., 'Bought 100 ABX at 23.50').\n"
        "2. **Analyze**: Ask for a market breakdown.\n"
        "3. **Q&A**: Ask any questions about the portfolio.\n\n"
        "Commands:\n"
        "/status - Check daemon health and queue size"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uptime = datetime.datetime.now() - DAEMON_START_TIME
    in_q = 0
    out_q = 0
    if os.path.exists("incoming_queue.jsonl"):
        with open("incoming_queue.jsonl", "r") as f:
            in_q = len(f.readlines())
    if os.path.exists("outgoing_queue.jsonl"):
        with open("outgoing_queue.jsonl", "r") as f:
            out_q = len(f.readlines())
            
    status_text = (
        f"🟢 **Daemon Status: ONLINE**\n"
        f"Uptime: {uptime}\n"
        f"Incoming Queue: {in_q} messages\n"
        f"Outgoing Queue: {out_q} messages"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

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
                
            # Centralized logging: everything the agent says is recorded to history
            try:
                log_advice(text)
            except Exception as log_err:
                print("Error logging advice:", log_err)
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
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start polling job for outgoing messages
    app.job_queue.run_repeating(poll_outgoing_queue, interval=2.0)
    
    print("Daemon listening for Telegram messages...")
    app.run_polling()

if __name__ == "__main__":
    main()
