from flask import Flask
import threading
import os
import time
import requests
import pandas as pd
import numpy as np

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

if not os.environ.get("WERKZEUG_RUN_MAIN"):
    threading.Thread(target=run_web, daemon=True).start()

# --- TELEGRAM CONFIG ---
BOT_TOKEN = "8758337374:AAEWM-sRhg0nAUTSnCP0xodU7S-hm7mHIkw"
CHAT_ID = "6764734331"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print("Telegram Error:", e)

# --- YAHOO FINANCE DATA (EUR/USD 1m Interval) ---
def fetch_yahoo_data():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?interval=1m&range=1h"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        quote = result['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'epoch': timestamps,
            'open': quote['open'],
            'high': quote['high'],
            'low': quote['low'],
            'close': quote['close']
        }).dropna()
        
        # Calculate Bollinger Bands
        df['sma'] = df['close'].rolling(window=20).mean()
        df['std'] = df['close'].rolling(window=20).std()
        df['upper_band'] = df['sma'] + (df['std'] * 1.8)
        df['lower_band'] = df['sma'] - (df['std'] * 1.8)
        
        return df
    except Exception as e:
        print("Yahoo Data Error:", e)
        return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("🚀 *Nafi Yahoo Forex Bot Online!*")

last_signaled_time = 0

while True:
    try:
        df = fetch_yahoo_data()
        if df is not None and len(df) > 20:
            latest = df.iloc[-1]
            curr_time = latest['epoch']

            if curr_time != last_signaled_time:
                close = latest['close']
                upper = latest['upper_band']
                lower = latest['lower_band']

                # Signal Logic
                if close <= lower:
                    msg = f"🟢 *BINARY CALL (BUY) SIGNAL*\n📌 Asset: EUR/USD (Yahoo)\n⏱ Expiry: 1 MIN\n📊 Price: {close:.5f}"
                    send_telegram(msg)
                    last_signaled_time = curr_time
                elif close >= upper:
                    msg = f"🔴 *BINARY PUT (SELL) SIGNAL*\n📌 Asset: EUR/USD (Yahoo)\n⏱ Expiry: 1 MIN\n📊 Price: {close:.5f}"
                    send_telegram(msg)
                    last_signaled_time = curr_time

        time.sleep(20)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(20)
