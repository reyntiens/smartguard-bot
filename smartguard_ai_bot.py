from flask import Flask, request
import requests
import json
import time
import hashlib
import random
import string
import config

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256_hex(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def get_current_price():
    endpoint = f"{config.BASE_URL}/api/v1/futures/market/ticker?symbol={config.SYMBOL}"
    try:
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            return float(data["data"]["last"])
        else:
            print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[‼️] Fout bij prijs ophalen: {e}")
        return None

def calculate_volume(price):
    dollar_amount = config.STAKE_EURO
    volume = dollar_amount / price
    return max(config.MIN_VOLUME, round(volume, config.BASE_PRECISION))

def sign_request(body_json, nonce, timestamp):
    query_string = ""
    compact_body = json.dumps(body_json, separators=(',', ':'))
    digest_input = nonce + timestamp + config.API_KEY + query_string + compact_body
    digest = sha256_hex(digest_input)
    signature = sha256_hex(digest + config.API_SECRET)

    # Debug output
    print("== 🔐 Signature Debug ==")
    print(f"Nonce: {nonce}")
    print(f"Timestamp: {timestamp}")
    print(f"Query string: {query_string}")
    print(f"Body (JSON): {compact_body}")
    print(f"Digest input: {digest_input}")
    print(f"Digest: {digest}")
    print(f"Sign input: {digest + config.API_SECRET}")
    print(f"Signature: {signature}")
    print("========================")
    return signature

def place_order(signal_type):
    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))
    
    price = get_current_price()
    if price is None:
        print("[❌] Kan prijs niet ophalen, order afgebroken.")
        return

    volume = calculate_volume(price)

    body = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": 1,
        "position_side": 1 if signal_type == "buy" else 2
    }

    signature = sign_request(body, nonce, timestamp)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": signature
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {body}")
    try:
        response = requests.post(url, json=body, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200 or "code" in response.json() and response.json()["code"] != 0:
            print(f"[❌] Fout bij {signal_type.upper()} openen: {response.json()}")
        else:
            print(f"[✅] Order geplaatst: {response.json()}")
    except Exception as e:
        print(f"[‼️] Netwerkfout bij orderplaatsing: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data or 'signal' not in data:
        return "Ongeldig verzoek", 400

    signal = data['signal']
    if signal not in ['buy', 'sell']:
        return "Ongeldig signaal", 400

    place_order(signal)
    return "OK", 200

if __name__ == '__main__':
    app.run(debug=True)





