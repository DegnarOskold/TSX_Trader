import os
import sys
from dotenv import load_dotenv
from google import genai
from google.genai import types
from market_analyzer import get_analysis_prompt, get_eod_summary_prompt
from send_telegram import send_message

def main():
    load_dotenv()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY missing in .env")
        sys.exit(1)
        
    client = genai.Client(api_key=api_key)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--eod":
        print("Running EOD summary analysis...")
        prompt = get_eod_summary_prompt()
    elif len(sys.argv) > 1 and sys.argv[1] == "--hourly":
        print("Running hourly analysis...")
        prompt = get_analysis_prompt()
    else:
        print("No valid flag provided. Defaulting to hourly analysis...")
        prompt = get_analysis_prompt()
        
    print("Generating response from Gemini...")
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        print("Sending to Telegram...")
        send_message(response.text)
    except Exception as e:
        print(f"Error during analysis generation or transmission: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
