import os
import time
import threading
import requests
from flask import Flask

# تنظیمات اصلی
TOKEN = os.environ.get("BALE_TOKEN", "*******")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://member-gir-bot.onrender.com")

# راه‌اندازی Flask برای بیدار نگه داشتن رندر
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# تابع خودکار پینگ کردن برای جلوگیری از خوابیدن رندر
def self_ping():
    while True:
        try:
            time.sleep(300)  # هر ۵ دقیقه یک بار
            response = requests.get(RENDER_URL)
            print(f"Self-ping successful: {response.status_code}")
        except Exception as e:
            print(f"Self-ping error: {e}")

# دیتابیس‌های موقت در حافظه
users_db = {}          # chat_id -> nickname
wallets = {}           # chat_id -> coins
campaigns_db = []      # لیست کمپین‌ها: [{"owner": id, "channel": "@name", "remaining_views": 25}]
waiting_for_name = set()
waiting_for_channel = set()
user_task = {}         # نگهداری کانالی که کاربر در حال حاضر باید در آن عضو شود

def send_message_with_reply_keyboard(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        payload["reply_markup"] = {
            "keyboard": keyboard,
            "resize_keyboard": True,
            "one_time_keyboard": False
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

# تابع بررسی واقعی عضویت کاربر در کانال از طریق API بله
def check_user_membership(channel_username, user_id):
    url = f"{BASE_URL}/getChatMember"
    params = {
        "chat_id": channel_username,
        "user_id": user_id
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                status = data.get("result", {}).get("status")
                # وضعیاتی که یعنی کاربر عضو کانال است
                if status in ["member", "administrator", "creator"]:
                    return True
    except Exception as e:
        print(f"Error checking membership: {e}")
    
    # به طور پیش‌فرض اگر خطا داد یا ربات ادمین نبود، برای جلوگیری از گیر کردن، 
    # در محیط تستی می‌تونید بررسی کنید (یا در صورت نیاز سخت‌گیرانه‌تر عمل کنید).
    # اینجا اگر ادمین نبوده یا ارور داده، برای اینکه ربات کرش نکند False برمی‌گردانیم.
    return False

def show_main_menu(chat_id):
    if chat_id in waiting_for_name:
        waiting_for_name.remove(chat_id)
    if chat_id in waiting_for_channel:
        waiting_for_channel.remove(chat_id)
    if chat_id in user_task:
        del user_task[chat_id]

    nickname = users_db.get(chat_id, "کاربر")
    coins = wallets.get(chat_id, 0)
    text = f"سلام {nickname} عزیز! 🚀\nموجودی سکه شما: {coins} 🪙\n\nلطفاً یکی از گزینه‌های زیر را از منوی پایین انتخاب کنید:"
    
    keyboard = [
        [{"text": "📢 ثبت کانال جدید (جذب ممبر)"}],
        [{"text": "💰 دریافت سکه"}, {"text": "👤 پروفایل من"}]
    ]
    send_message_with_reply_keyboard(chat_id, text, keyboard)

def bot_main():
    print("Bot polling is started...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()
                
                if text == "🔙 بازگشت به منوی اصلی":
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_name.discard(chat_id)
                        send_message_with_reply_keyboard(chat_id, "به منوی اصلی برگشتید. برای شروع /start را بزنید.")
                    continue

                if text == "/start":
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_name.add(chat_id)
                        back_kb = [[{"text": "🔙 بازگشت به منوی اصلی"}]]
                        send_message_with_reply_keyboard(chat_id, "سلام! به ربات ممبرگیر خوش آمدید. 🚀\nلطفاً یک **نام مستعار (Nickname)** یکتا برای خودت ارسال کن:", back_kb)
                
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
                        wallets[chat_id] -= 50
                        campaigns_db.append({
                            "owner": chat_id,
                            "channel": channel_username,
                            "remaining_views": 25
                        })
                        waiting_for_channel.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"✅ کانال {channel_username} با موفقیت ثبت شد!\n۵۰ سکه کسر گردید و کانال شما برای **۲۵ کاربر دیگر** جهت عضویت نمایش داده خواهد شد. 🎯🪙\n\n*(توجه: حتماً ربات را ادمین کانال خود کنید تا بررسی عضویت به درست کار کند)*")
                        show_main_menu(chat_id)
                
                elif text == "📢 ثبت کانال جدید (جذب ممبر)":
                    if wallets.get(chat_id, 0) < 50:
                        send_message_with_reply_keyboard(chat_id, "⚠️ موجودی سکه شما برای ثبت کانال کافی نیست!\n(برای دریافت ۲۵ ممبر/پیشنهاد، حداقل **۵۰ سکه** نیاز دارید).")
                    else:
                        waiting_for_channel.add(chat_id)
                        back_kb = [[{"text": "🔙 بازگشت به منوی اصلی"}]]
                        send_message_with_reply_keyboard(chat_id, "📢 لطفاً آیدی کانال خود را ارسال کنید (مثلاً @YourChannel):\n\n*(هزینه: ۵۰ سکه برای ۲۵ پیشنهاد عضویت)*", back_kb)
                
                elif text == "💰 دریافت سکه":
                    available_campaigns = [c for c in campaigns_db if c["owner"] != chat_id and c["remaining_views"] > 0]
                    if not available_campaigns:
                        send_message_with_reply_keyboard(chat_id, "📭 در حال حاضر هیچ کانالی برای عضویت وجود ندارد. لطفاً بعداً دوباره امتحان کنید!")
                        show_main_menu(chat_id)
                    else:
                        target_campaign = available_campaigns[0]
                        user_task[chat_id] = target_campaign
                        
                        earn_keyboard = [
                            [{"text": "✅ بررسی عضویت"}],
                            [{"text": "🔙 بازگشت به منوی اصلی"}]
                        ]
                        msg = f"📢 لطفاً در کانال زیر عضو شوید:\n\n{target_campaign['channel']}\n\nپس از عضویت، روی دکمه «✅ بررسی عضویت» بزنید تا ۵ سکه هدیه بگیرید! 🪙"
                        send_message_with_reply_keyboard(chat_id, msg, earn_keyboard)
                
                elif text == "✅ بررسی عضویت":
                    if chat_id in user_task:
                        target_campaign = user_task[chat_id]
                        channel_to_check = target_campaign['channel']
                        
                        # بررسی واقعی عضویت کاربر در کانال
                        is_member = check_user_membership(channel_to_check, chat_id)
                        
                        if is_member:
                            # پاداش به کاربر
                            wallets[chat_id] = wallets.get(chat_id, 0) + 5
                            
                            # کم کردن یک واحد از سهمیه کمپین صاحب کانال
                            target_campaign["remaining_views"] -= 1
                            
                            # پاکسازی کمپین‌های تمام‌شده
                            if target_campaign["remaining_views"] <= 0 and target_campaign in campaigns_db:
                                campaigns_db.remove(target_campaign)
                            
                            del user_task[chat_id]
                            send_message_with_reply_keyboard(chat_id, "🎉 تبریک! عضویت شما تایید شد و ۵ سکه به کیف پول شما اضافه گردید! 🪙✨")
                            show_main_menu(chat_id)
                        else:
                            send_message_with_reply_keyboard(chat_id, "❌ شما هنوز در کانال مورد نظر عضو نشده‌اید!\nلطفاً اول در کانال عضو شوید و سپس دوباره روی «✅ بررسی عضویت» بزنید.")
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ شما در حال حاضر در دستوری برای دریافت سکه نیستید.")
                        show_main_menu(chat_id)
                
                elif text == "👤 پروفایل من":
                    nickname = users_db.get(chat_id, "کاربر")
                    coins = wallets.get(chat_id, 0)
                    
                    my_campaigns_info = []
                    for c in campaigns_db:
                        if c["owner"] == chat_id:
                            my_campaigns_info.append(f"{c['channel']} (باقی‌مانده پیشنهاد: {c['remaining_views']})")
                    
                    channels_list = "\n".join(my_campaigns_info) if my_campaigns_info else "ندارد"
                    
                    profile_text = (
                        f"👤 **اطلاعات پروفایل شما:**\n\n"
                        f"🔹 نام مستعار: {nickname}\n"
                        f"🪙 موجودی سکه: {coins}\n\n"
                        f"📢 **کانال‌های در حال جذب شما:**\n{channels_list}"
                    )
                    send_message_with_reply_keyboard(chat_id, profile_text)
                    show_main_menu(chat_id)
                
                else:
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_name.add(chat_id)
                        back_kb = [[{"text": "🔙 بازگشت به منوی اصلی"}]]
                        send_message_with_reply_keyboard(chat_id, "لطفاً اول یک نام مستعار برای خودت بفرست:", back_kb)

        time.sleep(1)

if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    ping_thread = threading.Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    bot_main()
