from flask import Flask, request
import requests
import time
import hashlib
import hmac
import random
import string
import json
import config

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256_hex(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def get_price(symbol):
    url = f"{config.BASE_URL}/api/v1/futures/market/ticker?symbol={symbol}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return float(data['data']['last']) if 'data' in data else None
        else:
            print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[‼️] Netwerkfout bij prijs ophalen: {e}")
        return None

def calculate_signature(nonce, timestamp, api_key, query_string, body, secret_key):
    digest_input = nonce + timestamp + api_key + query_string + body
    digest = sha256_hex(digest_input)
    sign_input = digest + secret_key
    sign = sha256_hex(sign_input)
    return sign

def place_order(signal_type):
    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))
    
    price = get_price(config.SYMBOL)
    if not price:
        print("[❌] Kan prijs niet ophalen, order afgebroken.")
        return

    volume = round(config.STAKE_EURO / price, config.BASE_PRECISION)

    payload = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT
    }

    body = json.dumps(payload, separators=(',', ':'))
    query_string = ""
    sign = calculate_signature(nonce, timestamp, config.API_KEY, query_string, body, config.API_SECRET)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign
    }

    print(f"== 🔐 Signature Debug ==\nNonce: {nonce}\nTimestamp: {timestamp}\nQuery string: {query_string}\nBody (JSON): {body}")
    print(f"Digest input: {nonce + timestamp + config.API_KEY + query_string + body}")
    print(f"Sign: {sign}\n========================")
    
    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, headers=headers, data=body)
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



