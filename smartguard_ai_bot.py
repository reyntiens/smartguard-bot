from flask import Flask, request
import requests
import time
import hashlib
import hmac
import json
import random
import string
import config

app = Flask(__name__)

def generate_nonce(length=32):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def sha256_hex(data):
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def get_price(symbol):
    try:
        url = f"{config.BASE_URL}/api/v1/futures/market/trade?symbol={symbol}"
        response = requests.get(url)
        result = response.json()
        return float(result['data']['price'])
    except:
        return None

def create_signature(nonce, timestamp, body):
    digest_input = nonce + timestamp + config.API_KEY + "" + body
    digest = sha256_hex(digest_input)
    sign_input = digest + config.API_SECRET
    return sha256_hex(sign_input)

def calculate_volume(price):
    volume = config.STAKE_USD / price
    volume = int(volume)  # basePrecision = 0, dus afronden naar integer
    return max(volume, 70)  # Bitunix vereist minTradeVolume = 70

def place_order(signal_type):
    price = get_price(config.SYMBOL)
    if not price:
        print("[❌] Prijs ophalen mislukt")
        return

    volume = calculate_volume(price)
    side = 1 if signal_type == "buy" else 2
    position_side = config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT

    body_dict = {
        "symbol": config.SYMBOL,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": side,
        "order_type": config.ORDER_TYPE,
        "position_side": position_side
    }

    body_json = json.dumps(body_dict, separators=(',', ':'))
    nonce = generate_nonce()
    timestamp = str(int(time.time() * 1000))
    signature = create_signature(nonce, timestamp, body_json)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": signature
    }

    url = f"{config.BASE_URL}/api/v1/futures/trade/place_order"
    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {body_dict}")
    try:
        response = requests.post(url, headers=headers, data=body_json)
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






