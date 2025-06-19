# smartguard_ai_bot.py

from flask import Flask, request
import requests
import time
import hashlib
import hmac
import json
import config
import random
import string

app = Flask(__name__)

def sha256_hex(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sign_request(api_key, api_secret, nonce, timestamp, query_params, body_dict):
    query_string = ''.join([f"{k}{v}" for k, v in sorted(query_params.items())]) if query_params else ""

    # Zorg dat body geen spaties bevat:
    body = json.dumps(body_dict, separators=(',', ':'))

    digest_input = nonce + timestamp + api_key + query_string + body
    digest = sha256_hex(digest_input)
    sign = sha256_hex(digest + api_secret)

    # Debugprint
    print("== 🔐 Signature Debug ==")
    print("Nonce:", nonce)
    print("Timestamp:", timestamp)
    print("Query string:", query_string)
    print("Body (JSON):", body)
    print("Digest input:", digest_input)
    print("Digest:", digest)
    print("Sign input:", digest + api_secret)
    print("Signature:", sign)
    print("========================")

    return sign, body

def place_order(signal_type):
    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"

    # Timestamp en nonce
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))

    # Payload body
    payload = {
        "symbol": config.SYMBOL,
        "vol": config.STAKE_EURO,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": 1,  # market
        "position_side": 1 if signal_type == "buy" else 2
    }

    # Signatuur berekenen
    sign, body = sign_request(config.API_KEY, config.API_SECRET, nonce, timestamp, {}, payload)

    headers = {
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign,
        "Content-Type": "application/json",
        "language": "en-US"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, headers=headers, data=body)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                print(f"[✅] Order succesvol geplaatst: {result}")
            else:
                print(f"[❌] Fout bij BUY openen: {result}")
        else:
            print(f"[❌] HTTP-fout: {response.status_code}")
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





