import requests
import json
import time
import random
import string
from hashlib import sha256
from flask import Flask, request
import config

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256_hex(s):
    return sha256(s.encode('utf-8')).hexdigest()

def get_price(symbol):
    url = f"{config.BASE_URL}/api/v1/futures/market/ticker?symbol={symbol}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return float(data['data']['last']) if 'data' in data and 'last' in data['data'] else None
    else:
        print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
        return None

def sign_request(nonce, timestamp, query_params, body_json):
    body_str = json.dumps(body_json, separators=(',', ':'))
    digest_input = f"{nonce}{timestamp}{config.API_KEY}{query_params}{body_str}"
    digest = sha256_hex(digest_input)
    sign_input = digest + config.API_SECRET
    signature = sha256_hex(sign_input)

    print("== 🔐 Signature Debug ==")
    print(f"Nonce: {nonce}")
    print(f"Timestamp: {timestamp}")
    print(f"Query string: {query_params}")
    print(f"Body (JSON): {body_str}")
    print(f"Digest input: {digest_input}")
    print(f"Digest: {digest}")
    print(f"Sign input: {sign_input}")
    print(f"Signature: {signature}")
    print("========================")

    return signature

def place_order(side):
    price = get_price(config.SYMBOL)
    if price is None:
        print("[❌] Kan prijs niet ophalen, order afgebroken.")
        return

    volume = round(config.STAKE_EURO / price)
    if volume < 1:
        volume = 1

    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    body = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": 1 if side == "buy" else 2,
        "order_type": 1,
        "position_side": 1 if side == "buy" else 2
    }

    signature = sign_request(nonce, timestamp, "", body)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": signature
    }

    print(f"[📤] Plaats order ({side.upper()}): {url} | Payload: {body}")
    response = requests.post(url, json=body, headers=headers)
    print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")

    if response.status_code == 200 and response.json().get("code") == 0:
        print(f"[✅] Order geplaatst: {response.json()}")
    else:
        print(f"[❌] Fout bij {side.upper()} openen: {response.json()}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or 'signal' not in data:
        return "Ongeldig verzoek", 400

    signal = data['signal']
    if signal == "buy":
        place_order("buy")
    elif signal == "sell":
        place_order("sell")
    else:
        return "Ongeldig signaal", 400

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)




