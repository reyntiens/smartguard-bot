# smartguard_ai_bot.py
from flask import Flask, request
import requests
import time
import hashlib
import uuid
import json
import config

app = Flask(__name__)

def generate_signature(nonce, timestamp, api_key, query_params, body, api_secret):
    # Stap 1: Digest maken
    digest_input = nonce + timestamp + api_key + query_params + body
    digest = hashlib.sha256(digest_input.encode('utf-8')).hexdigest()
    # Stap 2: Final sign
    sign_input = digest + api_secret
    sign = hashlib.sha256(sign_input.encode('utf-8')).hexdigest()
    return sign

def place_order(signal_type, price):
    url = f"{config.BASE_URL}/api/v1/futures/order/place"

    body_dict = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT
    }

    body_str = json.dumps(body_dict, separators=(',', ':'))  # ⚠️ Geen spaties!
    query_string = ""  # Geen query parameters hier
    nonce = uuid.uuid4().hex[:32]
    timestamp = str(int(time.time() * 1000))

    sign = generate_signature(nonce, timestamp, config.API_KEY, query_string, body_str, config.API_SECRET)

    headers = {
        "api-key": config.API_KEY,
        "sign": sign,
        "nonce": nonce,
        "timestamp": timestamp,
        "Content-Type": "application/json"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {body_dict}")
    try:
        response = requests.post(url, headers=headers, data=body_str)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200 or "code" in response.json() and response.json()["code"] != 0:
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


