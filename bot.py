import os
import sys
import time
import json
import random
import threading
import requests
from flask import Flask

# تنظیم برای خروجی فوری لاگ‌ها در رندر
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات اولیه و توکن
BOT_TOKEN = os.environ.get("BOT_TOKEN", "*******")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1708788049"))

print(f"🚀 ربات ممبرگیر شروع به کار کرد...", flush=True)
print(f"🔗 BASE_URL: {BASE_URL}", flush=True)

# وب‌سرور Flask برای زنده نگه داشتن روی Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running! 🤖", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# راه‌اندازی سرور در ترد جداگانه
threading.Thread(target=run_flask, daemon=True).start()

# دیتابیس ساده JSON
DB_FILE = "bot_database.json"

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {
        "users_db": {},
        "wallets": {},
        "gift_codes_db": {},
        "user_redeemed_codes": {}
    }

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتابیس: {e}", flush=True)

db = load_db()

# توابع ارتباطی با API بله
def api(method, params=None):
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=params or {}, timeout=30)
        print(f"📤 {method} → {r.status_code}: {r.text[:200]}", flush=True)
        return r.json()
    except Exception as e:
        print(f"⚠️ خطای API در {method}: {e}", flush=True)
        return {}

def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", payload)

def get_updates(offset=None):
    params = {"timeout": 25}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.post(f"{BASE_URL}/getUpdates", json=params, timeout=30)
        return r.json()
    except Exception as e:
        print(f"⚠️ خطای getUpdates: {e}", flush=True)
        return {"ok": False, "result": []}

# مدیریت پیام‌ها و آپدیت‌ها
def handle_update(update):
    message = update.get("message")
    if not message:
        return
    
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    
    print(f"📩 پیام جدید از {chat_id}: {text}", flush=True)

    # ثبت نام کاربر در صورت عدم حضور
    str_chat_id = str(chat_id)
    if str_chat_id not in db["wallets"]:
        db["wallets"][str_chat_id] = 50 # هدیه ثبت‌نام
        save_db(db)

    # پاسخ ساده به /start برای تست اولیه
    if text == "/start":
        send_message(chat_id, "سلام کیا جان! 🤖 ربات با موفقیت به بله متصل شد و پیامت رو دریافت کرد. 🎉")
    else:
        send_message(chat_id, f"پیام شما دریافت شد: {text}")

def main():
    # پاک کردن وب‌هوک قبلی برای اطمینان از کارکرد پولینگ
    try:
        r = requests.get(f"{BASE_URL}/deleteWebhook", timeout=15)
        print(f"🧹 وبهوک پاک شد: {r.status_code}", flush=True)
    except Exception as e:
        print(f"⚠️ خطا در پاک کردن وبهوک: {e}", flush=True)

    # بررسی اتصال ربات
    me = api("getMe")
    if me.get("ok"):
        print(f"🤖 متصل به ربات: @{me['result'].get('username')}", flush=True)
    else:
        print(f"❌ توکن نامعتبر یا خطا در getMe: {me}", flush=True)

    offset = None
    while True:
        try:
            data = get_updates(offset)
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        handle_update(update)
                    except Exception as e:
                        print(f"❌ خطا در پردازش آپدیت: {e}", flush=True)
            else:
                time.sleep(2)
        except Exception as e:
            print(f"❌ خطای حلقه اصلی: {e}", flush=True)
            time.sleep(3)

if __name__ == "__main__":
    main()
