import os
import time
import subprocess
import psutil

def is_process_running(script_name):
    for q in psutil.process_iter(['name', 'cmdline']):
        try:
            if q.info['cmdline'] and script_name in ' '.join(q.info['cmdline']):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False

def start_process(script_path):
    subprocess.Popen(['C:\\Users\\Aamir\\miniforge3\\python.exe', script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)

if __name__ == '__main__':
    watch_script = 'file_watcher.py'
    # Start loop
    while True:
        if not is_process_running(watch_script):
            start_process(watch_script)
        time.sleep(600)  # Check every 10 minutes
