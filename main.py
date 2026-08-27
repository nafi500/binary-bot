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

# Prevent Duplicate Threads
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

# --- BOLLINGER BANDS & EMA ---
def get_indicators(df):
    # Bollinger Bands (20, 1.8) - Adjusted for quick signals
    df['sma'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma'] + (df['std'] * 1.8)
    df['lower_band'] = df['sma'] - (df['std'] * 1.8)
    
    # EMA 5 & 20 for momentum
    df['ema_fast'] = df['close'].ewm(span=5, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=20, adjust=False).mean()
    return df

# --- FETCH CANDLE DATA FROM BINANCE ---
def fetch_candles(symbol="EURUSDT"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&limit=50"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
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
            return get_indicators(df)
    except Exception as e:
        print("Data Fetch Error:", e)
    return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("🚀 *Nafi Super-Indicator Bot Online!*")

last_signaled_candle = 0

while True:
    try:
        df = fetch_candles("EURUSDT")
        if df is not None and len(df) > 25:
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            curr_candle_time = latest['epoch']

            if curr_candle_time != last_signaled_candle:
                close = latest['close']
                
                # Condition 1: Bollinger Bands Breakout OR EMA Crossover
                call_bb = close <= latest['lower_band']
                call_ema = (prev['ema_fast'] <= prev['ema_slow']) and (latest['ema_fast'] > latest['ema_slow'])
                
                put_bb = close >= latest['upper_band']
                put_ema = (prev['ema_fast'] >= prev['ema_slow']) and (latest['ema_fast'] < latest['ema_slow'])

                if call_bb or call_ema:
                    msg = f"🟢 *BINARY CALL (BUY) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time
                elif put_bb or put_ema:
                    msg = f"🔴 *BINARY PUT (SELL) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time

        time.sleep(10)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(10)
