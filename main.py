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

threading.Thread(target=run_web, daemon=True).start()

# --- TELEGRAM CONFIG ---
BOT_TOKEN = "8758337374:AAEWM-sRhg0nAUTSnCP0xodU7S-hm7mHIkw"
CHAT_ID = "6764734331"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        print("Telegram Send Status:", res.status_code)
    except Exception as e:
        print("Telegram Error:", e)

# --- ACCURATE RSI CALCULATION (WILDER'S SMOOTHING) ---
def get_rsi(df, window=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df

# --- FETCH CANDLE DATA FROM BINANCE ---
def fetch_candles(symbol="EURUSDT"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=100"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10).json()
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
            return get_rsi(df)
    except Exception as e:
        print("Data Fetch Error:", e)
    return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("🚀 *Nafi Trade Bot Active! Scanning Market...*")

last_signaled_candle = 0

while True:
    try:
        df = fetch_candles("EURUSDT")
        if df is not None and len(df) > 15:
            latest = df.iloc[-1]
            curr_candle_time = latest['epoch']
            rsi_val = round(latest['rsi'], 2)

            if curr_candle_time != last_signaled_candle:
                # Fast Test Trigger (RSI 48 / 52)
                if rsi_val <= 48:
                    msg = f"🟢 *BINARY CALL SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {latest['close']}\n🎯 RSI: {rsi_val}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time
                elif rsi_val >= 52:
                    msg = f"🔴 *BINARY PUT SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {latest['close']}\n🎯 RSI: {rsi_val}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time

        time.sleep(15)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(15)
