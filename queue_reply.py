"""Reusable script to queue a message to outgoing_queue.jsonl.
Usage: python queue_reply.py "Your message text here"
"""
import json
import sys
import os
from dotenv import load_dotenv

load_dotenv()
chat_id = os.getenv("TELEGRAM_CHAT_ID")

if len(sys.argv) < 2:
    print("Usage: python queue_reply.py <message_file.txt>")
    sys.exit(1)

file_path = sys.argv[1]
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

with open(file_path, "r", encoding="utf-8") as f:
    message_text = f.read()

msg = {
    "chat_id": chat_id,
    "text": message_text
}

with open("outgoing_queue.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps(msg) + "\n")

print("Message queued.")
