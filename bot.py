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

ADMIN_ID = "@kia_karfarma"
INFO_CHANNEL = "@ettela_resani_member"

app = Flask(__name__)

# --- دیتابیس‌های در حافظه ---
users_db = {}          
wallets = {}           
campaigns_db = []      # مربوط به تبلیغ و جذب ممبر کانال‌های بله
history_db = {}        
user_task = {}         
rewarded_info_channel = set()
created_groups_db = [] # مربوط به سفارش ساخت کانال/گروه

waiting_for_name = set()
waiting_for_channel = set()
waiting_for_deletion = set()
waiting_for_referral_code = set()
is_entering_ref_code = set()

waiting_for_transfer_dest = set()
waiting_for_transfer_amount = set()
transfer_temp_dest = {}

waiting_for_group_name = set()

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
              waiting_for_referral_code, is_entering_ref_code,
              waiting_for_transfer_dest, waiting_for_transfer_amount,
              waiting_for_group_name]:
        if chat_id in s: s.remove(chat_id)
    if chat_id in user_task: del user_task[chat_id]
    if chat_id in transfer_temp_dest: del transfer_temp_dest[chat_id]

    nickname = users_db.get(chat_id, "کاربر")
    coins = wallets.get(chat_id, 0)
    text = f"سلام {nickname} عزیز! 🚀\n\n💰 موجودی سکه شما: {coins} 🪙\n\nلطفاً یکی از گزینه‌های زیر را انتخاب کنید:"
    keyboard = [
        [{"text": "📢 ثبت تبلیغ کانال (جذب ممبر)"}],
        [{"text": "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)"}],
        [{"text": "💰 دریافت سکه"}, {"text": "🎁 دریافت جایزه کانال"}],
        [{"text": "📋 لیست تبلیغ‌های من"}, {"text": "📂 لیست کانال/گروه‌های سفارشی"}],
        [{"text": "👥 دعوت از دوستان"}, {"text": "💳 انتقال سکه"}],
        [{"text": "👤 پروفایل من"}, {"text": "❓ راهنمای استفاده"}],
        [{"text": "📞 پشتیبانی و ارتباط با ما"}]
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

                if text == "/start":
                    if chat_id in users_db:
                        show_main_menu(chat_id)
                    else:
                        waiting_for_referral_code.add(chat_id)
                        keyboard = [[{"text": "✅ بله، کد دارم"}, {"text": "❌ خیر، ندارم"}]]
                        send_message_with_reply_keyboard(chat_id, "👋 خوش آمدید!\n\nآیا از طرف کسی دعوت شده‌اید و کد دعوت دارید؟", keyboard)
                    continue

                if text == "🔙 بازگشت به منوی اصلی" or text == "🔙 بازگشت":
                    show_main_menu(chat_id)
                    continue

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

                if text == "💳 انتقال سکه":
                    waiting_for_transfer_dest.add(chat_id)
                    send_message_with_reply_keyboard(chat_id, "💳 **انتقال سکه به دیگران**\n\nلطفاً `chat_id` (آیدی عددی) کاربر مقصد را وارد کنید:", [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                    continue

                if chat_id in waiting_for_transfer_dest:
                    if text.isdigit():
                        dest_id = int(text)
                        if dest_id == chat_id:
                            send_message_with_reply_keyboard(chat_id, "⚠️ نمی‌توانید به خودتان سکه انتقال دهید! دوباره وارد کنید:")
                        elif dest_id not in users_db:
                            send_message_with_reply_keyboard(chat_id, "⚠️ کاربری با این مشخصات در ربات یافت نشد! دوباره وارد کنید:")
                        else:
                            waiting_for_transfer_dest.remove(chat_id)
                            transfer_temp_dest[chat_id] = dest_id
                            waiting_for_transfer_amount.add(chat_id)
                            send_message_with_reply_keyboard(chat_id, f"✅ کاربر مقصد تایید شد (`{dest_id}`).\n\nحالا تعداد سکه‌ای که می‌خواهید انتقال دهید را وارد کنید (عدد):", [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ لطفاً یک عدد معتبر (`chat_id`) وارد کنید:")
                    continue

                if chat_id in waiting_for_transfer_amount:
                    if text.isdigit():
                        amount = int(text)
                        dest_id = transfer_temp_dest.get(chat_id)
                        current_coins = wallets.get(chat_id, 0)

                        if amount <= 0:
                            send_message_with_reply_keyboard(chat_id, "⚠️ مقدار سکه باید بیشتر از صفر باشد:")
                        elif current_coins < amount:
                            send_message_with_reply_keyboard(chat_id, f"⚠️ موجودی شما کافی نیست! موجودی فعلی شما: {current_coins} سکه است. مقدار کمتری وارد کنید:")
                        else:
                            wallets[chat_id] -= amount
                            wallets[dest_id] = wallets.get(dest_id, 0) + amount

                            waiting_for_transfer_amount.remove(chat_id)
                            if chat_id in transfer_temp_dest: del transfer_temp_dest[chat_id]

                            send_message_with_reply_keyboard(chat_id, f"✅ انتقال با موفقیت انجام شد!\nتعداد {amount} سکه به کاربر `{dest_id}` واریز گردید. 🪙")
                            
                            sender_name = users_db.get(chat_id, "یک کاربر")
                            send_message_with_reply_keyboard(dest_id, f"🎁 شما تعداد {amount} سکه از طرف {sender_name} (`{chat_id}`) هدیه گرفتید! 🪙")
                            
                            show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ لطفاً تعداد سکه را به صورت عدد وارد کنید:")
                    continue

                if text == "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)":
                    if wallets.get(chat_id, 0) < 1000:
                        send_message_with_reply_keyboard(chat_id, f"⚠️ موجودی شما کافی نیست!\nبرای سفارش ساخت کانال/گروه به **۱۰۰۰ سکه** نیاز دارید اما موجودی شما `{wallets.get(chat_id, 0)}` سکه است.")
                    else:
                        waiting_for_group_name.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "✨ **سفارش ساخت کانال یا گروه جدید**\n\nهزینه این خدمت **۱۰۰۰ سکه** از حساب شما کسر خواهد شد.\n\nلطفاً جزئیات و نام دلخواه کانال یا گروهی که می‌خواهید برایتان ساخته شود را بفرستید:", [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                    continue

                if chat_id in waiting_for_group_name:
                    wallets[chat_id] = wallets.get(chat_id, 0) - 1000
                    owner_name = users_db.get(chat_id, "کاربر")
                    created_groups_db.append({"owner": owner_name, "owner_id": chat_id, "info": text})
                    waiting_for_group_name.remove(chat_id)

                    send_message_with_reply_keyboard(chat_id, "🎉 سفارش ساخت کانال/گروه شما ثبت شد و ۱۰۰۰ سکه کسر گردید!\nبه زودی ادمین با شما ارتباط می‌گیرد. 🚀")
                    
                    try:
                        send_message_with_reply_keyboard(ADMIN_ID.replace("@",""), f"🔔 سفارش ساخت کانال/گروه جدید!\nاز طرف: {owner_name} (`{chat_id}`)\nجزئیات: {text}")
                    except:
                        pass

                    show_main_menu(chat_id)
                    continue

                if text == "📂 لیست کانال/گروه‌های سفارشی":
                    if not created_groups_db:
                        send_message_with_reply_keyboard(chat_id, "📭 هنوز سفارش ساخت کانال یا گروهی ثبت نشده است.")
                    else:
                        msg = "📂 **لیست کانال‌ها و گروه‌های سفارشی کاربران:**\n\n"
                        for idx, g in enumerate(created_groups_db, 1):
                            msg += f"{idx}. 📌 {g['info']}\n   👤 سفارش‌دهنده: {g['owner']}\n\n"
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                    continue

                if text == "📢 ثبت تبلیغ کانال (جذب ممبر)":
                    if wallets.get(chat_id, 0) < 50:
                        send_message_with_reply_keyboard(chat_id, "⚠️ موجودی شما کمتر از ۵۰ سکه است!")
                    else:
                        waiting_for_channel.add(chat_id)
                        guide = (
                            "📖 *راهنمای ادمین کردن ربات*\n\n"
                            "برای اینکه ربات بتواند عضویت کاربران را در کانال شما بررسی کند، حتماً باید ربات را در کانال خود ادمین کنید.\n\n"
                            "✅ مراحل:\n"
                            "۱. وارد کانال خود شوید.\n"
                            "۲. به قسمت ادمین‌ها بروید.\n"
                            "۳. ربات را اضافه کرده و دسترسی لازم را به آن بدهید.\n\n"
                            "حالا آیدی کانال خود را با @ بفرستید:"
                        )
                        send_message_with_reply_keyboard(chat_id, guide, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif chat_id in waiting_for_channel:
                    if text.startswith("@"):
                        wallets[chat_id] = wallets.get(chat_id, 0) - 50
                        campaigns_db.append({"owner": chat_id, "channel": text, "remaining_views": 25})
                        waiting_for_channel.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"✅ تبلیغ کانال {text} با موفقیت ثبت شد! 🎯", [[{"text": "🔙 بازگشت به منوی اصلی"}]])
                        show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ آیدی کانال حتماً باید با @ شروع شود:")

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
                    # --- 🛡️ سیستم ضد تقلب (جریمه ۳ سکه‌ای به ازای هر لفت) ---
                    user_joined_channels = history_db.get(chat_id, [])
                    left_channels = []

                    for ch in user_joined_channels:
                        if not check_user_membership(ch, chat_id):
                            left_channels.append(ch)

                    if left_channels:
                        penalty = len(left_channels) * 3
                        wallets[chat_id] = max(0, wallets.get(chat_id, 0) - penalty)
                        
                        for ch in left_channels:
                            history_db[chat_id].remove(ch)

                        send_message_with_reply_keyboard(
                            chat_id, 
                            f"🚨 **اخطار سیستم ضد تقلب!**\n\nشما از {len(left_channels)} کانالی که برای عضویت در آن‌ها سکه گرفته بودید لفت داده‌اید!\nبه همین دلیل مبلغ **{penalty} سکه** از کیف پول شما جریمه کسر گردید. 💸"
                        )
                    # ---------------------------------------------------------

                    available = [c for c in campaigns_db if c["owner"] != chat_id and c["remaining_views"] > 0 and c["channel"] not in history_db.get(chat_id, [])]

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

                elif text == "📋 لیست تبلیغ‌های من":
                    my_c = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_c:
                        send_message_with_reply_keyboard(chat_id, "📭 شما تبلیغ فعالی ندارید.")
                    else:
                        msg = "📋 **تبلیغ‌های کانال شما:**\n\n" + "\n".join([f"- {c['channel']} ({c['remaining_views']} بازدید باقی‌مانده)" for c in my_c])
                        send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🗑️ حذف تبلیغ کانال"}, {"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "🗑️ حذف تبلیغ کانال":
                    my_c = [c for c in campaigns_db if c["owner"] == chat_id]
                    if not my_c:
                        send_message_with_reply_keyboard(chat_id, "📭 کانالی برای حذف وجود ندارد.")
                    else:
                        waiting_for_deletion.add(chat_id)
                        send_message_with_reply_keyboard(chat_id, "👇 آیدی کانالی که می‌خواهید حذف شود را بفرستید:", [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif chat_id in waiting_for_deletion:
                    found = next((c for c in campaigns_db if c["owner"] == chat_id and c["channel"] == text), None)
                    if found:
                        campaigns_db.remove(found)
                        waiting_for_deletion.remove(chat_id)
                        send_message_with_reply_keyboard(chat_id, f"🗑️ تبلیغ کانال {text} حذف شد.")
                        show_main_menu(chat_id)
                    else:
                        send_message_with_reply_keyboard(chat_id, "⚠️ کانالی با این آیدی در لیست شما یافت نشد!")

                elif text == "👤 پروفایل من":
                    nickname = users_db.get(chat_id, "کاربر")
                    coins = wallets.get(chat_id, 0)
                    my_c_list = [f"- {c['channel']}" for c in campaigns_db if c["owner"] == chat_id]
                    channels_str = "\n".join(my_c_list) if my_c_list else "ندارد"
                    
                    profile_text = (
                        f"👤 پروفایل:\n\n"
                        f"🔹 نام: {nickname}\n"
                        f"🪙 سکه: {coins}\n\n"
                        f"📢 کانال‌های ثبت شده برای جذب ممبر:\n{channels_str}"
                    )
                    send_message_with_reply_keyboard(chat_id, profile_text, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "❓ راهنمای استفاده":
                    help_text = (
                        "❓ **راهنمای جامع استفاده از ربات**\n\n"
                        "1️⃣ **دریافت سکه:** با زدن روی «💰 دریافت سکه» و عضویت در کانال‌ها، ۵ سکه بگیرید.\n"
                        "⚠️ **سیستم ضد تقلب:** اگر از کانال‌ها لفت بدهید، به ازای هر کدام **۳ سکه** جریمه می‌شوید!\n\n"
                        "2️⃣ **ثبت تبلیغ (جذب ممبر):** کانال خود را با کمترین هزینه در معرض دید کاربران قرار دهید.\n\n"
                        "3️⃣ **سفارش ساخت کانال/گروه:** با پرداخت ۱۰۰۰ سکه درخواست ساخت کانال/گروه اختصاصی ثبت کنید.\n\n"
                        "4️⃣ **دعوت و انتقال سکه:** از کد دعوت خود استفاده کنید یا به دوستانتان سکه بفرستید."
                    )
                    send_message_with_reply_keyboard(chat_id, help_text, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "📞 پشتیبانی و ارتباط با ما":
                    support_text = (
                        "📞 **ارتباط با پشتیبانی و اطلاع‌رسانی**\n\n"
                        f"👨‍💻 **پشتیبان اصلی:** {ADMIN_ID}\n"
                        f"📢 **کانال اطلاع‌رسانی ربات:** {INFO_CHANNEL}\n\n"
                        "هرگونه سوال یا مشکلی دارید می‌توانید به ادمین پیام دهید."
                    )
                    send_message_with_reply_keyboard(chat_id, support_text, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

                elif text == "👥 دعوت از دوستان":
                    invite_code = chat_id
                    msg = (
                        "👥 **سیستم دعوت از دوستان**\n\n"
                        "با دعوت از دوستان خود، برای هر نفر ۱۰ سکه هدیه بگیرید! 🎁\n\n"
                        f"🔑 **کد اختصاصی شما:**\n`{invite_code}`"
                    )
                    send_message_with_reply_keyboard(chat_id, msg, [[{"text": "🔙 بازگشت به منوی اصلی"}]])

        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=self_ping, daemon=True).start()
    bot_main()
