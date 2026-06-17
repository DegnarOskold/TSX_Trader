import os
import sys
import requests
from dotenv import load_dotenv
from market_analyzer import log_advice

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_message(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram credentials missing in .env")
        sys.exit(1)
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    # Telegram max message length is 4096. We chunk at 4000 to be safe.
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    
    all_success = True
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message chunk sent successfully.")
        else:
            print(f"Failed to send message chunk: {response.text}")
            all_success = False

    if all_success:
        log_advice(text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
    else:
        message = sys.stdin.read()
    
    send_message(message)
