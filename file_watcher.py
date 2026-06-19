import time
import os
import sys

QUEUE_FILE = "incoming_queue.jsonl"

def main():
    if not os.path.exists(QUEUE_FILE):
        open(QUEUE_FILE, 'w').close()
        
    last_size = os.path.getsize(QUEUE_FILE)
    
    while True:
        try:
            current_size = os.path.getsize(QUEUE_FILE)
            if current_size < last_size:
                last_size = 0
            
            if current_size > last_size:
                with open(QUEUE_FILE, 'r') as f:
                    f.seek(last_size)
                    line = f.readline()
                    if line:
                        print(f"NEW_MESSAGE:{line.strip()}", flush=True)
                        sys.exit(0)  # Exit immediately to wake up Antigravity!
        except Exception:
            pass
            
        time.sleep(1)

if __name__ == "__main__":
    main()
