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
                    first_msg = lines.pop(0)
                    
                    if lines:
                        with open(QUEUE_FILE, 'a') as f:
                            for line in lines:
                                f.write(line)
                                
                    os.remove(PROCESSING_FILE)
                    
                    if first_msg.strip():
                        print(f"NEW_MESSAGE:{first_msg.strip()}", flush=True)
                        sys.exit(0)
                else:
                    os.remove(PROCESSING_FILE)
        except Exception:
            pass
            
        time.sleep(1)

if __name__ == "__main__":
    main()
