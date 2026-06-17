import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from market_analyzer import get_tickers

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=GEMINI_API_KEY)

tickers = get_tickers()
tickers_str = ", ".join(tickers)

user_text = "I just bought 15 shares of ABX for 25.50"
prompt = f"""
You are a trading extraction tool. Extract the trade details from the following message: "{user_text}"
Return ONLY a JSON object with the following keys, and nothing else:
- action: "BUY" or "SELL"
- ticker: The ticker symbol with .TO suffix (valid tickers: {tickers_str}). If user says just the name without .TO, append .TO.
- quantity: float
- price: float

Example: {{"action": "SELL", "ticker": "{tickers[0] if tickers else 'CNQ.TO'}", "quantity": 20.0, "price": 45.50}}
"""

try:
    print("Testing Gemini API connection...")
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    print("Response successful!")
    print("Raw output:", response.text)
    
    # Verify it parses as JSON
    data = json.loads(response.text)
    print("Parsed JSON object:", data)
except Exception as e:
    print("API Error:", e)
