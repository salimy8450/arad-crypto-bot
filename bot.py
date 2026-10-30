
import os
import time
import requests
from datetime import datetime, timezone

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN secret is missing")

TG = f"https://api.telegram.org/bot{TOKEN}"
BINANCE = "https://api.binance.com"

SYMBOLS = [
    "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "BONKUSDT",
    "WIFUSDT", "FLOKIUSDT", "BOMEUSDT", "MEMEUSDT"
]

def get(url, params=None):
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok", True):
        raise RuntimeError(str(data))
    return data

def ema(values, period):
    if len(values) < period:
        return None
    result = sum(values[:period]) / period
    k = 2 / (period + 1)
    for value in values[period:]:
        result = value * k + result * (1 - k)
    return result

def rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]
    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100
    return 100 - (100 / (1 + avg_gain / avg_loss))

def candles(symbol, interval):
    raw = get(
        BINANCE + "/api/v3/klines",
        {"symbol": symbol, "interval": interval, "limit": 100}
    )
    raw = raw[:-1]  # حذف کندل باز
    return [
        {
            "o": float(x[1]),
            "h": float(x[2]),
            "l": float(x[3]),
            "c": float(x[4]),
            "v": float(x[5])
        }
        for x in raw
    ]

def analyze(symbol):
    candles_15m = candles(symbol, "15m")
    candles_1h = candles(symbol, "1h")

    x = [c["c"] for c in candles_15m]
    y = [c["c"] for c in candles_1h]

    e21 = ema(x, 21)
    e50 = ema(x, 50)
    e21h = ema(y, 21)
    e50h = ema(y, 50)

    r15 = rsi(x)
    r1h = rsi(y)

    if None in (e21, e50, e21h, e50h, r15, r1h):
        return None

    true_ranges = []
    for i in range(1, len(candles_15m)):
        current = candles_15m[i]
        previous_close = candles_15m[i - 1]["c"]
        true_ranges.append(max(
            current["h"] - current["l"],
            abs(current["h"] - previous_close),
            abs(current["l"] - previous_close)
        ))

    atr = sum(true_ranges[-14:]) / 14
    if atr <= 0:
        return None

    avg_volume = sum(c["v"] for c in candles_15m[-15:-1]) / 14
    volume_ratio = candles_15m[-1]["v"] / avg_volume if avg_volume else 0
    price = x[-1]

    long_score = 0
    short_score = 0

    if e21 > e50:
        long_score += 25
    else:
        short_score += 25

    if e21h > e50h:
        long_score += 25
    else:
        short_score += 25

    if price > e21:
        long_score += 15
    else:
        short_score += 15

    if 50 <= r15 <= 68:
        long_score += 15
    elif 32 <= r15 <= 50:
        short_score += 15

    if r1h > 50:
        long_score += 10
    elif r1h < 50:
        short_score += 10

    if volume_ratio >= 1.2:
        if candles_15m[-1]["c"] > candles_15m[-1]["o"]:
            long_score += 10
        elif candles_15m[-1]["c"] < candles_15m[-1]["o"]:
            short_score += 10

    side = "LONG" if long_score >= short_score else "SHORT"
    score = max(long_score, short_score)

    aligned = (
        side == "LONG" and e21 > e50 and e21h > e50h
    ) or (
        side == "SHORT" and e21 < e50 and e21h < e50h
    )

    if not aligned or score < 75:
        return None

    if side == "LONG" and r15 >= 75:
        return None
    if side == "SHORT" and r15 <= 25:
        return None

    risk = atr * 1.5

    if side == "LONG":
        stop_loss = price - risk
        targets = [price + risk * k for k in (1, 1.5, 2, 3)]
    else:
        stop_loss = price + risk
        targets = [price - risk * k for k in (1, 1.5, 2, 3)]

    return (
        side, score, price, stop_loss,
        targets, r15, r1h, volume_ratio
    )

def fmt(value):
    return f"{value:.8f}".rstrip("0").rstrip(".")

def send_message(chat_id, message):
    response = requests.post(
        TG + "/sendMessage",
        data={"chat_id": chat_id, "text": message},
        timeout=20
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(str(result))

def main():
    print("Arad scanner started...")
    print("UTC time:", datetime.now(timezone.utc).isoformat())

    # دریافت شناسه گفتگوی تلگرام
    updates = get(TG + "/getUpdates").get("result", [])
    chat_id = None

    for update in reversed(updates):
        message = update.get("message") or update.get("edited_message")
        if message and message.get("chat", {}).get("type") == "private":
            chat_id = message["chat"]["id"]
            break

    if chat_id is None:
        raise RuntimeError(
            "Chat ID not found. Open the bot in Telegram and send /start."
        )

    signals = []

    for symbol in SYMBOLS:
        try:
            signal = analyze(symbol)
            if signal:
                signals.append((symbol, signal))
                print(symbol, "signal found")
            else:
                print(symbol, "no strong signal")
        except Exception as error:
            print(symbol, "scan error:", str(error))

        time.sleep(0.3)

    if not signals:
        send_message(
            chat_id,
            "Arad Crypto Bot\n"
            "اسکن ۸ ارز انجام شد.\n"
            "فعلاً سیگنال قوی و هم‌جهت در تایم‌فریم‌های ۱۵ دقیقه و ۱ ساعت پیدا نشد."
        )
        print("Scan completed: no strong signals.")
        return

    for symbol, signal in signals:
        side, score, price, sl, targets, r15, r1h, vr = signal

        message = (
            f"🚨 ARAD CRYPTO SIGNAL\n"
            f"{symbol} | {side}\n"
            f"Score: {score}/100\n\n"
            f"Entry: {fmt(price)}\n"
            f"TP1: {fmt(targets[0])}\n"
            f"TP2: {fmt(targets[1])}\n"
            f"TP3: {fmt(targets[2])}\n"
            f"TP4: {fmt(targets[3])}\n"
            f"SL: {fmt(sl)}\n\n"
            f"RSI 15m: {r15:.1f}\n"
            f"RSI 1h: {r1h:.1f}\n"
            f"Volume: {vr:.2f}x\n\n"
            f"ATR-based levels. Leverage not included.\n"
            f"قبل از ورود، شرایط بازار را بررسی کن."
        )

        send_message(chat_id, message)
        time.sleep(1)

    print("Scan completed. Signals sent:", len(signals))

if __name__ == "__main__":
    main()
