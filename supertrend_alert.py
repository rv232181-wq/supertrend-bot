from SmartApi import SmartConnect
import pyotp
import pandas as pd
import pandas_ta as ta
from datetime import datetime
import requests
import time

# ================= TELEGRAM SETTINGS =================
BOT_TOKEN = "8293457475:AAGOL4NOyvWy_6FGbeD_5nA3ndDbbXcQ00Y"
CHAT_ID = "8500636016"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)

# ================= ANGEL ONE LOGIN =================
api_key = "2Cno0972"
client_id = "M730626"
password = "3316"
totp_key = "2ARHIZBFVW32WILAGQTF6W6VWA"

totp = pyotp.TOTP(totp_key).now()
obj = SmartConnect(api_key)
session = obj.generateSession(client_id, password, totp)

print("Login Successful")

send_telegram("✅ Supertrend Index Bot Started")

# ================= INDEX LIST =================
symbols = {
    "NIFTY": "26000",
    "BANKNIFTY": "26009",
    "FINNIFTY": "26037",
    "MIDCPNIFTY": "26121",
    "SENSEX": "1"
}

# ================= SIGNAL MEMORY =================
last_signal = {
    "NIFTY": None,
    "BANKNIFTY": None,
    "FINNIFTY": None,
    "MIDCPNIFTY": None,
    "SENSEX": None
}

# ================= MARKET TIME =================
market_open = datetime.strptime("09:15", "%H:%M").time()
market_close = datetime.strptime("15:30", "%H:%M").time()

# ================= CANDLE SYNC =================
def wait_for_next_candle():
    now = datetime.now()
    seconds_passed = (now.minute % 5) * 60 + now.second
    sleep_time = 300 - seconds_passed
    print("Waiting for candle close...")
    time.sleep(sleep_time)

# ================= MAIN LOOP =================
while True:

    try:

        now = datetime.now().time()

        if now < market_open or now > market_close:
            print("Market closed — waiting...")
            time.sleep(300)
            continue

        wait_for_next_candle()

        today = datetime.now().strftime("%Y-%m-%d")

        for symbol, token in symbols.items():

            params = {
                "exchange": "NSE",
                "symboltoken": token,
                "interval": "FIVE_MINUTE",
                "fromdate": today + " 09:15",
                "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
            }

            candles = obj.getCandleData(params)

            if candles is None or candles.get("data") is None:
                print(symbol, "No candle data")
                continue

            data = candles["data"]

            df = pd.DataFrame(
                data,
                columns=["time","open","high","low","close","volume"]
            )

            df["open"] = pd.to_numeric(df["open"])
            df["high"] = pd.to_numeric(df["high"])
            df["low"] = pd.to_numeric(df["low"])
            df["close"] = pd.to_numeric(df["close"])
            df["volume"] = pd.to_numeric(df["volume"])

            # ===== SUPERTREND =====
            st = ta.supertrend(
                df["high"],
                df["low"],
                df["close"],
                length=40,
                multiplier=3
            )

            df = pd.concat([df, st], axis=1)

            last = df.iloc[-1]
            prev = df.iloc[-2]

            print("Checking:", symbol, datetime.now())

            # ===== BUY SIGNAL =====
            if prev["SUPERTd_40_3"] == -1 and last["SUPERTd_40_3"] == 1:

                if last_signal[symbol] != "BUY":

                    msg = f"""
🚀 SUPERTREND BUY

Index: {symbol}
Price: {last['close']}
Time: {datetime.now().strftime("%H:%M")}
"""

                    print(msg)
                    send_telegram(msg)

                    last_signal[symbol] = "BUY"

            # ===== SELL SIGNAL =====
            elif prev["SUPERTd_40_3"] == 1 and last["SUPERTd_40_3"] == -1:

                if last_signal[symbol] != "SELL":

                    msg = f"""
🔻 SUPERTREND SELL

Index: {symbol}
Price: {last['close']}
Time: {datetime.now().strftime("%H:%M")}
"""

                    print(msg)
                    send_telegram(msg)

                    last_signal[symbol] = "SELL"

            else:
                print(symbol, "No new signal")

    except Exception as e:
        print("Error:", e)
        time.sleep(60)