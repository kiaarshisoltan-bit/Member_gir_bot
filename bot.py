import os
import sys
import time
import json
import random
import threading
import requests
from flask import Flask

# تنظیم خروجی فوری برای لاگ‌های رندر
sys.stdout.reconfigure(line_buffering=True)

# تنظیمات پایه
BOT_TOKEN = os.environ.get("BOT_TOKEN", "*******")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
ADMIN_ID = int(os.environ.get("ADMIN_ID", "1708788049"))
INFO_CHANNEL = "@ettela_resani_member"
SUPPORT_CHANNEL = "@ettela_resani_member"
ADMIN_USERNAME = "@kia_karfarma"

print(f"🚀 ربات ممبرگیر جامع بله شروع به کار کرد...", flush=True)

# وب‌سرور Flask برای زنده ماندن روی Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive and running! 🤖", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# دیتابیس JSON
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
        "campaigns_db": {},
        "history_db": {},
        "rewarded_info_channel": [],
        "rewarded_earn_channels": {},
        "waiting_for_name": [],
        "waiting_for_channel": [],
        "waiting_for_transfer_dest": {},
        "waiting_for_transfer_amount": {},
        "waiting_for_order_link": [],
        "waiting_for_order_count": {},
        "waiting_for_broadcast": [],
        "last_lucky_wheel": {},
        "gift_codes_db": {},
        "user_redeemed_codes": {},
        "waiting_for_new_gift_code": [],
        "waiting_for_redeem_code": [],
        "user_earn_target": {}
    }

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتابیس: {e}", flush=True)

db = load_db()

# نام دکمه‌ها (Constants)
BTN_MAIN_MENU = "🔙 بازگشت به منوی اصلی"
BTN_EARN_COINS = "💰 دریافت سکه"
BTN_MY_ACCOUNT = "👤 حساب کاربری من"
BTN_REF_SYSTEM = "👥 دعوت از دوستان"
BTN_INFO_BONUS = "🎁 دریافت جایزه کانال"
BTN_SUPPORT = "📞 پشتیبانی و ارتباط با ما"
BTN_GUIDE = "❓ راهنمای استفاده"
BTN_TRANSFER = "💳 انتقال سکه"
BTN_ORDER_MEMBER = "📢 سفارش جذب ممبر"
BTN_MY_ORDERS = "📋 لیست سفارش‌های من"
BTN_LUCKY_WHEEL = "🎡 گردونه شانس"
BTN_ADMIN_PANEL = "🛠 پنل مدیریت"
BTN_BROADCAST = "📢 ارسال پیام همگانی"
BTN_CREATE_GIFT = "🎁 ساخت کد هدیه"
BTN_REDEEM_GIFT = "🎟 وارد کردن کد هدیه"

# دکمه‌های اختصاصی بخش دریافت سکه
BTN_CHECK_MEMBERSHIP = "✅ بررسی عضویت"

# ارتباط با API بله
def api(method, params=None):
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=params or {}, timeout=30)
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

# کیبوردها
def get_main_keyboard(chat_id):
    keyboard = [
        [BTN_EARN_COINS, BTN_MY_ACCOUNT],
        [BTN_REF_SYSTEM, BTN_MY_ORDERS],
        [BTN_LUCKY_WHEEL, BTN_TRANSFER],
        [BTN_INFO_BONUS, BTN_ORDER_MEMBER],
        [BTN_REDEEM_GIFT, BTN_SUPPORT],
        [BTN_GUIDE]
    ]
    if int(chat_id) == ADMIN_ID:
        keyboard.append([BTN_ADMIN_PANEL])
    return {"keyboard": keyboard, "resize_keyboard": True}

def get_back_keyboard():
    return {"keyboard": [[BTN_MAIN_MENU]], "resize_keyboard": True}

def get_earn_keyboard():
    return {
        "keyboard": [
            [BTN_CHECK_MEMBERSHIP],
            [BTN_MAIN_MENU]
        ],
        "resize_keyboard": True
    }

def is_nickname_taken(name, current_chat_id):
    for cid, u_data in db["users_db"].items():
        if cid != str(current_chat_id) and u_data.get("name") == name:
            return True
    return False

def check_channel_membership(chat_id, channel):
    res = api("getChatMember", {"chat_id": channel, "user_id": chat_id})
    if res.get("ok"):
        status = res["result"].get("status")
        if status in ["member", "administrator", "creator"]:
            return True
    return False

def clear_user_states(str_cid):
    for key in ["waiting_for_name", "waiting_for_channel", "waiting_for_order_link", "waiting_for_broadcast", "waiting_for_new_gift_code", "waiting_for_redeem_code"]:
        if str_cid in db.get(key, []):
            db[key].remove(str_cid)
    for key in ["waiting_for_transfer_dest", "waiting_for_transfer_amount", "waiting_for_order_count", "user_earn_target"]:
        if str_cid in db.get(key, {}):
            del db[key][str_cid]
    save_db(db)

def handle_update(update):
    message = update.get("message")
    if not message:
        return
    
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    str_cid = str(chat_id)
    
    print(f"📩 پیام جدید از {chat_id}: {text}", flush=True)

    if str_cid not in db["wallets"]:
        db["wallets"][str_cid] = 50
        save_db(db)

    if text == BTN_MAIN_MENU:
        clear_user_states(str_cid)
        send_message(chat_id, "🏠 به منوی اصلی بازگشتید.", get_main_keyboard(chat_id))
        return

    if text.startswith("/start") or str_cid in db.get("waiting_for_name", []):
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1 and str_cid not in db["users_db"]:
                ref_id = parts[1]
                if ref_id != str_cid and ref_id in db["wallets"]:
                    db["wallets"][ref_id] = db["wallets"].get(ref_id, 0) + 20
                    send_message(int(ref_id), "🎉 یک نفر با لینک دعوت شما وارد ربات شد و ۲۰ سکه به شما اضافه شد!")
            
            if str_cid not in db["users_db"]:
                db.setdefault("waiting_for_name", []).append(str_cid)
                save_db(db)
                send_message(chat_id, "سلام! به ربات ممبرگیر خوش آمدید. لطفاً یک نام مستعار یکتا برای خودت وارد کن:", get_back_keyboard())
                return
        
        if str_cid in db.get("waiting_for_name", []):
            if is_nickname_taken(text, chat_id):
                send_message(chat_id, "⚠️ این نام قبلاً انتخاب شده است. لطفاً نام دیگری وارد کنید:", get_back_keyboard())
                return
            db["users_db"][str_cid] = {"name": text}
            db["waiting_for_name"].remove(str_cid)
            save_db(db)
            send_message(chat_id, f"🎉 ثبت‌نام تکمیل شد!\n۵۰ سکه هدیه ورود به حساب شما واریز شد.", get_main_keyboard(chat_id))
            return

        send_message(chat_id, "سلام! به منوی اصلی ربات ممبرگیر خوش آمدید.", get_main_keyboard(chat_id))
        return

    if str_cid in db.get("waiting_for_order_link", []):
        db["waiting_for_order_link"].remove(str_cid)
        db.setdefault("waiting_for_order_count", {})[str_cid] = text
        save_db(db)
        send_message(chat_id, "🔢 چه تعداد ممبر نیاز دارید؟ (هر ممبر ۲ سکه - لطفاً تعداد را به عدد وارد کنید):", get_back_keyboard())
        return

    if str_cid in db.get("waiting_for_order_count", {}):
        try:
            count = int(text)
        except:
            send_message(chat_id, "⚠️ لطفاً یک عدد معتبر وارد کنید:", get_back_keyboard())
            return
        
        channel_link = db["waiting_for_order_count"][str_cid]
        total_cost = count * 2
        current_coins = db["wallets"].get(str_cid, 0)

        if total_cost > current_coins:
            send_message(chat_id, f"⚠️ موجودی شما کافی نیست! هزینه کل: {total_cost} سکه، موجودی شما: {current_coins} سکه.", get_main_keyboard(chat_id))
            del db["waiting_for_order_count"][str_cid]
            save_db(db)
            return

        db["wallets"][str_cid] -= total_cost
        db.setdefault("campaigns_db", {})[str_cid] = {
            "channel": channel_link, 
            "count": count, 
            "remaining": count,
            "owner": str_cid
        }
        del db["waiting_for_order_count"][str_cid]
        save_db(db)
        send_message(chat_id, f"✅ سفارش شما با موفقیت ثبت شد!\nکانال: {channel_link}\nتعداد: {count} ممبر\nهزینه کسر شده: {total_cost} سکه.", get_main_keyboard(chat_id))
        return

    if str_cid in db.get("waiting_for_transfer_dest", {}) and str_cid not in db.get("waiting_for_transfer_amount", {}):
        dest_id = text
        if dest_id not in db["wallets"]:
            send_message(chat_id, "⚠️ کاربر مورد نظر در ربات یافت نشد. لطفاً آیدی معتبر وارد کنید:", get_back_keyboard())
            return
        if dest_id == str_cid:
            send_message(chat_id, "⚠️ نمی‌توانید به خودتان سکه انتقال دهید!", get_back_keyboard())
            return
        db["waiting_for_transfer_dest"][str_cid] = dest_id
        db["waiting_for_transfer_amount"][str_cid] = True
        save_db(db)
        send_message(chat_id, "💳 چه تعداد سکه می‌خواهید انتقال دهید؟ (عدد وارد کنید):", get_back_keyboard())
        return

    if str_cid in db.get("waiting_for_transfer_amount", {}):
        try:
            amount = int(text)
        except:
            send_message(chat_id, "⚠️ لطفاً یک عدد معتبر وارد کنید:", get_back_keyboard())
            return
        
        dest_id = db["waiting_for_transfer_dest"][str_cid]
        current_coins = db["wallets"].get(str_cid, 0)
        
        if amount <= 0 or amount > current_coins:
            send_message(chat_id, f"⚠️ موجودی شما کافی نیست. موجودی فعلی: {current_coins}", get_back_keyboard())
            return
        
        db["wallets"][str_cid] -= amount
        db["wallets"][dest_id] = db["wallets"].get(dest_id, 0) + amount
        
        del db["waiting_for_transfer_dest"][str_cid]
        del db["waiting_for_transfer_amount"][str_cid]
        save_db(db)
        
        send_message(chat_id, f"✅ {amount} سکه با موفقیت به کاربر {dest_id} منتقل شد.", get_main_keyboard(chat_id))
        send_message(int(dest_id), f"💳 مبلغ {amount} سکه از طرف کاربر {chat_id} به حساب شما واریز شد!")
        return

    if str_cid in db.get("waiting_for_redeem_code", []):
        db["waiting_for_redeem_code"].remove(str_cid)
        save_db(db)
        
        code = text
        gift_data = db["gift_codes_db"].get(code)
        if not gift_data:
            send_message(chat_id, "❌ این کد هدیه معتبر نیست یا وجود ندارد.", get_main_keyboard(chat_id))
            return
        
        redeemed_users = db.setdefault("user_redeemed_codes", {}).setdefault(code, [])
        if str_cid in redeemed_users:
            send_message(chat_id, "⚠️ شما قبلاً از این کد هدیه استفاده کرده‌اید!", get_main_keyboard(chat_id))
            return
        
        if len(redeemed_users) >= gift_data["max_uses"]:
            send_message(chat_id, "❌ ظرفیت این کد هدیه به پایان رسیده است.", get_main_keyboard(chat_id))
            return
        
        redeemed_users.append(str_cid)
        db["wallets"][str_cid] = db["wallets"].get(str_cid, 0) + gift_data["reward"]
        save_db(db)
        send_message(chat_id, f"🎁 تبریک! کد هدیه با موفقیت اعمال شد و {gift_data['reward']} سکه به شما اضافه شد.", get_main_keyboard(chat_id))
        return

    if str_cid in db.get("waiting_for_new_gift_code", []) and int(chat_id) == ADMIN_ID:
        db["waiting_for_new_gift_code"].remove(str_cid)
        save_db(db)
        try:
            parts = [p.strip() for p in text.split("|")]
            code, reward, max_uses = parts[0], int(parts[1]), int(parts[2])
            db.setdefault("gift_codes_db", {})[code] = {"reward": reward, "max_uses": max_uses}
            save_db(db)
            send_message(chat_id, f"✅ کد هدیه `{code}` با موفقیت ساخته شد!", get_main_keyboard(chat_id))
        except:
            send_message(chat_id, "⚠️ فرمت اشتباه است. ساخت کد لغو شد.", get_main_keyboard(chat_id))
        return

    if str_cid in db.get("waiting_for_broadcast", []) and int(chat_id) == ADMIN_ID:
        db["waiting_for_broadcast"].remove(str_cid)
        save_db(db)
        count = 0
        for uid in db["wallets"]:
            send_message(int(uid), f"📢 اطلاعیه مدیریت:\n\n{text}")
            count += 1
        send_message(chat_id, f"✅ به {count} کاربر ارسال شد.", get_main_keyboard(chat_id))
        return

    if text == BTN_MY_ACCOUNT:
        u_name = db["users_db"].get(str_cid, {}).get("name", "ثبت نشده")
        coins = db["wallets"].get(str_cid, 0)
        msg = f"👤 حساب کاربری شما:\n\n🏷 نام مستعار: {u_name}\n💰 موجودی سکه: {coins}\n🆔 کد کاربری: {chat_id}"
        send_message(chat_id, msg, get_main_keyboard(chat_id))
        return

    if text == BTN_REF_SYSTEM:
        msg = f"👥 سیستم دعوت از دوستان:\n\nبا ارسال لینک دعوت زیر به دوستانتان، به ازای هر ورود ۲۰ سکه هدیه بگیرید!\n\n🔗 کد دعوت (آیدی شما):\n`{chat_id}`"
        send_message(chat_id, msg, get_main_keyboard(chat_id))
        return

    # بخش لیست سفارش‌های کاربر
    if text == BTN_MY_ORDERS:
        campaigns = db.get("campaigns_db", {})
        user_camp = campaigns.get(str_cid)
        
        if not user_camp:
            send_message(chat_id, "📋 شما در حال حاضر هیچ سفارش فعالی ثبت نکرده‌اید.", get_main_keyboard(chat_id))
            return
        
        channel = user_camp.get("channel")
        total_count = user_camp.get("count", 0)
        remaining = user_camp.get("remaining", 0)
        received = total_count - remaining
        
        status_text = "🟢 در حال انجام (فعال)" if remaining > 0 else "✅ تکمیل شده"
        
        msg = (
            f"📋 جزئیات آخرین سفارش شما:\n\n"
            f"📢 کانال/گروه: {channel}\n"
            f"📊 تعداد کل درخواستی: {total_count} ممبر\n"
            f"✅ جذب‌شده: {received} ممبر\n"
            f"⏳ باقیمانده: {remaining} ممبر\n"
            f"📌 وضعیت: {status_text}"
        )
        send_message(chat_id, msg, get_main_keyboard(chat_id))
        return

    # بخش دریافت سکه با دکمه بررسی عضویت و بازگشت به صفحه اصلی
    if text == BTN_EARN_COINS:
        user_earn_target = db.setdefault("user_earn_target", {})
        
        campaigns = db.get("campaigns_db", {})
        valid_campaigns = []
        for owner_id, camp in campaigns.items():
            if owner_id != str_cid and camp.get("remaining", 0) > 0:
                rewarded_users = camp.setdefault("rewarded_users", [])
                if str_cid not in rewarded_users:
                    valid_campaigns.append((owner_id, camp))

        if not valid_campaigns:
            send_message(chat_id, "🎁 در حال حاضر کانال فعالی برای دریافت سکه وجود ندارد!\nلطفاً بعداً دوباره امتحان کنید یا خودتان سفارش ممبر ثبت کنید.", get_main_keyboard(chat_id))
            return

        owner_id, camp = random.choice(valid_campaigns)
        target_channel = camp["channel"]

        user_earn_target[str_cid] = {
            "owner_id": owner_id,
            "channel": target_channel
        }
        save_db(db)

        msg = (
            f"💰 بخش دریافت سکه:\n\n"
            f"لطفاً ابتدا در کانال زیر عضو شوید:\n"
            f"🔗 {target_channel}\n\n"
            f"سپس پس از عضویت، روی دکمه **«بررسی عضویت ✅»** در زیر صفحه بزنید تا ۵ سکه هدیه بگیرید!"
        )
        send_message(chat_id, msg, get_earn_keyboard())
        return

    if text == BTN_CHECK_MEMBERSHIP:
        user_earn_target = db.setdefault("user_earn_target", {})
        if str_cid not in user_earn_target:
            send_message(chat_id, "⚠️ شما هنوز کانالی برای دریافت سکه انتخاب نکرده‌اید. روی «دریافت سکه» بزنید.", get_main_keyboard(chat_id))
            return

        target_info = user_earn_target[str_cid]
        owner_id = target_info["owner_id"]
        target_channel = target_info["channel"]

        campaigns = db.get("campaigns_db", {})
        if owner_id in campaigns and campaigns[owner_id].get("remaining", 0) > 0:
            camp = campaigns[owner_id]
            if check_channel_membership(chat_id, target_channel):
                camp.setdefault("rewarded_users", []).append(str_cid)
                camp["remaining"] -= 1
                db["wallets"][str_cid] = db["wallets"].get(str_cid, 0) + 5
                del user_earn_target[str_cid]
                save_db(db)
                send_message(chat_id, f"🎉 تبریک! عضویت شما در کانال {target_channel} تأیید شد و ۵ سکه به حساب شما واریز گردید.", get_main_keyboard(chat_id))
                return
            else:
                send_message(chat_id, f"⚠️ شما هنوز در کانال زیر عضو نشده‌اید:\n🔗 {target_channel}\n\nلطفاً ابتدا عضو شوید و سپس دوباره روی «بررسی عضویت ✅» بزنید.", get_earn_keyboard())
                return
        else:
            del user_earn_target[str_cid]
            save_db(db)
            send_message(chat_id, "❌ این کمپین به پایان رسیده است. لطفاً دوباره روی «دریافت سکه» بزنید تا کانال جدیدی به شما نشان داده شود.", get_main_keyboard(chat_id))
            return

    if text == BTN_INFO_BONUS:
        if str_cid in db["rewarded_info_channel"]:
            send_message(chat_id, "🎁 شما قبلاً جایزه این کانال را دریافت کرده‌اید!", get_main_keyboard(chat_id))
        else:
            if check_channel_membership(chat_id, INFO_CHANNEL):
                db["rewarded_info_channel"].append(str_cid)
                db["wallets"][str_cid] = db["wallets"].get(str_cid, 0) + 30
                save_db(db)
                send_message(chat_id, "🎁 تبریک! ۳۰ سکه هدیه عضویت در کانال اطلاع‌رسانی به حساب شما واریز شد.", get_main_keyboard(chat_id))
            else:
                send_message(chat_id, f"⚠️ ابتدا باید در کانال زیر عضو شوید:\n{INFO_CHANNEL}\n\nسپس دوباره روی این دکمه بزنید.", get_main_keyboard(chat_id))
        return

    if text == BTN_LUCKY_WHEEL:
        last_time = db["last_lucky_wheel"].get(str_cid, 0)
        if time.time() - last_time < 86400:
            remaining = int((86400 - (time.time() - last_time)) / 3600)
            send_message(chat_id, f"🎡 شما امروز از گردونه شانس استفاده کرده‌اید. لطفاً پس از {remaining} ساعت دوباره امتحان کنید.", get_main_keyboard(chat_id))
        else:
            prize = random.choice([10, 20, 50, 100, 0, 30])
            db["last_lucky_wheel"][str_cid] = time.time()
            db["wallets"][str_cid] = db["wallets"].get(str_cid, 0) + prize
            save_db(db)
            send_message(chat_id, f"🎡 چرخ گردونه چرخید و شما برنده {prize} سکه شدید! 🎉", get_main_keyboard(chat_id))
        return

    if text == BTN_ORDER_MEMBER:
        db.setdefault("waiting_for_order_link", []).append(str_cid)
        save_db(db)
        send_message(chat_id, "📢 لطفاً لینک یا آیدی کانال/گروه خود را ارسال کنید (مثلاً `@my_channel`):", get_back_keyboard())
        return

    if text == BTN_TRANSFER:
        db.setdefault("waiting_for_transfer_dest", {})[str_cid] = True
        save_db(db)
        send_message(chat_id, "💳 لطفاً آیدی عددی (Chat ID) کاربر مقصد را وارد کنید:", get_back_keyboard())
        return

    if text == BTN_REDEEM_GIFT:
        db.setdefault("waiting_for_redeem_code", []).append(str_cid)
        save_db(db)
        send_message(chat_id, "🎟 لطفاً کد هدیه خود را وارد کنید:", get_back_keyboard())
        return

    if text == BTN_SUPPORT:
        support_msg = (
            f"📞 پشتیبانی و ارتباط با ما:\n\n"
            f"👤 آیدی پشتیبان: {ADMIN_USERNAME}\n"
            f"📢 کانال اطلاع‌رسانی و پشتیبانی: {SUPPORT_CHANNEL}\n\n"
            f"برای هرگونه سوال، پیشنهاد یا مشکل می‌توانید از طریق راه‌های فوق با ما در ارتباط باشید."
        )
        send_message(chat_id, support_msg, get_main_keyboard(chat_id))
        return

    if text == BTN_GUIDE:
        guide_text = (
            "❓ راهنمای کامل استفاده از ربات ممبرگیر:\n\n"
            "1️⃣ **دریافت سکه (💰):** با عضویت در کانال‌های ثبت‌شده توسط کاربران، به ازای هر کانال ۵ سکه رایگان دریافت کنید.\n"
            "2️⃣ **دعوت از دوستان (👥):** لینک یا آیدی خود را به دوستانتان بدهید؛ با ورود هر نفر، ۲۰ سکه هدیه بگیرید.\n"
            "3️⃣ **سفارش جذب ممبر (📢):** کانال خود را ثبت کنید و به ازای هر ممبر تنها ۲ سکه بپردازید.\n"
            "4️⃣ **لیست سفارش‌ها (📋):** وضعیت پیشرفت و تعداد ممبرهای جذب‌شده کانال خود را مشاهده کنید.\n"
            "5️⃣ **گردونه شانس و کد هدیه (🎡):** هر روز شانس خود را امتحان کنید یا کدهای هدیه را وارد کنید."
        )
        send_message(chat_id, guide_text, get_main_keyboard(chat_id))
        return

    if text == BTN_ADMIN_PANEL and int(chat_id) == ADMIN_ID:
        admin_keyboard = {
            "keyboard": [
                [BTN_BROADCAST, BTN_CREATE_GIFT],
                [BTN_MAIN_MENU]
            ],
            "resize_keyboard": True
        }
        send_message(chat_id, "🛠 پنل مدیریت:", admin_keyboard)
        return

    if text == BTN_CREATE_GIFT and int(chat_id) == ADMIN_ID:
        db.setdefault("waiting_for_new_gift_code", []).append(str_cid)
        save_db(db)
        send_message(chat_id, "🎁 ساخت کد هدیه:\nلطفاً به این فرمت بفرستید:\n`کد | مقدار سکه | تعداد استفاده`\nمثال: `gift100 | 50 | 10`", get_back_keyboard())
        return

    if text == BTN_BROADCAST and int(chat_id) == ADMIN_ID:
        db.setdefault("waiting_for_broadcast", []).append(str_cid)
        save_db(db)
        send_message(chat_id, "📢 متن پیام همگانی را بفرستید:", get_back_keyboard())
        return

    send_message(chat_id, "دستور نامعتبر است. از دکمه‌های زیر استفاده کنید:", get_main_keyboard(chat_id))

def keep_alive():
    while True:
        try:
            url = os.environ.get("RENDER_EXTERNAL_URL", "https://member-gir-bot.onrender.com")
            requests.get(url, timeout=10)
            print("🔄 پینگ خودکار انجام شد.", flush=True)
        except Exception as e:
            print(f"⚠️ خطای پینگ خودکار: {e}", flush=True)
        time.sleep(180)

def main():
    try:
        requests.get(f"{BASE_URL}/deleteWebhook", timeout=15)
        print("🧹 وبهوک پاک شد.", flush=True)
    except:
        pass

    me = api("getMe")
    if me.get("ok"):
        print(f"🤖 متصل به ربات: @{me['result'].get('username')}", flush=True)
    else:
        print(f"❌ خطا در اتصال: {me}", flush=True)

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
                        print(f"❌ خطای پردازش: {e}", flush=True)
            else:
                time.sleep(2)
        except Exception as e:
            print(f"❌ خطای حلقه اصلی: {e}", flush=True)
            time.sleep(3)

if __name__ == "__main__":
    threading.Thread(target=keep_alive, daemon=True).start()
    main()
