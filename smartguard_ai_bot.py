import time
import hmac
import hashlib
import requests
from flask import Flask, request
import config

app = Flask(__name__)

def log(msg):
    timestamp = time.strftime("[%H:%M:%S]")
    print(f"{timestamp} {msg}")

def generate_signature(payload, secret):
    query_string = '&'.join([f"{k}={v}" for k, v in sorted(payload.items())])
    return hmac.new(secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

def place_order(direction, price):
    url = f"{config.BASE_URL}/api/v1/private/futures/order/create"
    timestamp = int(time.time() * 1000)

    side = 1 if direction == "buy" else 2
    position_side = 1 if direction == "buy" else 2

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": side,
        "order_type": config.ORDER_TYPE,
        "position_side": position_side,
        "timestamp": timestamp
    }

    sign = generate_signature(payload, config.API_SECRET)
    payload["sign"] = sign

    headers = {
        "Content-Type": "application/json",
        "ApiKey": config.API_KEY
    }

    log(f"📤 Plaats order ({direction.upper()}): {url} | Payload: {payload}")
    response = requests.post(url, json=payload, headers=headers)
    log(f"📥 Antwoord van Bitunix: {response.status_code} - {response.text}")

    if response.status_code != 200:
        log(f"❌ Fout bij {direction.upper()} openen: {response.text}")
        return None
    return response.json()

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data is None:
        return "No data", 400

    signal = data.get("signal")
    price = data.get("price", 0)

    if signal == "buy":
        place_order("buy", price)
    elif signal == "sell":
        place_order("sell", price)
    else:
        log("⚠️ Onbekend signaal ontvangen")

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=False, port=5000)


