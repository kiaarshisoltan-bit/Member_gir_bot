import os
import time
import requests

TOKEN = os.environ.get("BALE_TOKEN", "546304737:3dWovOidcSZK6SPZbwzjspTZlUwA32MUU0E")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

# دیتابیس‌های موقت در حافظه
users_db = {}          # chat_id -> nickname
wallets = {}           # chat_id -> coins
channels_db = []       # لیست کانال‌های ثبت شده
waiting_for_name = set()
waiting_for_channel = set()

def send_message_with_reply_keyboard(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,   # دکمه‌ها بزرگ و اندازه مناسب بشن
            "one_time_keyboard": False # دکمه‌ها پایین صفحه باقی بمونن
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

def show_main_menu(chat_id):
    nickname = users_db.get(chat_id, "کاربر")
    coins = wallets.get(chat_id, 0)
    text = f"سلام {nickname} عزیز! 🚀\nموجودی سکه شما: {coins} 🪙\n\nلطفاً یکی از گزینه‌های زیر را از منوی پایین انتخاب کنید:"
    
    # دکمه‌های معمولی پایین صفحه (Reply Keyboard)
    keyboard = [
        [{"text": "📢 ثبت کانال جدید"}],
        [{"text": "💰 دریافت سکه"}, {"text": "👤 پروفایل من"}]
    ]
    send_message_with_reply_keyboard(chat_id, text, keyboard)

def main():
    print("Bot is starting with Reply Keyboard support...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()
                
                if text == "/start":
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_name.add(chat_id)
                        # در هنگام ثبت نام دکمه‌ها رو بر می‌داریم تا اول نامش رو بفرسته
                        send_message_with_reply_keyboard(chat_id, "سلام کیا جان! به ربات ممبرگیر خوش آمدید. 🚀\nلطفاً یک **نام مستعار (Nickname)** یکتا برای خودت ارسال کن:")
                
                elif chat_id in waiting_for_name:
                    new_name = text
                    if new_name in users_db.values():
                        send_message_with_reply_keyboard(chat_id, "⚠️ این نام قبلاً توسط کاربر دیگری انتخاب شده است! لطفاً یک نام دیگر انتخاب کن:")
                    elif len(new_name) < 3:
                        send_message_with_reply_keyboard(chat_id, "⚠️ نام انتخابی خیلی کوتاه است. لطفاً حداقل ۳ کاراکتر وارد کن:")
                    else:
                        users_db[chat_id] = new_name
                        wallets[chat_id] = 50  # هدیه اولیه
                        waiting_for_name.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"🎉 عالیه! نام **{new_name}** ثبت شد و ۵۰ سکه هدیه اولیه دریافت کردید! 🎁")
                        show_main_menu(chat_id)
                
                elif chat_id in waiting_for_channel:
                    channel_username = text
                    if not channel_username.startswith("@"):
                        send_message_with_reply_keyboard(chat_id, "⚠️ آیدی کانال باید با @ شروع شود. دوباره تلاش کنید:")
                    else:
                        wallets[chat_id] -= 10
                        channels_db.append({
                            "owner": chat_id,
                            "channel": channel_username,
                            "target": 5
                        })
                        waiting_for_channel.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"✅ کانال {channel_username} با موفقیت ثبت شد!\n۱۰ سکه از حساب شما کسر گردید. 🪙")
                        show_main_menu(chat_id)
                
                # مدیریت کلیک روی دکمه‌های منوی پایین
                elif text == "📢 ثبت کانال جدید":
                    if wallets.get(chat_id, 0) < 10:
                        send_message_with_reply_keyboard(chat_id, "⚠️ موجودی سکه شما برای ثبت کانال کافی نیست! (حداقل ۱۰ سکه نیاز است)")
                    else:
                        waiting_for_channel.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "📢 لطفاً آیدی کانال خود را ارسال کنید (مثلاً @YourChannel):")
                
                elif text == "👤 پروفایل من" or text == "💰 دریافت سکه":
                    if text == "💰 دریافت سکه":
                        send_message_with_reply_keyboard(chat_id, "💡 بخش دریافت سکه به زودی فعال می‌شود! (در حال توسعه توسط کیا 🚀)")
                    show_main_menu(chat_id)
                
                else:
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_name.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "لطفاً اول یک نام مستعار برای خودت بفرست.")

        time.sleep(1)

if __name__ == "__main__":
    main()
