import os
import time
import requests

TOKEN = os.environ.get("BALE_TOKEN", "546304737:3dWovOidcSZK6SPZbwzjspTZlUwA32MUU0E")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get("result", [])
    except Exception as e:
        print(f"Error fetching updates: {e}")
    return []

def main():
    print("Bot is starting polling...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "")
                
                if text == "/start":
                    send_message(chat_id, "سلام کیا جان! ربات ممبرگیر با موفقیت روشن شد. 🚀")
                else:
                    send_message(chat_id, f"پیام شما دریافت شد: {text}")
                    
        time.sleep(1)

if __name__ == "__main__":
    main()
