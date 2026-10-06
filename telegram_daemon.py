import os
import json
import asyncio
import datetime
import threading
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from market_analyzer import log_advice

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DAEMON_START_TIME = datetime.datetime.now()

ALLOWED_CHAT_IDS_STR = os.getenv("ALLOWED_CHAT_IDS", "")
if not ALLOWED_CHAT_IDS_STR:
    ALLOWED_CHAT_IDS_STR = os.getenv("TELEGRAM_CHAT_ID", "")
ALLOWED_CHAT_IDS = [x.strip() for x in ALLOWED_CHAT_IDS_STR.split(",") if x.strip()]

def is_authorized(update: Update) -> bool:
    if not ALLOWED_CHAT_IDS:
        print("[SECURITY] ALLOWED_CHAT_IDS is empty. All messages will be blocked.", flush=True)
        return False
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    if chat_id in ALLOWED_CHAT_IDS or user_id in ALLOWED_CHAT_IDS:
        return True
    print(f"[SECURITY] Blocked unauthorized message from chat_id={chat_id} user_id={user_id}", flush=True)
    return False

def suicide_soon():
    time.sleep(5.0)
    os._exit(0)

def stream_to_agent(chat_id, user_id, username, msg_id, text):
    """Streams the incoming message directly to stdout for Antigravity and exits after delay."""
    msg_data = {
        "event_type": "TELEGRAM_MESSAGE",
        "chat_id": chat_id,
        "user_id": user_id,
        "username": username,
        "msg_id": msg_id,
        "text": text,
        "timestamp": datetime.datetime.now().isoformat()
    }
    # Print the exact format expected by the agent
    print(f"NEW_MESSAGE:{json.dumps(msg_data)}", flush=True)
    threading.Thread(target=suicide_soon).start()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
    await update.message.reply_text("Trading Daemon online. I am a relay for the Antigravity AI agent. Send /help for more info.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update): return
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
    if not is_authorized(update): return
    uptime = datetime.datetime.now() - DAEMON_START_TIME
    out_q = 0
    if os.path.exists("outgoing_queue.jsonl"):
        with open("outgoing_queue.jsonl", "r", encoding="utf-8") as f:
            out_q = len(f.readlines())
            
    status_text = (
        f"🟢 **Daemon Status: ONLINE (One-Shot Mode)**\n"
        f"Uptime: {uptime}\n"
        f"Outgoing Queue: {out_q} messages"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return

    user_text = update.message.text if update.message else ""
    if not user_text:
        return
        
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    msg_id = update.message.message_id
    
    stream_to_agent(chat_id, user_id, username, msg_id, user_text)


async def poll_outgoing_queue(context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists("outgoing_processing.jsonl"):
        if not os.path.exists("outgoing_queue.jsonl"):
            return
        try:
            os.rename("outgoing_queue.jsonl", "outgoing_processing.jsonl")
        except Exception:
            return
        
    lines = []
    try:
        with open("outgoing_processing.jsonl", "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as read_err:
        print("Error reading outgoing_processing.jsonl:", read_err)
        return
        
    failed_lines = []
    for line in lines:
        if not line.strip(): continue
        try:
            data = json.loads(line)
            chat_id = data['chat_id']
            text = data['text']
            
            # Telegram limits messages to 4096 characters. Chunk safely.
            chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
            for chunk in chunks:
                await context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode="Markdown")
                
            # Centralized logging: everything the agent says is recorded to history
            try:
                log_advice(text)
            except Exception as log_err:
                print("Error logging advice:", log_err)
        except Exception as e:
            print("Error sending queued message:", e)
            failed_lines.append(line)
            
    if failed_lines:
        with open("outgoing_queue.jsonl", "a", encoding="utf-8") as f:
            for line in failed_lines:
                f.write(line)
                
    try:
        os.remove("outgoing_processing.jsonl")
    except Exception:
        pass


async def main():
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
    
    print("Daemon listening for Telegram messages (One-Shot Mode)...", flush=True)
    
    # Run polling but keep the loop open so `os._exit()` can kill it cleanly when a message arrives
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Shutting down...", flush=True)
