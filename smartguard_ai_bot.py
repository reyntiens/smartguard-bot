# smartguard_ai_bot.py

from flask import Flask, request
import requests
import time
import hashlib
import random
import string
import config
import json

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256_hex(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def sign_request(nonce, timestamp, api_key, query_params, body, secret_key):
    digest = sha256_hex(nonce + timestamp + api_key + query_params + body)
    sign = sha256_hex(digest + secret_key)
    return sign

def place_order(signal_type, price):
    url = f"{config.BASE_URL}/api/v1/futures/order/place"

    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT,
    }

    query_params = ""  # geen query params
    body_str = json.dumps(payload, separators=(',', ':'))  # zonder spaties!

    sign = sign_request(nonce, timestamp, config.API_KEY, query_params, body_str, config.API_SECRET)

    headers = {
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign,
        "Content-Type": "application/json"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200:
            print(f"[❌] Fout bij {signal_type.upper()} openen: {response.text}")
        else:
            print(f"[✅] Order geplaatst: {response.json()}")
    except Exception as e:
        print(f"[‼️] Netwerkfout: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'signal' not in data:
        return "Ongeldig verzoek", 400

    signal = data['signal']
    price = data.get('price', 0)

    if signal == 'buy':
        place_order("buy", price)
    elif signal == 'sell':
        place_order("sell", price)
    else:
        return "Ongeldig signaal", 400

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)



