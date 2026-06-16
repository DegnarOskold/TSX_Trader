import os
import sys
import requests
from dotenv import load_dotenv

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
    
    for chunk in chunks:
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk
        }
        
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Message chunk sent successfully.")
            # Log the sent message
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open("advice_history.txt", "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}]\n{chunk}\n\n")
        else:
            print(f"Failed to send message chunk: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
    else:
        message = sys.stdin.read()
    
    send_message(message)
