import os
import time
import threading
import requests
from flask import Flask

# تنظیمات اصلی
TOKEN = os.environ.get("BALE_TOKEN", "*******")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://member-gir-bot.onrender.com")

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is active and running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def self_ping():
    while True:
        try:
            time.sleep(300)
            requests.get(RENDER_URL)
        except:
            pass

# دیتابیس‌ها
users_db = {}
wallets = {}
campaigns_db = []
waiting_for_name = set()
waiting_for_channel = set()
waiting_for_deletion = set()
user_task = {}

def send_message_with_reply_keyboard(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True, "one_time_keyboard": False}
    requests.post(url, json=payload)

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        response = requests.get(url, params=params, timeout=35)
        if response.status_code == 200:
            return response.json().get("result", [])
    except:
        pass
    return []

def check_user_membership(channel_username, user_id):
    url = f"{BASE_URL}/getChatMember"
    params = {"chat_id": channel_username, "user_id": user_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                status = data.get("result", {}).get("status")
                if status in ["member", "administrator", "creator"]:
                    return True
    except:
        pass
    return False

def show_main_menu(chat_id):
    if chat_id in waiting_for_name: waiting_for_name.remove(chat_id)
    if chat_id in waiting_for_channel: waiting_for_channel.remove(chat_id)
    if chat_id in waiting_for_deletion: waiting_for_deletion.remove(chat_id)
    if chat_id in user_task: del user_task[chat_id]

    nickname = users_db.get(chat_id, "کاربر")
    coins = wallets.get(chat_id, 0)
    text = f"سلام {nickname} عزیز! 🚀\nموجودی سکه شما: {coins} 🪙\n\nلطفاً یکی از گزینه‌های زیر را از منوی پایین انتخاب کنید:"
    keyboard = [[{"text": "📢 ثبت کانال جدید (جذب ممبر)"}], [{"text": "💰 دریافت سکه"}, {"text": "📋 لیست کانال‌های من"}], [{"text": "👤 پروفایل من"}]]
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
                    show_main_menu(chat_id)
                    continue

                # --- سیستم بررسی جریمه و عضویت (هنگام شروع هر فعالیت حساس) ---
                if text in ["💰 دریافت سکه", "👤 پروفایل من", "📋 لیست کانال‌های من"]:
                    my_campaigns = [c for c in campaigns_db if c["owner"] == chat_id]
                    for campaign in my_campaigns:
                        # چک کردن اینکه آیا کاربر هنوز عضو کانال خودش هست یا نه
                        if not check_user_membership(campaign["channel"], chat_id):
                            # اگر عضو نبود: کسر سکه و هشدار
                            current_coins = wallets.get(chat_id, 0)
                            wallets[chat_id] = max(0, current_coins - 2)
                            send_message_with_reply_keyboard(chat_id, f"⚠️ هشدار جریمه! شما از کانال {campaign['channel']} خارج شده‌اید. ۲ سکه از شما کسر شد! 💸\n\nبرای جلوگیری از کسر سکه بیشتر، حتماً عضو کانال خود بمانید.")
                            # اگر سکه صفر شد یا کاربر خیلی زیاده‌رو بود، اینجا میتونی محدودیت بیشتری بذاری
                    
                    # ادامه روند عادی بعد از چک کردن جریمه...

                if text == "/start":
                    if chat_id in users_db: show_main_menu(chat_id)
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
                        wallets[chat_id] = 50  
                        waiting_for_name.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"🎉 عالیه! نام **{new_name}** ثبت شد و ۵۰ سکه هدیه اولیه دریافت کردید! 🎁")
                        show_main_menu(chat_id)
                
                elif chat_id in waiting_for_channel:
                    channel_username = text
                    if not channel_username.startswith("@"):
                        send_message_with_reply_keyboard(chat_id, "⚠️ آیدی کانال باید با @ شروع شود. دوباره تلاش کنید:")
                    else:
                        wallets[chat_id] -= 50
                        campaigns_db.append({"owner": chat_id, "channel": channel_username, "remaining_views": 25})
                        waiting_for_channel.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"✅ کانال {channel_username} با موفقیت ثبت شد!\n۵۰ سکه کسر گردید. 🎯🪙\n\n*(توجه: حتماً ربات را ادمین کانال خود کنید)*")
                        show_main_menu(chat_id)
                
                elif chat_id in waiting_for_deletion:
                    channel_to_delete = text
                    found_campaign = next((c for c in campaigns_db if c["owner"] == chat_id and c["channel"] == channel_to_delete), None)
                    if found_campaign:
                        campaigns_db.remove(found_campaign)
                        waiting_for_deletion.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"🗑️ کانال {channel_to_delete} حذف شد.")
                        show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ چنین کانالی یافت نشد!")

                elif text == "📢 ثبت کانال جدید (جذب ممبر)":
                    if wallets.get(chat_id, 0) < 50:
                        send_message_with_reply_keyboard(chat_id, "⚠️ موجودی سکه کافی نیست! (نیاز به ۵۰ سکه)")
                    else:
                        guide_text = (
                            "📖 *راهنمای ادمین کردن ربات*\n\n"
                            "برای اینکه ربات بتواند در کانال شما فعالیت کند، باید آن را ادمین کنید:\n\n"
                            "1️⃣ وارد کانال/گروه خود شوید\n"
                            "2️⃣ روی نام کانال/گروه در بالای صفحه کلیک کنید\n"
                            "3️⃣ گزینه *Administrators* یا *مدیران* را انتخاب کنید\n"
                            "4️⃣ روی *Add Admin* یا *افزودن مدیر* کلیک کنید\n"
                            "5️⃣ نام یا یوزرنیم ربات را جستجو کنید\n"
                            "6️⃣ ربات را انتخاب و دسترسی‌های لازم را فعال کنید\n"
                            "7️⃣ روی *Save* یا *ذخیره* کلیک کنید\n\n"
                            "✅ حالا ربات ادمین کانال شماست و می‌توانید آن را ثبت کنید."
                        )
                        waiting_for_channel.add(chat_id)
                        back_kb = [[{"text": "🔙 بازگشت به منوی اصلی"}]]
                        send_message_with_reply_keyboard(chat_id, guide_text, back_kb)
                        time.sleep(1)
                        send_message_with_reply_keyboard(chat_id, "👇\n\nحالا لطفاً **آیدی کانال یا گروه** خود را ارسال کنید (مثلاً @YourChannel):", back_kb)

                elif text == "📋 لیست کانال‌های من":
                    my_campaigns = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_campaigns:
                        send_message_with_reply_keyboard(chat_id, "📭 شما هیچ کانالی ندارید.")
                    else:
                        msg = "📋 **لیست کانال‌های فعال شما:**\n\n"
                        for idx, c in enumerate(my_campaigns, 1):
                            msg += f"{idx}. {c['channel']} (باقی‌مانده: {c['remaining_views']})\n"
                        msg += "\nبرای حذف، روی دکمه «🗑️ حذف کانال» بزنید."
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🗑️ حذف کانال"}, {"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "🗑️ حذف کانال":
                    my_campaigns = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_campaigns:
                        send_message_with_reply_keyboard(chat_id, "📭 کانالی برای حذف نیست.")
                    else:
                        waiting_for_deletion.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "👇 آیدی کانال برای حذف را بفرستید:", [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "💰 دریافت سکه":
                    # چک کردن جریمه قبل از نمایش لیست کانال‌ها
                    my_campaigns = [c for c in campaigns_db if c["owner"] == chat_id]
                    for c in my_campaigns:
                        if not check_user_membership(c["channel"], chat_id):
                            wallets[chat_id] = max(0, wallets.get(chat_id, 0) - 2)
                            send_message_with_reply_keyboard(chat_id, f"⚠️ جریمه! از کانال {c['channel']} خارج شدید! ۲ سکه کسر شد.")
                            break

                    available_campaigns = [c for c in campaigns_db if c["owner"] != chat_id and c["remaining_views"] > 0]
                    if not available_campaigns:
                        send_message_with_reply_keyboard(chat_id, "📭 کانالی موجود نیست.")
                    else:
                        target_campaign = available_campaigns[0]
                        user_task[chat_id] = target_campaign
                        msg = f"📢 در این کانال عضو شوید:\n\n{target_campaign['channel']}\n\nسپس روی «✅ بررسی عضویت» بزنید."
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "✅ بررسی عضویت"}, {"text": "🔙 بازگشت به منوی اصلی"}]])
                
                elif text == "✅ بررسی عضویت":
                    if chat_id in user_task:
                        target_campaign = user_task[chat_id]
                        if check_user_membership(target_campaign['channel'], chat_id):
                            wallets[chat_id] = wallets.get(chat_id, 0) + 5
                            target_campaign["remaining_views"] -= 1
                            if target_campaign["remaining_views"] <= 0 and target_campaign in campaigns_db:
                                campaigns_db.remove(target_campaign)
                            del user_task[chat_id]
                            send_message_with_reply_keyboard(chat_id, "🎉 تایید شد! ۵ سکه گرفتید! 🪙")
                            show_main_menu(chat_id)
                        else:
                            send_message_with_reply_keyboard(chat_id, "❌ هنوز عضو نشده‌ای!")
                    else:
                        show_main_menu(chat_id)

                elif text == "👤 پروفایل من":
                    nickname = users_db.get(chat_id, "کاربر")
                    coins = wallets.get(chat_id, 0)
                    my_campaigns_info = [f"{c['channel']} ({c['remaining_views']})" for c in campaigns_db if c["owner"] == chat_id]
                    channels_list = "\n".join(my_campaigns_info) if my_campaigns_info else "ندارد"
                    profile_text = f"👤 پروفایل:\n\n🔹 نام: {nickname}\n🪙 سکه: {coins}\n\n📢 کانال‌های من:\n{channels_list}"
                    send_message_with_reply_keyboard(chat_id, profile_text)
                    show_main_menu(chat_id)

        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    bot_main()
