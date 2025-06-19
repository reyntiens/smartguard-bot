# smartguard_ai_bot.py

from flask import Flask, request
import requests
import time
import hashlib
import hmac
import uuid
import json
import config
import math

app = Flask(__name__)

def sha256_hex(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def get_price(symbol):
    url = f"{config.BASE_URL}/api/v1/futures/market/ticker?symbol={symbol}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return float(response.json()["data"]["lastPrice"])
        else:
            print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[‼️] Prijs ophalen fout: {e}")
        return None

def sign_request(body_str, nonce, timestamp, api_key, secret_key, query_string=""):
    digest_input = nonce + timestamp + api_key + query_string + body_str
    digest = sha256_hex(digest_input)
    sign = sha256_hex(digest + secret_key)

    print("== 🔐 Signature Debug ==")
    print(f"Nonce: {nonce}")
    print(f"Timestamp: {timestamp}")
    print(f"Query string: {query_string}")
    print(f"Body (JSON): {body_str}")
    print(f"Digest input: {digest_input}")
    print(f"Digest: {digest}")
    print(f"Sign input: {digest + secret_key}")
    print(f"Signature: {sign}")
    print("========================")

    return sign

def place_order(signal_type):
    price = get_price(config.SYMBOL)
    if not price:
        print("[❌] Kan prijs niet ophalen, order afgebroken.")
        return

    # Bereken volume in coins (afronden naar boven, geen decimalen)
    volume = math.ceil(config.STAKE_EURO / price)
    if volume < config.MIN_VOLUME:
        volume = config.MIN_VOLUME

    payload = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT
    }

    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time() * 1000))
    body_str = json.dumps(payload, separators=(',', ':'))

    sign = sign_request(body_str, nonce, timestamp, config.API_KEY, config.API_SECRET)

    headers = {
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign,
        "Content-Type": "application/json"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, data=body_str, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print(f"[✅] Order succesvol geplaatst: {result}")
            else:
                print(f"[❌] Fout bij order: {result}")
        else:
            print(f"[❌] HTTP fout: {response.status_code}")
    except Exception as e:
        print(f"[‼️] Netwerkfout: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'signal' not in data:
        return "Ongeldig verzoek", 400

    signal = data['signal']
    if signal == 'buy':
        place_order("buy")
    elif signal == 'sell':
        place_order("sell")
    else:
        return "Ongeldig signaal", 400

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)


