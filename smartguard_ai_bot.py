import time
import uuid
import json
import hmac
import hashlib
import requests
from flask import Flask, request
import config  # Aparte config.py zoals jij gebruikt

app = Flask(__name__)

def sha256_hex(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def generate_signature(endpoint, body):
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time() * 1000))
    query_string = ""  # geen query params bij POST
    body_str = json.dumps(body, separators=(',', ':'))  # zonder spaties

    digest_input = nonce + timestamp + config.API_KEY + query_string + body_str
    digest = sha256_hex(digest_input)
    sign_input = digest + config.API_SECRET
    sign = sha256_hex(sign_input)

    headers = {
        'Content-Type': 'application/json',
        'api-key': config.API_KEY,
        'nonce': nonce,
        'timestamp': timestamp,
        'sign': sign,
        'language': 'en-US'
    }

    return headers

def get_price():
    try:
        endpoint = f"{config.BASE_URL}/api/v1/futures/market/ticker?symbol={config.SYMBOL}"
        response = requests.get(endpoint)
        if response.status_code == 200:
            data = response.json()
            return float(data['data']['last'])  # huidige prijs
        else:
            print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[❌] Fout bij prijs ophalen: {e}")
        return None

def place_order(signal):
    price = get_price()
    if price is None:
        print("[❌] Kan prijs niet ophalen, order afgebroken.")
        return

    volume = round(config.STAKE_USD / price, config.BASE_PRECISION)

    payload = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": 1 if signal == "buy" else 2,
        "order_type": 1,
        "position_side": 1 if signal == "buy" else 2
    }

    headers = generate_signature("/api/v1/futures/trade/place_order", payload)
    endpoint = f"{config.BASE_URL}/api/v1/futures/trade/place_order"

    print(f"[📤] Plaats order ({signal.upper()}): {endpoint} | Payload: {payload}")
    response = requests.post(endpoint, headers=headers, json=payload)
    try:
        response_data = response.json()
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response_data}")
        if response_data.get("code") == 0:
            print("[✅] Order succesvol geplaatst.")
        else:
            print(f"[❌] Fout bij {signal.upper()} openen: {response_data}")
    except Exception as e:
        print(f"[❌] Antwoord kon niet gelezen worden: {e}")

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    signal = data.get("signal")

    if signal == "buy":
        place_order("buy")
    elif signal == "sell":
        place_order("sell")
    else:
        print("[❌] Ongeldig signaal ontvangen.")

    return "OK", 200

if __name__ == "__main__":
    app.run(debug=True)





