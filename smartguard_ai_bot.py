# smartguard_ai_bot.py

from flask import Flask, request
import requests
import time
import json
import hashlib
import random
import string
import config

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def create_signature(payload: dict, endpoint: str):
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))
    query_string = ""  # geen query parameters voor POST
    body = json.dumps(payload, separators=(',', ':'))  # zonder spaties

    digest_input = nonce + timestamp + config.API_KEY + query_string + body
    digest = sha256(digest_input)
    sign = sha256(digest + config.API_SECRET)

    return {
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign
    }

def place_order(signal_type):
    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT
    }

    signature = create_signature(payload, "/api/v1/futures/trade/place_order")

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "sign": signature["sign"],
        "nonce": signature["nonce"],
        "timestamp": signature["timestamp"],
        "language": "en-US"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200 or '"code":10007' in response.text:
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

    if signal == 'buy':
        place_order("buy")
    elif signal == 'sell':
        place_order("sell")
    else:
        return "Ongeldig signaal", 400

    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)




