import os
import time
import requests

TOKEN = os.environ.get("BALE_TOKEN", "546304737:3dWovOidcSZK6SPZbwzjspTZlUwA32MUU0E")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# دیتابیس‌های موقت در حافظه
users_db = {}          # chat_id -> nickname
wallets = {}           # chat_id -> coins (موجودی سکه)
channels_db = []       # لیستی از دیکشنری‌های کانال‌ها
waiting_for_name = set()
waiting_for_channel = set() # کاربرانی که در حال ارسال آیدی کانال هستند

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
    print("Bot is starting with Channel Registration feature...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()
                
                # ۱. دستور شروع (/start)
                if text == "/start":
                    if chat_id in users_db:
                        send_message(chat_id, f"سلام {users_db[chat_id]} عزیز! 🚀\nموجودی سکه شما: {wallets.get(chat_id, 0)} سکه\n\nدستورات:\n/register_channel - ثبت کانال جدید\n/balance - موجودی سکه")
                    else:
                        waiting_for_name.add(chat_id)
                        send_message(chat_id, "سلام کیا جان! به ربات ممبرگیر خوش آمدید. 🚀\nلطفاً یک **نام مستعار (Nickname)** یکتا برای خودت ارسال کن:")
                
                # ۲. مرحله ورود نام مستعار
                elif chat_id in waiting_for_name:
                    new_name = text
                    if new_name in users_db.values():
                        send_message(chat_id, "⚠️ این نام قبلاً توسط کاربر دیگری انتخاب شده است! لطفاً یک نام دیگر انتخاب کن:")
                    elif len(new_name) < 3:
                        send_message(chat_id, "⚠️ نام انتخابی خیلی کوتاه است. لطفاً حداقل ۳ کاراکتر وارد کن:")
                    else:
                        users_db[chat_id] = new_name
                        wallets[chat_id] = 50  # هدیه اولیه: ۵۰ سکه
                        waiting_for_name.remove(chat_id)
                        send_message(chat_id, f"🎉 عالیه! نام **{new_name}** ثبت شد و ۵۰ سکه هدیه اولیه به حساب شما واریز گردید! 🎁\n\nبرای ثبت کانال از دستور /register_channel استفاده کنید.")
                
                # ۳. دستور موجودی
                elif text == "/balance":
                    if chat_id in users_db:
                        send_message(chat_id, f"💰 موجودی شما: {wallets.get(chat_id, 0)} سکه")
                    else:
                        send_message(chat_id, "اول باید ثبت‌نام کنی! /start رو بزن.")

                # ۴. دستور ثبت کانال
                elif text == "/register_channel":
                    if chat_id not in users_db:
                        send_message(chat_id, "ابتدا با دستور /start ثبت‌نام کنید.")
                    elif wallets.get(chat_id, 0) < 10:
                        send_message(chat_id, "⚠️ موجودی سکه شما برای ثبت کانال کافی نیست! (حداقل ۱۰ سکه نیاز است)")
                    else:
                        waiting_for_channel.add(chat_id)
                        send_message(chat_id, "📢 لطفاً آیدی کانال خود را ارسال کنید (مثلاً @YourChannel):")

                # ۵. دریافت آیدی کانال از کاربر
                elif chat_id in waiting_for_channel:
                    channel_username = text
                    if not channel_username.startswith("@"):
                        send_message(chat_id, "⚠️ آیدی کانال باید با @ شروع شود. دوباره تلاش کنید:")
                    else:
                        # کسر سکه و ثبت کانال
                        wallets[chat_id] -= 10
                        channels_db.append({
                            "owner": chat_id,
                            "channel": channel_username,
                            "target": 5 # فرضاً فعلا ۵ ممبر درخواستی
                        })
                        waiting_for_channel.remove(chat_id)
                        send_message(chat_id, f"✅ کانال {channel_username} با موفقیت ثبت شد!\n۱۰ سکه از حساب شما کسر گردید.\nموجودی جدید: {wallets[chat_id]} سکه 🪙")
                
                # ۶. پیام‌های متفرقه
                else:
                    if chat_id in users_db:
                        send_message(chat_id, "دستور نامعتبر. برای راهنمایی /start را بفرستید.")
                    else:
                        waiting_for_name.add(chat_id)
                        send_message(chat_id, "لطفاً اول یک نام مستعار برای خودت بفرست.")
                        
        time.sleep(1)

if __name__ == "__main__":
    main()
