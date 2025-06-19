# smartguard_ai_bot.py

from flask import Flask, request
import requests
import time
import hashlib
import json
import uuid
import config

app = Flask(__name__)

def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_signature(payload: dict, query_params: str = "") -> tuple:
    nonce = uuid.uuid4().hex[:32]
    timestamp = str(int(time.time() * 1000))
    body_str = json.dumps(payload, separators=(',', ':'))  # géén spaties!

    digest_input = nonce + timestamp + config.API_KEY + query_params + body_str
    digest = sha256_hex(digest_input)
    sign = sha256_hex(digest + config.API_SECRET)

    return sign, nonce, timestamp

def place_order(signal_type: str):
    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT
    }

    sign, nonce, timestamp = generate_signature(payload)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "sign": sign,
        "nonce": nonce,
        "timestamp": timestamp,
        "language": "en-US"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code == 200 and '"code":0' in response.text:
            print(f"[✅] Order geplaatst: {response.json()}")
        else:
            print(f"[❌] Fout bij {signal_type.upper()} openen: {response.text}")
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




