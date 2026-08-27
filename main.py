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
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram Error:", e)

# --- BOLLINGER BANDS INDICATOR ---
def get_bollinger_bands(df, window=20, std_dev=2):
    df['sma'] = df['close'].rolling(window=window).mean()
    df['std'] = df['close'].rolling(window=window).std()
    df['upper_band'] = df['sma'] + (df['std'] * std_dev)
    df['lower_band'] = df['sma'] - (df['std'] * std_dev)
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
            return get_bollinger_bands(df)
    except Exception as e:
        print("Data Fetch Error:", e)
    return None

# --- MAIN LOOP ---
print("Bot Started...")
send_telegram("🔥 *Nafi Power Trading Bot (Bollinger Bands) Active!*")

last_signaled_candle = 0

while True:
    try:
        df = fetch_candles("EURUSDT")
        if df is not None and len(df) > 25:
            latest = df.iloc[-1]
            curr_candle_time = latest['epoch']

            if curr_candle_time != last_signaled_candle:
                close_price = latest['close']
                upper = round(latest['upper_band'], 5)
                lower = round(latest['lower_band'], 5)

                # CALL SIGNAL: Price touches or goes below Lower Band
                if close_price <= latest['lower_band']:
                    msg = f"🟢 *STRONG CALL (BUY) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close_price}\n🎯 Lower Band: {lower}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time

                # PUT SIGNAL: Price touches or goes above Upper Band
                elif close_price >= latest['upper_band']:
                    msg = f"🔴 *STRONG PUT (SELL) SIGNAL*\n📌 Asset: EUR/USD\n⏱ Expiry: 1 MIN\n📊 Price: {close_price}\n🎯 Upper Band: {upper}"
                    send_telegram(msg)
                    last_signaled_candle = curr_candle_time

        time.sleep(10)
    except Exception as e:
        print("Loop Error:", e)
        time.sleep(10)
