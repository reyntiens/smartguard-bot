import hmac
import hashlib
import time
import requests
from flask import Flask, request, jsonify
from datetime import datetime
from config import (
    API_KEY, API_SECRET,
    BOT_TOKEN, TELEGRAM_CHAT_ID,
    STAKE_EURO, LEVERAGE,
    STOP_LOSS_PERCENT, TAKE_PROFIT_PERCENT,
    TRAILING_BUFFER_PERCENT
)

app = Flask(__name__)
BASE_URL = "https://contract.bitunix.com"


# === STATUS ===
position_long = None
position_short = None
entry_price_long = None
entry_price_short = None
peak_price_long = None
peak_price_short = None


def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})


def log(msg):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] {msg}")
    send_telegram(msg)


def sign(params):
    sorted_params = sorted(params.items())
    encoded = "&".join([f"{k}={v}" for k, v in sorted_params])
    return hmac.new(API_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()


def place_order(side, price):
    vol = round((STAKE_EURO * LEVERAGE) / price, 2)
    position_side = 1 if side == "buy" else 2
    payload = {
        "symbol": "BRETTUSDT",
        "vol": vol,
        "leverage": LEVERAGE,
        "side": 1 if side == "buy" else 2,
        "order_type": 1,
        "position_side": position_side,
        "timestamp": int(time.time() * 1000),
    }
    payload["sign"] = sign(payload)

    headers = {"ApiKey": API_KEY, "Content-Type": "application/json"}
    url = f"{BASE_URL}/api/v1/private/futures/order/create"
    log(f"📤 Plaats order ({side.upper()}): {url} | Payload: {payload}")
    response = requests.post(url, json=payload, headers=headers)

    try:
        result = response.json()
        log(f"📥 Antwoord van Bitunix: {response.status_code} - {result}")
        return result
    except:
        log(f"📥 Antwoord van Bitunix: {response.status_code} - {response.text}")
        return {"code": -1, "msg": "Geen JSON antwoord"}


@app.route('/webhook', methods=['POST'])
def webhook():
    global position_long, position_short
    global entry_price_long, entry_price_short
    global peak_price_long, peak_price_short

    data = request.json
    action = data.get("action")
    price = float(data.get("price"))

    if position_long:
        pnl = (price - entry_price_long) / entry_price_long * 100
        drawdown = (peak_price_long - price) / peak_price_long * 100
        if price > peak_price_long:
            peak_price_long = price
        if pnl >= TAKE_PROFIT_PERCENT and drawdown >= TRAILING_BUFFER_PERCENT:
            winst = pnl / 100 * STAKE_EURO
            log(f"🏁 LONG gesloten @ ${price:.5f} | PnL: {pnl:.2f}% | Winst: €{winst:.2f} (TP)")
            position_long = None
        elif pnl <= -STOP_LOSS_PERCENT:
            verlies = pnl / 100 * STAKE_EURO
            log(f"❌ LONG gestopt @ ${price:.5f} | PnL: {pnl:.2f}% | Verlies: €{verlies:.2f} (SL)")
            position_long = None

    if position_short:
        pnl = (entry_price_short - price) / entry_price_short * 100
        drawdown = (price - peak_price_short) / peak_price_short * 100
        if price < peak_price_short:
            peak_price_short = price
        if pnl >= TAKE_PROFIT_PERCENT and drawdown >= TRAILING_BUFFER_PERCENT:
            winst = pnl / 100 * STAKE_EURO
            log(f"🏁 SHORT gesloten @ ${price:.5f} | PnL: {pnl:.2f}% | Winst: €{winst:.2f} (TP)")
            position_short = None
        elif pnl <= -STOP_LOSS_PERCENT:
            verlies = pnl / 100 * STAKE_EURO
            log(f"❌ SHORT gestopt @ ${price:.5f} | PnL: {pnl:.2f}% | Verlies: €{verlies:.2f} (SL)")
            position_short = None

    if action == "buy" and not position_long:
        result = place_order("buy", price)
        if isinstance(result, dict) and result.get("code") == 0:
            position_long = True
            entry_price_long = price
            peak_price_long = price
            log(f"🚀 OPEN LONG @ ${price:.5f} (€{STAKE_EURO}, x{LEVERAGE})")
        else:
            log(f"❌ Fout bij LONG openen: {result}")

    if action == "sell" and not position_short:
        result = place_order("sell", price)
        if isinstance(result, dict) and result.get("code") == 0:
            position_short = True
            entry_price_short = price
            peak_price_short = price
            log(f"🚀 OPEN SHORT @ ${price:.5f} (€{STAKE_EURO}, x{LEVERAGE})")
        else:
            log(f"❌ Fout bij SHORT openen: {result}")

    return jsonify({"status": "OK"})


if __name__ == '__main__':
    log(f"🤖 SmartGuard AI Bot gestart met €{STAKE_EURO} per positie en {LEVERAGE}x leverage.")
    app.run(port=5000)


