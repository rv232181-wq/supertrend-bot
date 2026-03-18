import requests
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
from SmartApi import SmartConnect
import pyotp

# ==============================
# CONFIG
# ==============================

API_KEY = "XUbkTXuh"
CLIENT_ID = "M730626"
PASSWORD = "3316"
TOTP_SECRET = "2ARHIZBFVW32WILAGQTF6W6VWA"

BOT_TOKEN = "8293457475:AAGOL4NOyvWy_6FGbeD_5nA3ndDbbXcQ00Y"
CHAT_ID = "8500636016"

symbols = {
    "NIFTY": "26000",
}

last_signal = {}
obj = None


# ==============================
# TELEGRAM
# ==============================

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print("Telegram Error:", e)


# ==============================
# LOGIN (AUTO RETRY)
# ==============================

def login():
    global obj
    try:
        totp = pyotp.TOTP(TOTP_SECRET).now()
        obj = SmartConnect(api_key=API_KEY)
        obj.generateSession(CLIENT_ID, PASSWORD, totp)
        print("Login Successful")
    except Exception as e:
        print("Login Error:", e)
        time.sleep(5)
        login()


# ==============================
# GET CANDLES (FIXED)
# ==============================

def get_candles(token):
    try:
        todate = datetime.now().strftime("%Y-%m-%d %H:%M")
        fromdate = datetime.now().strftime("%Y-%m-%d 09:15")

        params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": fromdate,
            "todate": todate
        }

        data = obj.getCandleData(params)

        # 🔥 TOKEN EXPIRED FIX
        if data.get("status") is False and "Invalid Token" in str(data):
            print("Session expired → Re-login...")
            login()
            time.sleep(2)
            data = obj.getCandleData(params)

        # 🔥 RATE LIMIT FIX
        if "Access denied" in str(data):
            print("Rate limit hit → sleeping 10 sec...")
            time.sleep(10)
            return None

        if not data.get("data"):
            return None

        df = pd.DataFrame(data["data"])
        df.columns = ["time", "open", "high", "low", "close", "volume"]

        return df

    except Exception as e:
        print("Candle Error:", e)
        return None


# ==============================
# SUPERTREND SIGNAL
# ==============================

def check_signal(symbol, token):
    df = get_candles(token)

    # 🔥 FIX NoneType crash
    if df is None or len(df) < 2:
        return

    try:
        df["SUPERT"] = ta.supertrend(
            df["high"],
            df["low"],
            df["close"],
            length=10,
            multiplier=3
        )["SUPERTd_10_3.0"]

        prev = df.iloc[-2]
        last = df.iloc[-1]

        # BUY
        if prev["SUPERT"] == -1 and last["SUPERT"] == 1:
            if last_signal.get(symbol) != "BUY":
                msg = f"✅ BUY SIGNAL\n{symbol}\nPrice: {last['close']}"
                print(msg)
                send_telegram(msg)
                last_signal[symbol] = "BUY"

        # SELL
        elif prev["SUPERT"] == 1 and last["SUPERT"] == -1:
            if last_signal.get(symbol) != "SELL":
                msg = f"❌ SELL SIGNAL\n{symbol}\nPrice: {last['close']}"
                print(msg)
                send_telegram(msg)
                last_signal[symbol] = "SELL"

    except Exception as e:
        print("Signal Error:", e)


# ==============================
# MARKET TIME
# ==============================

def market_open():
    now = datetime.now().time()
    start = datetime.strptime("09:15", "%H:%M").time()
    end = datetime.strptime("15:30", "%H:%M").time()
    return start <= now <= end


# ==============================
# MAIN LOOP
# ==============================

login()
print("🚀 Supertrend bot is running...")

while True:
    try:
        print(f"🟢 Bot alive at {datetime.now()}")

        if not market_open():
            print("Market closed — sleeping...")
            time.sleep(300)
            continue

        print("Checking signals...")

        for symbol, token in symbols.items():
            check_signal(symbol, token)

        print("Waiting for next candle...")
        time.sleep(60)  # 🔥 reduced to avoid rate limit

    except Exception as e:
        print("Main Loop Error:", e)
        time.sleep(10)
