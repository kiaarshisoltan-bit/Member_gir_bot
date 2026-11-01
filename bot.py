import os
import time
import requests

TOKEN = os.environ.get("BALE_TOKEN", "546304737:3dWovOidcSZK6SPZbwzjspTZlUwA32MUU0E")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# دیتابیس موقت در حافظه
# ساختار: users[chat_id] = "nickname"
users_db = {}

# نگهداری وضعیت کاربرانی که در حال وارد کردن نام هستند
# ساختار: waiting_for_name[chat_id] = True
waiting_for_name = set()

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
    print("Bot is starting polling with Nickname registration...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()
                
                # ۱. اگر کاربر دستور /start را زد
                if text == "/start":
                    if chat_id in users_db:
                        # اگر قبلاً ثبت‌نام کرده بود
                        send_message(chat_id, f"سلام {users_db[chat_id]} عزیز! مجدداً خوش آمدی. 🚀\nاسم فعلی‌ات در سیستم ثبت شده.")
                    else:
                        # اگر کاربر جدید است، منتظر نام می‌شویم
                        waiting_for_name.add(chat_id)
                        send_message(chat_id, "سلام کیا جان! به ربات ممبرگیر خوش آمدید. 🚀\nلطفاً یک **نام مستعار (Nickname)** یکتا برای خودت ارسال کن:")
                
                # ۲. اگر کاربر در مرحله وارد کردن نام بود
                elif chat_id in waiting_for_name:
                    new_name = text
                    
                    # بررسی اینکه آیا این نام قبلاً توسط کسی انتخاب شده است یا نه
                    if new_name in users_db.values():
                        send_message(chat_id, "⚠️ این نام قبلاً توسط کاربر دیگری انتخاب شده است! لطفاً یک نام دیگر انتخاب کن:")
                    elif len(new_name) < 3:
                        send_message(chat_id, "⚠️ نام انتخابی خیلی کوتاه است. لطفاً حداقل ۳ کاراکتر وارد کن:")
                    else:
                        # ثبت نام در دیتابیس
                        users_db[chat_id] = new_name
                        waiting_for_name.remove(chat_id)
                        send_message(chat_id, f"🎉 عالیه! نام **{new_name}** با موفقیت برای شما ثبت شد.\nاکنون حساب کاربری‌تان آماده است.")
                
                # ۳. بقیه پیام‌ها
                else:
                    if chat_id in users_db:
                        send_message(chat_id, f"کاربر {users_db[chat_id]}، پیام شما دریافت شد: {text}")
                    else:
                        waiting_for_name.add(chat_id)
                        send_message(chat_id, "لطفاً اول با دستور /start یا ارسال نام، ثبت‌نام کن.")
                        
        time.sleep(1)

if __name__ == "__main__":
    main()
