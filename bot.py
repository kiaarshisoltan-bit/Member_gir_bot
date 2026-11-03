import os
import time
import threading
import requests
import random
from flask import Flask

# --- تنظیمات اصلی ---
TOKEN = os.environ.get("BALE_TOKEN", "*******")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://member-gir-bot.onrender.com")

# اطلاعات جدید تو و کانال
ADMIN_ID = "@kia_karfarma"
INFO_CHANNEL = "@ettela_resani_member"

app = Flask(__name__)

# --- دیتابیس‌های در حافظه ---
users_db = {}          
wallets = {}           
campaigns_db = []      
history_db = {}        
user_task = {}         
rewarded_info_channel = set() # برای اینکه هر کس فقط یکبار جایزه بگیرد

waiting_for_name = set()
waiting_for_channel = set()
waiting_for_deletion = set()
waiting_for_referral_code = set()
is_entering_ref_code = set()

# --- توابع کمکی ---

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def self_ping():
    while True:
        try:
            time.sleep(300)
            requests.get(RENDER_URL, timeout=10)
        except:
            pass

def send_message_with_reply_keyboard(chat_id, text, keyboard=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"keyboard": keyboard, "resize_keyboard": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

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
                return status in ["member", "administrator", "creator"]
    except:
        pass
    return False

def show_main_menu(chat_id):
    for s in [waiting_for_name, waiting_for_channel, waiting_for_deletion, 
              waiting_for_referral_code, is_entering_ref_code]:
        if chat_id in s: s.remove(chat_id)
    if chat_id in user_task: del user_task[chat_id]

    nickname = users_db.get(chat_id, "کاربر")
    coins = wallets.get(chat_id, 0)
    text = f"سلام {nickname} عزیز! 🚀\n\n💰 موجودی سکه شما: {coins} 🪙\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    keyboard = [
        [{"text": "📢 ثبت کانال جدید (جذب ممبر)"}],
        [{"text": "💰 دریافت سکه"}, {"text": "🎁 دریافت جایزه کانال"}],
        [{"text": "📋 لیست کانال‌های من"}, {"text": "👥 دعوت از دوستان"}],
        [{"text": "👤 پروفایل من"}]
    ]
    send_message_with_reply_keyboard(chat_id, text, keyboard)

# --- بدنه اصلی ربات ---

def bot_main():
    print("Bot is running...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                text = update["message"].get("text", "").strip()

                # ۱. شروع و کد دعوت
                if text == "/start":
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_referral_code.add(chat_id)
                        keyboard = [[{"text": "✅ بله، کد دارم"}, {"text": "❌ خیر، ندارم"}]]
                        send_message_with_reply_keyboard(chat_id, "👋 خوش آمدید!\n\nآیا از طرف کسی دعوت شده‌اید و کد دعوت دارید؟", keyboard)
                    continue

                # ۲. بازگشت
                if text == "🔙 بازگشت به منوی اصلی" or text == "🔙 بازگشت":
                    show_main_menu(chat_id)
                    continue

                # ۳. فرآیند ثبت‌نام
                if chat_id in waiting_for_referral_code:
                    if text == "❌ خیر، ندارم":
                        waiting_for_referral_code.remove(chat_id)
                        users_db[chat_id] = "کاربر جدید"
                        wallets[chat_id] = 50
                        waiting_for_name.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "نام مستعار خود را بفرستید:", [[{"text": "🔙 بازگشت"} ]])
                    elif text == "✅ بله، کد دارم":
                        is_entering_ref_code.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "لطفاً کد دعوت را وارد کنید (عدد):", [[{"text": "🔙 بازگشت"} ]])
                    elif text.isdigit():
                        ref_id = int(text)
                        if ref_id in wallets and ref_id != chat_id:
                            wallets[ref_id] = wallets.get(ref_id, 0) + 10
                            users_db[chat_id] = "کاربر جدید"
                            wallets[chat_id] = 50
                            is_entering_ref_code.remove(chat_id)
                            waiting_for_referral_code.remove(chat_id)
                            waiting_for_name.add(chat_id)
                            send_message_with_reply_keyboard(chat_id, "✅ کد تایید شد! ۱۰ سکه به دعوت‌کننده تعلق گرفت. 🎁\n\nحالا نام مستعار خود را بفرستید:", [[{"text": "🔙 بازگشت"} ]])
                        else:
                            send_message_with_reply_keyboard(chat_id, "⚠️ کد اشتباه است. دوباره تلاش کنید:")
                    continue

                if chat_id in waiting_for_name:
                    if text == "🔙 بازگشت":
                        waiting_for_name.remove(chat_id)
                        show_main_menu(chat_id)
                    else:
                        users_db[chat_id] = text
                        waiting_for_name.remove(chat_id)
                        show_main_menu(chat_id)
                    continue

                # ۴. منوی اصلی
                if text == "📢 ثبت کانال جدید (جذب ممبر)":
                    if wallets.get(chat_id, 0) < 50:
                        send_message_with_reply_keyboard(chat_id, "⚠️ موجودی شما کمتر از ۵۰ سکه است!")
                    else:
                        waiting_for_channel.add(chat_id)
                        guide = (
                            "📖 *راهنمای ادمین کردن ربات*\n\n"
                            "برای اینکه ربات بتواند عضویت کاربران را بررسی کند، حتماً باید در کانال خود ادمین شود.\n\n"
                            "✅ مراحل:\n"
                            "۱. وارد کانال خود شوید.\n"
                            "۲. به قسمت ادمین‌ها بروید.\n"
                            "۳. ربات را اضافه کرده و دسترسی 'مشاهده پیام‌ها' را به آن بدهید.\n\n"
                            "حالا آیدی کانال را با @ بفرستید:"
                        )
                        send_message_with_reply_keyboard(chat_id, guide, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif chat_id in waiting_for_channel:
                    if text.startswith("@"):
                        wallets[chat_id] = wallets.get(chat_id, 0) - 50
                        campaigns_db.append({"owner": chat_id, "channel": text, "remaining_views": 25})
                        waiting_for_channel.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"✅ کانال {text} ثبت شد! 🎯", [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                        show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ آیدی باید با @ شروع شود:")

                elif text == "🎁 دریافت جایزه کانال":
                    if chat_id in rewarded_info_channel:
                        send_message_with_reply_keyboard(chat_id, "⚠️ شما قبلاً این جایزه را دریافت کرده‌اید!")
                    else:
                        if check_user_membership(INFO_CHANNEL, chat_id):
                            wallets[chat_id] = wallets.get(chat_id, 0) + 10
                            rewarded_info_channel.add(chat_id)
                            send_message_with_reply_keyboard(chat_id, "🎉 تبریک! ۱۰ سکه بابت عضویت در کانال اطلاع‌رسانی دریافت کردید! 🪙")
                            show_main_menu(chat_id)
                        else:
                            send_message_with_reply_keyboard(chat_id, f"❌ شما هنوز عضو کانال {INFO_CHANNEL} نیستید! ابتدا عضو شوید و دوباره تلاش کنید.")

                elif text == "💰 دریافت سکه":
                    my_campaigns = [c for c in campaigns_db if c["owner"] == chat_id]
                    for c in my_campaigns:
                        if not check_user_membership(c["channel"], chat_id):
                            wallets[chat_id] = max(0, wallets.get(chat_id, 0) - 2)
                            send_message_with_reply_keyboard(chat_id, f"⚠️ جریمه! شما از کانال {c['channel']} خارج شدید! ۲ سکه کسر شد. 💸")
                            break

                    user_history = history_db.get(chat_id, [])
                    available = [c for c in campaigns_db if c["owner"] != chat_id and c["remaining_views"] > 0 and c["channel"] not in user_history]

                    if not available:
                        send_message_with_reply_keyboard(chat_id, "🎉 همه کانال‌ها را دیده‌اید یا کانالی باقی نمانده است.")
                    else:
                        target = random.choice(available)
                        user_task[chat_id] = target
                        msg = f"📢 در این کانال عضو شوید:\n\n{target['channel']}\n\nسپس روی «✅ بررسی عضویت» بزنید."
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "✅ بررسی عضویت"}, {"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "✅ بررسی عضویت":
                    if chat_id in user_task:
                        target = user_task[chat_id]
                        if check_user_membership(target['channel'], chat_id):
                            wallets[chat_id] = wallets.get(chat_id, 0) + 5
                            target["remaining_views"] -= 1
                            if chat_id not in history_db: history_db[chat_id] = []
                            if target['channel'] not in history_db[chat_id]: history_db[chat_id].append(target['channel'])
                            
                            if target["remaining_views"] <= 0:
                                if target in campaigns_db: campaigns_db.remove(target)
                            
                            del user_task[chat_id]
                            send_message_with_reply_keyboard(chat_id, "🎉 تایید شد! ۵ سکه دریافت کردید! 🪙")
                            show_main_menu(chat_id)
                        else:
                            send_message_with_reply_keyboard(chat_id, "❌ هنوز عضو نشده‌ای!")
                    else:
                        show_main_menu(chat_id)

                elif text == "📋 لیست کانال‌های من":
                    my_c = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_c:
                        send_message_with_reply_keyboard(chat_id, "📭 کانالی ندارید.")
                    else:
                        msg = "📋 **کانال‌های شما:**\n\n" + "\n".join([f"- {c['channel']} ({c['remaining_views']} باقی‌مانده)" for c in my_c])
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🗑️ حذف کانال"}, {"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "🗑️ حذف کانال":
                    my_c = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_c:
                        send_message_with_reply_keyboard(chat_id, "📭 کانالی نیست.")
                    else:
                        waiting_for_deletion.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "👇 آیدی کانال را برای حذف بفرستید:", [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif chat_id in waiting_for_deletion:
                    found = next((c for c in campaigns_db if c["owner"] == chat_id and c["channel"] == text), None)
                    if found:
                        campaigns_db.remove(found)
                        waiting_for_deletion.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"🗑️ کانال {text} حذف شد.")
                        show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ یافت نشد!")

                elif text == "👤 پروفایل من":
                    nickname = users_db.get(chat_id, "کاربر")
                    coins = wallets.get(chat_id, 0)
                    my_c_list = [f"- {c['channel']}" for c in campaigns_db if c["owner"] == chat_id]
                    channels_str = "\n".join(my_c_list) if my_c_list else "ندارد"
                    
                    profile_text = (
                        f"👤 پروفایل:\n\n"
                        f"🔹 نام: {nickname}\n"
                        f"🪙 سکه: {coins}\n"
                        f"📢 کانال‌های من:\n{channels_str}\n\n"
                        f"📞 **پشتیبانی:** {ADMIN_ID}\n"
                        f"📢 **کانال اطلاع‌رسانی:** {INFO_CHANNEL}"
                    )
                    send_message_with_reply_keyboard(chat_id, profile_text, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "👥 دعوت از دوستان":
                    invite_code = chat_id
                    msg = (
                        "👥 **سیستم دعوت از دوستان**\n\n"
                        "با دعوت از دوستان خود، برای هر نفر که با کد شما وارد شود، ۱۰ سکه هدیه می‌گیرید! 🎁\n\n"
                        f"🔑 **کد اختصاصی شما:**\n`{invite_code}`\n\n"
                        "این کد را برای دوستان خود بفرستید و بگویید در هنگام شروع، آن را وارد کنند."
                    )
                    send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    bot_main()
