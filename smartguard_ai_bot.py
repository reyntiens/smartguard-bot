from flask import Flask, request
import requests
import time
import hashlib
import json
import secrets
import config

app = Flask(__name__)

def sha256_hex(input_string):
    return hashlib.sha256(input_string.encode('utf-8')).hexdigest()

def sign_payload(payload_dict, query_params_dict):
    # 1. Genereer nonce en timestamp
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time() * 1000))

    # 2. Sort query params (leeg in dit geval, maar laat staan voor uitbreidbaarheid)
    query_string = ''.join(f"{k}{v}" for k, v in sorted(query_params_dict.items()))

    # 3. Maak body json string zonder spaties
    body = json.dumps(payload_dict, separators=(',', ':'))

    # 4. SHA256(nonce + timestamp + api-key + queryParams + body)
    digest_input = nonce + timestamp + config.API_KEY + query_string + body
    digest = sha256_hex(digest_input)

    # 5. SHA256(digest + secretKey)
    sign_input = digest + config.API_SECRET
    signature = sha256_hex(sign_input)

    return nonce, timestamp, signature

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

    query_params = {}  # indien nodig in toekomst
    nonce, timestamp, signature = sign_payload(payload, query_params)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": signature,
        "language": "en-US"
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200 or response.json().get("code") != 0:
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




