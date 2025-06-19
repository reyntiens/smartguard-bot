from flask import Flask, request
import requests
import time
import hashlib
import hmac
import config

app = Flask(__name__)

def sign_payload(payload, secret):
    query_string = '&'.join([f"{key}={payload[key]}" for key in sorted(payload)])
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

def place_order(signal_type, price):
   url = f"{config.BASE_URL}/api/v1/private/futures/order/create"

    payload = {
        "symbol": config.SYMBOL,
        "vol": config.VOLUME,
        "leverage": config.LEVERAGE,
        "side": 1 if signal_type == "buy" else 2,
        "order_type": config.ORDER_TYPE,
        "position_side": config.POSITION_SIDE_LONG if signal_type == "buy" else config.POSITION_SIDE_SHORT,
        "timestamp": int(time.time() * 1000)
    }
    payload["sign"] = sign_payload(payload, config.API_SECRET)

    headers = {
        "Content-Type": "application/json",
        "ApiKey": config.API_KEY
    }

    print(f"[📤] Plaats order ({signal_type.upper()}): {url} | Payload: {payload}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response.text}")
        if response.status_code != 200:
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


