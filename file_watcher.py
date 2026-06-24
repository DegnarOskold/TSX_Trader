import time
import os
import sys

QUEUE_FILE = "incoming_queue.jsonl"

PROCESSING_FILE = "incoming_processing.jsonl"

def main():
    if not os.path.exists(QUEUE_FILE):
        open(QUEUE_FILE, 'w').close()
        
    while True:
        try:
            if os.path.exists(QUEUE_FILE) and os.path.getsize(QUEUE_FILE) > 0:
                os.rename(QUEUE_FILE, PROCESSING_FILE)
                
                lines = []
                with open(PROCESSING_FILE, 'r') as f:
                    lines = f.readlines()
                    
                if lines:
                    for line in lines:
                        if line.strip():
                            print(f"NEW_MESSAGE:{line.strip()}", flush=True)
                    os.remove(PROCESSING_FILE)
                else:
                    os.remove(PROCESSING_FILE)
        except Exception:
            pass
            
        time.sleep(1)

if __name__ == "__main__":
    main()
