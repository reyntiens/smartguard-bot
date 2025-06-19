import hmac
import hashlib
import time
import json
from flask import Flask, request
import requests
import config  # <-- we halen info uit config.py

app = Flask(__name__)

def generate_signature(payload, secret):
    sorted_payload = sorted(payload.items())
    encoded = "&".join(f"{k}={v}" for k, v in sorted_payload)
    return hmac.new(secret.encode(), encoded.encode(), hashlib.sha256).hexdigest()

def place_order(order_type, price):
    url = f"{config.BASE_URL}/api/v1/private/futures/order/create"
    timestamp = int(time.time() * 1000)

    side = 1 if order_type == "buy" else 2
    position_side = 1 if order_type == "buy" else 2

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": side,
        "order_type": 1,
        "position_side": position_side,
        "timestamp": timestamp
    }

    sign = generate_signature(payload, config.API_SECRET)
    payload["sign"] = sign

    headers = {
        "Content-Type": "application/json",
        "ApiKey": config.API_KEY
    }

    print(f"[📤] Plaats order ({order_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        return response.json()
    except Exception as e:
        print(f"[❌] Fout bij {order_type.upper()} openen: {e}")
        return None

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data or "signal" not in data:
        return "Ongeldig verzoek", 400

    signal = data["signal"]
    price = data.get("price", 0)

    if signal == "buy":
        place_order("buy", price)
    elif signal == "sell":
        place_order("sell", price)
    else:
        return "Ongeldig signaal", 400

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)


