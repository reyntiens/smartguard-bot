from flask import Flask, request, jsonify
import time
import uuid
import hashlib
import hmac
import requests
import json
import config

app = Flask(__name__)

# === Helperfuncties ===
def get_server_timestamp():
    return str(int(time.time() * 1000))

def generate_nonce():
    return uuid.uuid4().hex

def generate_signature(nonce, timestamp, api_key, body):
    digest_input = f"{nonce}{timestamp}{api_key}{body}"
    digest = hashlib.sha256(digest_input.encode()).hexdigest()
    sign_input = digest + config.API_SECRET
    sign = hashlib.sha256(sign_input.encode()).hexdigest()
    return sign

def get_price(symbol):
    url = f"{config.BASE_URL}/api/v1/futures/market/get_ticker?symbol={symbol}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0 and data.get("data"):
                return float(data["data"]["lastPrice"])
            else:
                print(f"[❌] Ongeldige data: {data}")
        else:
            print(f"[❌] Prijs ophalen mislukt: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[❌] Fout bij prijs ophalen: {e}")
    return 0

def calculate_volume(price_usdt, coin_price):
    return round(price_usdt / coin_price, 2)

def place_order(signal_type):
    symbol = config.SYMBOL
    side = 1 if signal_type == "buy" else 2
    position_side = 1 if signal_type == "buy" else 2
    price = get_price(symbol)
    if price == 0:
        print("[❌] Kan prijs niet ophalen of prijs is nul, order afgebroken.")
        return

    volume = calculate_volume(config.QUANTITY, price)
    print(f"[📊] Coin prijs: {price:.5f} USDT, Volume berekend: {volume}")

    payload = {
        "symbol": symbol,
        "vol": volume,
        "leverage": config.LEVERAGE,
        "side": side,
        "order_type": 1,
        "position_side": position_side
    }

    json_payload = json.dumps(payload, separators=(',', ':'))
    nonce = generate_nonce()
    timestamp = get_server_timestamp()
    sign = generate_signature(nonce, timestamp, config.API_KEY, json_payload)

    headers = {
        "Content-Type": "application/json",
        "api-key": config.API_KEY,
        "nonce": nonce,
        "timestamp": timestamp,
        "sign": sign,
        "language": "en-US"
    }

    print(f"🔍 Digest input: {nonce}{timestamp}{config.API_KEY}{json_payload}")
    print(f"🔍 Headers: {headers}")
    print(f"[📤] Plaats order ({signal_type.upper()}): {config.BASE_URL}/api/v1/futures/trade/place_order | Payload: {payload}")

    try:
        response = requests.post(f"{config.BASE_URL}/api/v1/futures/trade/place_order", headers=headers, data=json_payload)
        response_data = response.json()
        print(f"[📥] Antwoord van Bitunix: {response.status_code} - {response_data}")
        if response_data.get("code") == 0:
            print(f"[✅] {signal_type.upper()} order succesvol geplaatst!")
        else:
            print(f"[❌] Fout bij {signal_type.upper()} openen: {response_data}")
    except Exception as e:
        print(f"[❌] Fout bij uitvoeren van order: {e}")


# === Webhook endpoint voor TradingView ===
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json
        print(f"[🔔] Webhook ontvangen: {data}")

        if "buy" in data.get("message", "").lower():
            place_order("buy")
        elif "sell" in data.get("message", "").lower():
            place_order("sell")
        else:
            print("[⚠️] Geen geldig signaal in webhook.")

        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"[❌] Webhook verwerkingsfout: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/")
def home():
    return "SmartGuard AI Bot draait ✔️"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)




