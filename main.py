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

# --- FAST FOREX DATA FETCH ---
def fetch_market_data():
    # Public fast tick data stream for EUR/USD
    url = "https://api.coinglass.com/api/pro/v1/futures/openInterest"
    # Fallback to direct price API with no IP block
    data_url = "https://api.binance.us/api/v3/klines?symbol=EURUSD&interval=1m&limit=50"
    try:
        res = requests.get(data_url, timeout=5).json()
        if isinstance(res, list) and len(res) > 0:
            data = []
            for item in res:
                data.append({
                    'epoch': item[0],
                    'open': float(item[1]),
                    'high': float(item[2]),
                    'low': float(item[3]),
                    'close': float(item[4])
                })
            df = pd.DataFrame(data)
            
            # Indicator Calculations (Bollinger Bands & RSI)
            df['sma'] = df['close'].rolling(window=14).mean()
            df['std'] = df['close'].rolling(window=14).std()
            df['upper'] = df['sma'] + (df['std'] * 1.5)
            df['lower'] = df['sma'] - (df['std'] * 1.5)
            
            # Quick RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)
            avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
            rs = avg_gain / avg_loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            return df
    except Exception as e:
        print("Data Error:", e)
    return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("⚡ *Nafi Ultra-Fast Signal Bot Online!*")

last_signaled_time = 0

while True:
    try:
        df = fetch_market_data()
        if df is not None and len(df) > 15:
            latest = df.iloc[-1]
            curr_time = latest['epoch']

            if curr_time != last_signaled_time:
                close = latest['close']
                rsi = round(latest['rsi'], 2)
                upper = latest['upper']
                lower = latest['lower']

                # Quick Trigger Conditions
                if close <= lower or rsi <= 45:
                    msg = f"🟢 *QUOTEX CALL (BUY) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close}\n🎯 RSI: {rsi}"
                    send_telegram(msg)
                    last_signaled_time = curr_time
                elif close >= upper or rsi >= 55:
                    msg = f"🔴 *QUOTEX PUT (SELL) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close}\n🎯 RSI: {rsi}"
                    send_telegram(msg)
                    last_signaled_time = curr_time

        time.sleep(10)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(10)
