# ==========================================================
# بخش صفر: ایمپورت‌های ضروری
# ==========================================================
import os
import time
import json
import random
import threading
import requests
from flask import Flask, request
from datetime import datetime
import sys
sys.stdout.reconfigure(line_buffering=True)


# --- تنظیمات اصلی ---
ADMIN_ID = 1708788049  # ← chat_id خودت
BOT_TOKEN = os.getenv("BOT_TOKEN", "546304737:fs7cQXqPES3D80hDcCxCfxHIwWfWr6ureuo")
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"   # ← اصلاح شد
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL", "")

# نام فایل دیتابیس
DB_FILE = "bot_database.json"

# --- مدیریت دیتابیس (JSON) ---
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading DB: {e}")
            return {}
    return {}

def save_db(db):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error saving DB: {e}")

# بارگذاری اولیه دیتابیس
db = load_db()

# --- توابع کمکی API بله ---
def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        post(f"{BASE_URL}/sendMessage", json=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_updates():
    try:
        response = get(f"{BASE_URL}/getUpdates")
        if response.status_code == 200:
            return response.json().get("result", [])
        return []
    except Exception as e:
        print(f"Error getting updates: {e}")
        return []

# --- تنظیمات Flask برای Render ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)
# ==========================================================
# بخش دوم: توابع کمکی کاربر، کیف پول و کیبوردها
# ==========================================================

def now_ts():
    return int(time.time())

def get_user(chat_id):
    """کاربر را برمی‌گرداند و اگر نبود، می‌سازد."""
    cid = str(chat_id)
    if "users_db" not in db:
        db["users_db"] = {}
    if cid not in db["users_db"]:
        db["users_db"][cid] = {
            "name": None,
            "coins": 50,
            "joined_at": now_ts(),
            "referred_by": None,
            "is_admin": False
        }
        save_db(db)
    return db["users_db"][cid]

def get_coins(chat_id):
    return get_user(chat_id).get("coins", 0)

def add_coins(chat_id, amount):
    u = get_user(chat_id)
    u["coins"] = max(0, u.get("coins", 0) + amount)
    save_db(db)
    return u["coins"]

def set_user_state(chat_id, state, value=True):
    """وضعیت انتظار کاربر را تنظیم می‌کند."""
    if "states" not in db:
        db["states"] = {}
    db["states"][str(chat_id)] = {state: value}
    save_db(db)

def clear_user_state(chat_id):
    if "states" in db:
        db["states"].pop(str(chat_id), None)
        save_db(db)

def get_user_state(chat_id):
    return db.get("states", {}).get(str(chat_id), {})

def is_nickname_taken(name, current_chat_id=None):
    """بررسی تکراری نبودن نام مستعار."""
    for cid, u in db.get("users_db", {}).items():
        if u.get("name") == name and cid != str(current_chat_id):
            return True
    return False

def get_name(chat_id):
    u = get_user(chat_id)
    return u.get("name") or "کاربر"

def is_admin(chat_id):
    # ادمین اصلی همیشه ادمین است
    if str(chat_id) == str(ADMIN_ID):
        return True
    return get_user(chat_id).get("is_admin", False)


# ---------- کیبوردها ----------
BTN_ADVERTISE = "📢 ثبت تبلیغ کانال (جذب ممبر)"
BTN_BUY_CHANNEL = "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)"
BTN_MY_ADS = "📋 لیست تبلیغ‌های من"
BTN_MY_CUSTOM = "📂 لیست کانال/گروه‌های سفارشی"
BTN_DELETE_AD = "🗑️ حذف تبلیغ کانال"
BTN_ADMIN = "🛠 پنل مدیریت"
BTN_EARN = "💰 دریافت سکه"
BTN_INVITE = "👥 دعوت از دوستان"
BTN_INFO_BONUS = "🎁 دریافت جایزه کانال"
BTN_TRANSFER = "💳 انتقال سکه"
BTN_WHEEL = "🎡 گردونه شانس"
BTN_GIFT = "🎁 وارد کردن کد هدیه"
BTN_MAKE_GIFT = "🎁 ساخت کد هدیه"
BTN_HELP = "❓ راهنمای استفاده"
BTN_SUPPORT = "📞 پشتیبانی و ارتباط با ما"
BTN_CHANGE_NAME = "✏️ تغییر نام مستعار"
BTN_BACK = "🔙 بازگشت به منوی اصلی"
BTN_CHECK = "✅ بررسی عضویت"


def main_menu_keyboard():
    return {
        "keyboard": [
            [{"text": BTN_ADVERTISE}],
            [{"text": BTN_BUY_CHANNEL}],
            [{"text": BTN_MY_ADS}, {"text": BTN_MY_CUSTOM}],
            [{"text": BTN_DELETE_AD}, {"text": BTN_EARN}],
            [{"text": BTN_INVITE}, {"text": BTN_INFO_BONUS}],
            [{"text": BTN_TRANSFER}, {"text": BTN_WHEEL}],
            [{"text": BTN_GIFT}, {"text": BTN_MAKE_GIFT}],
            [{"text": BTN_CHANGE_NAME}, {"text": BTN_HELP}],
            [{"text": BTN_SUPPORT}],
            [{"text": BTN_BACK}]
        ],
        "resize_keyboard": True
    }

def back_keyboard():
    return {
        "keyboard": [[{"text": BTN_BACK}]],
        "resize_keyboard": True
    }

def check_keyboard():
    return {
        "keyboard": [[{"text": BTN_CHECK}], [{"text": BTN_BACK}]],
        "resize_keyboard": True
    }

def admin_keyboard():
    return {
        "keyboard": [
            [{"text": "📢 ارسال پیام همگانی"}],
            [{"text": "🎁 ساخت کد هدیه"}],
            [{"text": "📊 آمار ربات"}],
            [{"text": BTN_BACK}]
        ],
        "resize_keyboard": True
    }
# ==========================================================
# بخش سوم: پردازش پیام‌ها
# ==========================================================

def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if not chat_id:
        return
    cid = str(chat_id)

    # ✅ پاکسازی متن: حذف فاصله‌های اضافی و نیم‌فاصله‌های مشکل‌ساز
    raw_text = message.get("text", "")
    text = str(raw_text).strip().replace("\u200c", " ")

    # ساخت کاربر در صورت نبود
    user = get_user(chat_id)
    state = get_user_state(chat_id)

    # ============ /start ============
    if text.startswith("/start"):
        parts = text.split()
        # ثبت معرف (کد دعوت = chat_id دعوت‌کننده)
        if len(parts) > 1 and user.get("referred_by") is None:
            ref_code = parts[1].strip()
            if ref_code.isdigit() and ref_code != cid and ref_code in db.get("users_db", {}):
                user["referred_by"] = ref_code
                add_coins(ref_code, 10)
                add_coins(chat_id, 10)
                save_db(db)
                send_message(ref_code, "🎉 یکی از دوستانت با کد تو وارد شد! ۱۰ سکه گرفتی.")
                send_message(chat_id, "🎉 ۱۰ سکه بابت استفاده از کد دعوت دریافت کردی!")

        if not user.get("name"):
            set_user_state(chat_id, "waiting_for_name")
            send_message(chat_id, "👋 سلام! به ربات ممبرگیر خوش اومدی.\n\n"
                                  "لطفاً یک **نام مستعار** برای خودت انتخاب کن.\n"
                                  "(نام نباید تکراری باشه)", back_keyboard())
            return

        send_message(chat_id,
                     f"سلام {user['name']} عزیز! 👋\n"
                     f"💰 موجودی سکه: {user.get('coins', 0)}\n\n"
                     "از منوی زیر انتخاب کن:",
                     main_menu_keyboard())
        return

    # ============ بازگشت به منوی اصلی ============
    if BTN_BACK in text:
        clear_user_state(chat_id)
        send_message(chat_id,
                     f"🏠 منوی اصلی\n💰 موجودی: {user.get('coins', 0)} سکه",
                     main_menu_keyboard())
        return

    # ============ حالت‌های انتظار (State Machine) ============
    if state.get("waiting_for_name"):
        name = text
        if len(name) < 2 or len(name) > 20:
            send_message(chat_id, "❌ نام باید بین ۲ تا ۲۰ کاراکتر باشه. دوباره بفرست:", back_keyboard())
            return
        if is_nickname_taken(name, chat_id):
            send_message(chat_id, "❌ این نام قبلاً گرفته شده. یه نام دیگه بفرست:", back_keyboard())
            return
        user["name"] = name
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ نام «{name}» ثبت شد!\n💰 هدیه ثبت‌نام: ۵۰ سکه",
                     main_menu_keyboard())
        return

    if state.get("waiting_for_name_change"):
        name = text
        if len(name) < 2 or len(name) > 20:
            send_message(chat_id, "❌ نام باید بین ۲ تا ۲۰ کاراکتر باشه:", back_keyboard())
            return
        if is_nickname_taken(name, chat_id):
            send_message(chat_id, "❌ این نام قبلاً گرفته شده. یه نام دیگه بفرست:", back_keyboard())
            return
        user["name"] = name
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ نام مستعارت به «{name}» تغییر کرد.", main_menu_keyboard())
        return

    if state.get("waiting_for_gift_code"):
        code = text.upper()
        gift = db.get("gift_codes_db", {}).get(code)
        if not gift:
            send_message(chat_id, "❌ کد هدیه نامعتبره.", back_keyboard())
            return
        redeemed = db.setdefault("user_redeemed_codes", {}).setdefault(cid, [])
        if code in redeemed:
            send_message(chat_id, "⚠️ قبلاً از این کد استفاده کردی.", back_keyboard())
            return
        if gift.get("used", 0) >= gift.get("max_uses", 1):
            send_message(chat_id, "😔 ظرفیت این کد پر شده.", back_keyboard())
            return
        gift["used"] = gift.get("used", 0) + 1
        redeemed.append(code)
        add_coins(chat_id, gift.get("amount", 0))
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id, f"🎉 تبریک! {gift.get('amount', 0)} سکه دریافت کردی.\n"
                              f"💰 موجودی: {get_coins(chat_id)}", main_menu_keyboard())
        return

    if state.get("waiting_for_channel"):
        channel = text
        if not channel.startswith("@") or len(channel) < 4:
            send_message(chat_id, "❌ آیدی کانال باید با @ شروع بشه. مثال: @my_channel", back_keyboard())
            return
        if get_coins(chat_id) < 50:
            send_message(chat_id, "❌ سکه کافی نداری! (۵۰ سکه لازمه)", back_keyboard())
            return
        add_coins(chat_id, -50)
        camp_id = str(now_ts())
        db.setdefault("campaigns_db", {})[camp_id] = {
            "owner": cid, "channel": channel, "views": 0,
            "created_at": now_ts(), "status": "active"
        }
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id,
                     f"✅ تبلیغ ثبت شد!\n📢 کانال: {channel}\n"
                     f"💰 ۵۰ سکه کسر شد. موجودی: {get_coins(chat_id)}\n\n"
                     "📖 برای ادامه، ربات رو ادمین کانال کن:\n"
                     "1️⃣ کانال → مدیریت → ادمین‌ها\n"
                     "2️⃣ ربات رو جستجو و ادمین کن\n"
                     "3️⃣ دسترسی «افزودن کاربر» رو فعال کن",
                     main_menu_keyboard())
        return

    if state.get("waiting_for_transfer_amount"):
        try:
            amount = int(text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            send_message(chat_id, "❌ عدد معتبر بفرست:", back_keyboard())
            return
        if get_coins(chat_id) < amount:
            send_message(chat_id, "❌ سکه کافی نداری.", back_keyboard())
            return
        dest = state.get("transfer_dest")
        if not dest or dest not in db.get("users_db", {}):
            send_message(chat_id, "❌ کاربر مقصد پیدا نشد.", back_keyboard())
            clear_user_state(chat_id)
            return
        add_coins(chat_id, -amount)
        add_coins(dest, amount)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ {amount} سکه به {get_name(dest)} منتقل شد.\n"
                              f"💰 موجودی: {get_coins(chat_id)}", main_menu_keyboard())
        send_message(dest, f"💳 {amount} سکه از {get_name(chat_id)} دریافت کردی!")
        return

    if state.get("waiting_for_transfer_dest"):
        dest_code = text.strip()
        if dest_code not in db.get("users_db", {}):
            send_message(chat_id, "❌ کد دعوت نامعتبره.", back_keyboard())
            return
        if dest_code == cid:
            send_message(chat_id, "❌ نمی‌تونی به خودت انتقال بدی.", back_keyboard())
            return
        clear_user_state(chat_id)
        set_user_state(chat_id, "waiting_for_transfer_amount")
        db["states"][cid]["transfer_dest"] = dest_code
        save_db(db)
        send_message(chat_id, f"👤 مقصد: {get_name(dest_code)}\n"
                              "حالا مقدار سکه رو بفرست:", back_keyboard())
        return

    if state.get("waiting_for_group_name"):
        add_coins(chat_id, -1000)
        gid = str(now_ts())
        db.setdefault("created_groups_db", {})[gid] = {
            "owner": cid, "name": text, "created_at": now_ts()
        }
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ سفارش ثبت شد!\n📛 نام: {text}\n"
                              "ادمین به‌زودی با تو تماس می‌گیره.", main_menu_keyboard())
        return

    if state.get("waiting_for_broadcast") and is_admin(chat_id):
        count = 0
        for ucid in list(db.get("users_db", {}).keys()):
            send_message(ucid, f"📢 اطلاعیه:\n\n{text}")
            count += 1
            time.sleep(0.05)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ پیام به {count} کاربر ارسال شد.", admin_keyboard())
        return

    if state.get("waiting_for_new_gift_code") and is_admin(chat_id):
        # فرمت: CODE AMOUNT MAX_USES
        parts = text.split()
        if len(parts) != 3:
            send_message(chat_id, "❌ فرمت درست: CODE AMOUNT MAX_USES\nمثال: EID1404 100 20", back_keyboard())
            return
        code, amount, max_uses = parts[0].upper(), parts[1], parts[2]
        if not amount.isdigit() or not max_uses.isdigit():
            send_message(chat_id, "❌ مقدار و تعداد باید عدد باشن.", back_keyboard())
            return
        db.setdefault("gift_codes_db", {})[code] = {
            "amount": int(amount), "max_uses": int(max_uses), "used": 0
        }
        save_db(db)
        clear_user_state(chat_id)
        send_message(chat_id, f"✅ کد «{code}» ساخته شد.\n"
                              f"💰 {amount} سکه × {max_uses} نفر", admin_keyboard())
        return

    # ============ دکمه‌های منوی اصلی ============
    if BTN_HELP in text:
        send_message(chat_id,
                     "📖 راهنمای استفاده\n\n"
                     "1️⃣ ثبت تبلیغ کانال (۵۰ سکه) → ۲۵ بازدید\n"
                     "2️⃣ دعوت دوستان → ۱۰ سکه برای هر نفر\n"
                     "3️⃣ دریافت سکه → با عضویت در کانال‌ها\n"
                     "4️⃣ کد هدیه → دریافت سکه رایگان\n"
                     "5️⃣ انتقال سکه → به دوستانت سکه بده\n"
                     "6️⃣ گردونه شانس → روزی یک بار\n\n"
                     "📞 پشتیبانی: @kia_karfarma",
                     back_keyboard())
        return

    if BTN_SUPPORT in text:
        send_message(chat_id,
                     "📞 پشتیبانی و ارتباط با ما\n\n"
                     "ادمین: @kia_karfarma\n"
                     "کانال اطلاع‌رسانی: @ettela_resani_member",
                     back_keyboard())
        return

    if BTN_CHANGE_NAME in text:
        set_user_state(chat_id, "waiting_for_name_change")
        send_message(chat_id, "✏️ نام مستعار جدیدت رو بفرست:", back_keyboard())
        return

    if BTN_GIFT in text:
        set_user_state(chat_id, "waiting_for_gift_code")
        send_message(chat_id, "🎁 کد هدیه‌ات رو بفرست:", back_keyboard())
        return

    if BTN_INVITE in text:
        send_message(chat_id,
                     f"👥 دعوت از دوستان\n\n"
                     f"🔑 کد دعوت تو: `{cid}`\n\n"
                     "دوستانت باید این کد رو در ربات وارد کنن:\n"
                     f"/start {cid}\n\n"
                     "💰 برای هر نفر ۱۰ سکه می‌گیری!",
                     back_keyboard())
        return

    if BTN_INFO_BONUS in text:
        if db.get("rewarded_info_channel", {}).get(cid):
            send_message(chat_id, "⚠️ قبلاً این جایزه رو گرفتی.", back_keyboard())
            return
        send_message(chat_id,
                     "🎁 برای دریافت ۱۰ سکه، اول عضو کانال ما شو:\n"
                     "@ettela_resani_member\n\n"
                     "بعد دکمه زیر رو بزن:",
                     check_keyboard())
        return

    if BTN_EARN in text:
        # جریمه خروج از کانال‌ها (۳ سکه به ازای هر کانال)
        camp_count = len(db.get("campaigns_db", {}))
        send_message(chat_id,
                     f"💰 دریافت سکه\n\n"
                     f"📢 تعداد تبلیغ‌های فعال: {camp_count}\n\n"
                     "برای دریافت ۵ سکه، عضو کانال‌ها شو و دکمه بررسی رو بزن:\n"
                     "⚠️ اگر بعداً لفت بدی، ۳ سکه جریمه می‌شی.",
                     check_keyboard())
        return

    if BTN_CHECK in text:
        # ضد اسپم: ۳ ثانیه کول‌داون
        last = db.setdefault("last_check", {}).get(cid, 0)
        if now_ts() - last < 3:
            send_message(chat_id, "⏳ کمی صبر کن، دوباره تلاش نکن.", check_keyboard())
            return
        db["last_check"][cid] = now_ts()
        save_db(db)

        # بررسی عضویت واقعی در کانال اطلاع‌رسانی
        try:
            r = get(f"{BASE_URL}/getChatMember",
                    params={"chat_id": "@ettela_resani_member", "user_id": chat_id}).json()
            status = r.get("result", {}).get("status", "")
            is_member = status in ("member", "administrator", "creator")
        except Exception:
            is_member = False

        if is_member:
            if not db.setdefault("rewarded_info_channel", {}).get(cid):
                db["rewarded_info_channel"][cid] = True
                add_coins(chat_id, 10)
                save_db(db)
                send_message(chat_id, f"✅ عضویت تایید شد! ۱۰ سکه گرفتی.\n"
                                      f"💰 موجودی: {get_coins(chat_id)}", main_menu_keyboard())
            else:
                add_coins(chat_id, 5)
                send_message(chat_id, f"✅ عضویت تایید شد! ۵ سکه گرفتی.\n"
                                      f"💰 موجودی: {get_coins(chat_id)}", main_menu_keyboard())
        else:
            send_message(chat_id,
                         "❌ هنوز عضو کانال نیستی!\n"
                         "اول عضو شو: @ettela_resani_member",
                         check_keyboard())
        return

    if BTN_TRANSFER in text:
        set_user_state(chat_id, "waiting_for_transfer_dest")
        send_message(chat_id, "💳 کد دعوت (chat_id) کاربر مقصد رو بفرست:", back_keyboard())
        return

    if BTN_WHEEL in text:
        last = db.setdefault("last_lucky_wheel", {}).get(cid, 0)
        if now_ts() - last < 86400:
            remain = 86400 - (now_ts() - last)
            hours = remain // 3600
            send_message(chat_id, f"⏳ گردونه امروز استفاده شد.\n"
                                  f"⏰ {hours} ساعت دیگه بیا.", back_keyboard())
            return
        prize = random.choice([0, 5, 10, 15, 25, 50])
        db["last_lucky_wheel"][cid] = now_ts()
        add_coins(chat_id, prize)
        save_db(db)
        if prize == 0:
            send_message(chat_id, "🎡 گردونه چرخید... 😢 متاسفانه هیچی نبردی!\n"
                                  "فردا دوباره شانس بیار.", main_menu_keyboard())
        else:
            send_message(chat_id, f"🎡 گردونه چرخید... 🎉 {prize} سکه بردی!\n"
                                  f"💰 موجودی: {get_coins(chat_id)}", main_menu_keyboard())
        return

    if BTN_ADVERTISE in text:
        set_user_state(chat_id, "waiting_for_channel")
        send_message(chat_id,
                     "📢 ثبت تبلیغ کانال\n\n"
                     "💰 هزینه: ۵۰ سکه\n"
                     "👁 بازدید تضمینی: ۲۵ نفر\n\n"
                     "آیدی کانالت رو با @ بفرست:\n"
                     "مثال: @my_channel",
                     back_keyboard())
        return

    if BTN_MY_ADS in text:
        camps = {k: v for k, v in db.get("campaigns_db", {}).items() if v.get("owner") == cid}
        if not camps:
            send_message(chat_id, "📋 هنوز هیچ تبلیغی ثبت نکردی.", back_keyboard())
            return
        lines = ["📋 لیست تبلیغ‌های من:\n"]
        for k, v in camps.items():
            lines.append(f"📢 {v['channel']} — 👁 {v.get('views', 0)} بازدید")
        send_message(chat_id, "\n".join(lines), back_keyboard())
        return

    if BTN_MY_CUSTOM in text:
        groups = {k: v for k, v in db.get("created_groups_db", {}).items() if v.get("owner") == cid}
        if not groups:
            send_message(chat_id, "📂 هنوز سفارشی ثبت نکردی.", back_keyboard())
            return
        lines = ["📂 کانال/گروه‌های سفارشی من:\n"]
        for k, v in groups.items():
            lines.append(f"📛 {v['name']}")
        send_message(chat_id, "\n".join(lines), back_keyboard())
        return

    if BTN_DELETE_AD in text:
        camps = {k: v for k, v in db.get("campaigns_db", {}).items() if v.get("owner") == cid}
        if not camps:
            send_message(chat_id, "🗑️ تبلیغی برای حذف نداری.", back_keyboard())
            return
        set_user_state(chat_id, "waiting_for_deletion")
        lines = ["🗑️ آیدی کانال مورد نظر رو بفرست:\n"]
        for v in camps.values():
            lines.append(f"• {v['channel']}")
        send_message(chat_id, "\n".join(lines), back_keyboard())
        return

    if state.get("waiting_for_deletion"):
        target = text
        removed = False
        for k, v in list(db.get("campaigns_db", {}).items()):
            if v.get("owner") == cid and v.get("channel") == target:
                del db["campaigns_db"][k]
                removed = True
        if removed:
            save_db(db)
            clear_user_state(chat_id)
            send_message(chat_id, f"✅ تبلیغ {target} حذف شد.", main_menu_keyboard())
        else:
            send_message(chat_id, "❌ چنین تبلیغی پیدا نشد.", back_keyboard())
        return

    if BTN_BUY_CHANNEL in text:
        if get_coins(chat_id) < 1000:
            send_message(chat_id, f"❌ سکه کافی نداری!\n"
                                  f"💰 موجودی: {get_coins(chat_id)} / ۱۰۰۰", back_keyboard())
            return
        set_user_state(chat_id, "waiting_for_group_name")
        send_message(chat_id, "✨ نام کانال/گروهی که می‌خوای ساخته بشه رو بفرست:", back_keyboard())
        return

    if BTN_ADMIN in text:
        if not is_admin(chat_id):
            send_message(chat_id, "❌ این بخش فقط برای ادمین‌هاست.", back_keyboard())
            return
        send_message(chat_id, "🛠 پنل مدیریت\nیکی از گزینه‌ها رو انتخاب کن:", admin_keyboard())
        return

    if is_admin(chat_id):
        if "ارسال پیام همگانی" in text:
            set_user_state(chat_id, "waiting_for_broadcast")
            send_message(chat_id, "📢 متن پیام همگانی رو بفرست:", back_keyboard())
            return
        if BTN_MAKE_GIFT in text:
            set_user_state(chat_id, "waiting_for_new_gift_code")
            send_message(chat_id,
                         "🎁 ساخت کد هدیه\n\n"
                         "فرمت: CODE AMOUNT MAX_USES\n"
                         "مثال: EID1404 100 20\n"
                         "(یعنی کد EID1404، هر نفر ۱۰۰ سکه، حداکثر ۲۰ نفر)",
                         back_keyboard())
            return
        if "آمار ربات" in text:
            stats = (f"📊 آمار ربات\n\n"
                     f"👥 کاربران: {len(db.get('users_db', {}))}\n"
                     f"📢 تبلیغ‌ها: {len(db.get('campaigns_db', {}))}\n"
                     f"🎁 کدهای هدیه: {len(db.get('gift_codes_db', {}))}\n"
                     f"📂 سفارش‌ها: {len(db.get('created_groups_db', {}))}")
            send_message(chat_id, stats, admin_keyboard())
            return

    if BTN_MAKE_GIFT in text and not is_admin(chat_id):
        send_message(chat_id, "❌ فقط ادمین می‌تونه کد هدیه بسازه.", back_keyboard())
        return

    # ============ پیام نامشخص ============
    send_message(chat_id,
                 "🤔 متوجه نشدم!\nاز منوی زیر انتخاب کن:",
                 main_menu_keyboard())
# ==========================================================
# بخش چهارم: حلقه اصلی، سرور Flask و بیدارنگه‌دارنده
# ==========================================================

# ---------- توابع کمکی (اگر در بخش دوم نداری، این‌ها را نگه دار) ----------
def now_ts():
    return int(time.time())


def get_coins(chat_id):
    return db.get("users_db", {}).get(str(chat_id), {}).get("coins", 0)


def get_name(chat_id):
    return db.get("users_db", {}).get(str(chat_id), {}).get("name", "کاربر")


def is_admin(chat_id):
    try:
        return int(chat_id) == int(ADMIN_ID)
    except Exception:
        return False


def api(method, params=None):
    """درخواست امن به API بله با مدیریت خطا"""
    try:
        r = requests.post(f"{BASE_URL}/{method}", json=params or {}, timeout=30)
        return r.json()
    except Exception as e:
        print(f"⚠️ خطای API در {method}: {e}")
        return {}


def get_updates(offset=None):
    params = {"timeout": 25}
    if offset:
        params["offset"] = offset
    return api("getUpdates", params)


# ---------- سرور Flask (برای جلوگیری از خواب رفتن Render) ----------
app = Flask(__name__)


@app.route("/")
def home():
    return "✅ ربات ممبرگیر در حال اجراست!", 200


@app.route("/health")
def health():
    return {"status": "ok", "users": len(db.get("users_db", {}))}, 200


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ---------- بیدارنگه‌دارنده (Self-Ping) ----------
def keep_alive():
    """هر ۵ دقیقه به خود Render درخواست می‌زند تا سرویس خواب نرود"""
    time.sleep(60)  # فرصت به سرویس برای بالا آمدن
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                requests.get(url, timeout=15)
                print("🔁 پینگ موفق")
            except Exception as e:
                print(f"⚠️ پینگ ناموفق: {e}")
        time.sleep(300)  # ۵ دقیقه


# ---------- حلقه اصلی ربات ----------
def main():
    print("🚀 ربات ممبرگیر روشن شد...")

    # پاک کردن وبهوک (چون از Polling استفاده می‌کنیم)
    try:
        requests.get(f"{BASE_URL}/deleteWebhook", timeout=20)
        print("🧹 وبهوک پاک شد.")
    except Exception as e:
        print(f"⚠️ پاک کردن وبهوک ناموفق: {e}")

    # بررسی صحت توکن
    me = api("getMe")
    if me.get("ok"):
        print(f"🤖 متصل به ربات: @{me['result'].get('username')}")
    else:
        print(f"❌ توکن نامعتبر است: {me}")
        return

    offset = None
    while True:
        try:
            data = get_updates(offset)
            if not data.get("ok"):
                print(f"⚠️ پاسخ ناموفق: {data.get('description')}")
                time.sleep(3)
                continue

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception as e:
                    print(f"❌ خطا در پردازش آپدیت {update.get('update_id')}: {e}")

            time.sleep(0.5)

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"❌ خطای حلقه اصلی: {e}")
            time.sleep(5)


# ---------- اجرا ----------
if __name__ == "__main__":
    # سرور Flask در ترد جداگانه
    threading.Thread(target=run_flask, daemon=True).start()
    # بیدارنگه‌دارنده در ترد جداگانه
    threading.Thread(target=keep_alive, daemon=True).start()
    # حلقه ربات در ترد اصلی
    main()
