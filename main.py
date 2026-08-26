from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web, daemon=True).start()
import time
import requests
import pandas as pd
import numpy as np

# --- TELEGRAM CONFIG ---
BOT_TOKEN = "758337374:AAEWM-sRhg0nAUTSnCP0xodU7S-hm7mHIkw"
CHAT_ID = "6764734331"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

# --- INDICATORS CALCULATION ---
def get_indicators(df):
    # RSI (14)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands (20, 2)
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std'] = df['close'].rolling(window=20).std()
    df['upper_bb'] = df['sma20'] + (df['std'] * 2)
    df['lower_bb'] = df['sma20'] - (df['std'] * 2)

    # Stochastic Oscillator (5,3,3)
    low_min = df['low'].rolling(window=5).min()
    high_max = df['high'].rolling(window=5).max()
    df['stoch_k'] = 100 * ((df['close'] - low_min) / (high_max - low_min))
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

    return df

# --- FETCH CANDLE DATA FROM DERIV API ---
def fetch_candles(symbol="frxEURUSD"):
    url = f"https://api.deriv.com/api/v1/candles?symbol={symbol}&granularity=60&count=50"
    try:
        res = requests.get(url).json()
        if "candles" in res:
            df = pd.DataFrame(res["candles"])
            return get_indicators(df)
    except Exception as e:
        print("Data Error:", e)
    return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("🚀 *Binary Option Signal Bot Active!*")

last_signal_time = 0

while True:
    try:
        df = fetch_candles()
        if df is not None and len(df) > 2:
            latest = df.iloc[-1]
            prev = df.iloc[-2]

            # Signal Conditions
            call_cond = (latest['close'] <= latest['lower_bb']) and (latest['rsi'] < 30) and (latest['stoch_k'] < 20)
            put_cond = (latest['close'] >= latest['upper_bb']) and (latest['rsi'] > 70) and (latest['stoch_k'] > 80)

            curr_time = latest['epoch']
            if curr_time != last_signal_time:
                if call_cond:
                    msg = f"🟢 *BINARY CALL SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n🎯 Pattern: Oversold Reversal"
                    send_telegram(msg)
                    last_signal_time = curr_time
                elif put_cond:
                    msg = f"🔴 *BINARY PUT SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n🎯 Pattern: Overbought Reversal"
                    send_telegram(msg)
                    last_signal_time = curr_time

        time.sleep(10)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(10)
