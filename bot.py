import os
from flask import Flask, request
import requests

app = Flask(__name__)

TOKEN = os.environ.get("BALE_TOKEN", "546304737:3dWovOidcSZK6SPZbwzjspTZlUwA32MUU0E")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return "Webhook endpoint is active!", 200
        
    data = request.get_json(silent=True)
    if data and "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if text == "/start":
            send_message(chat_id, "سلام کیا جان! به ربات ممبرگیر خوش آمدید. 🚀")
        else:
            send_message(chat_id, f"پیام شما دریافت شد: {text}")
            
    return "OK", 200

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

@app.route("/", methods=["GET"])
def home():
    return "Bale Bot is running!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
