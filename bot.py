import logging
import os
import random
import threading
import time
import requests
from flask import Flask
import json

# تنظیمات لاگینگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# خواندن توکن از متغیرهای محیطی رندر (با مقدار پیش‌فرض شما)
TOKEN = os.environ.get("BOT_TOKEN", "546304737:fs7cQXqPES3D80hDcCxCfxHIwWfWr6ureuo")
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

ADMIN_ID = 1708788049  # شناسه ادمین خودتان را اینجا قرار دهید
INFO_CHANNEL = "@ettela_resani_member"
ADMIN_SUPPORT_USERNAME = "@kia_karfarma"

# پایگاه‌های داده و وضعیت‌ها (ذخیره‌سازی در رم و فایل)
DB_FILE = "bot_database.json"


def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
    return {
        "users_db": {},
        "wallets": {},
        "nicknames": {},
        "campaigns_db": {},
        "history_db": {},
        "rewarded_info_channel": [],
        "user_task": {},
        "created_groups_db": {},
        "gift_codes_db": {},
        "user_redeemed_codes": {},
    }


def save_data():
    data = {
        "users_db": users_db,
        "wallets": wallets,
        "nicknames": nicknames,
        "campaigns_db": campaigns_db,
        "history_db": history_db,
        "rewarded_info_channel": rewarded_info_channel,
        "user_task": user_task,
        "created_groups_db": created_groups_db,
        "gift_codes_db": gift_codes_db,
        "user_redeemed_codes": user_redeemed_codes,
    }
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error saving database: {e}")


db = load_data()
users_db = db.get("users_db", {})
wallets = {int(k): v for k, v in db.get("wallets", {}).items()}
nicknames = {int(k): v for k, v in db.get("nicknames", {}).items()}
campaigns_db = db.get("campaigns_db", {})
history_db = {int(k): v for k, v in db.get("history_db", {}).items()}
rewarded_info_channel = [
    int(x) for x in db.get("rewarded_info_channel", [])
]
user_task = {int(k): v for k, v in db.get("user_task", {}).items()}
created_groups_db = db.get("created_groups_db", {})
gift_codes_db = db.get("gift_codes_db", {})
user_redeemed_codes = {
    int(k): v for k, v in db.get("user_redeemed_codes", {}).items()
}

# وضعیت‌های مکالمه کاربران
waiting_for_name = set()
waiting_for_name_change = set()
waiting_for_channel = set()
waiting_for_deletion = set()
waiting_for_referral_code = set()
waiting_for_group_name = set()
waiting_for_broadcast = set()
waiting_for_gift_code = set()  # برای ساخت کد هدیه توسط ادمین
waiting_for_redeem_code = set()  # برای وارد کردن کد هدیه توسط کاربر
last_click_time = {}

# راه‌اندازی وب‌سایت Flask جهت جلوگیری از خوابیدن ربات روی Render
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running and active!"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


def self_ping():
    while True:
        url = os.environ.get("RENDER_EXTERNAL_URL")
        if url:
            try:
                requests.get(url, timeout=10)
                logger.info("Self-ping sent successfully.")
            except Exception as e:
                logger.error(f"Self-ping failed: {e}")
        time.sleep(300)  # هر ۵ دقیقه


# توابع کمکی ارتباط با بله
def send_request(method, data):
    url = f"{BASE_URL}/{method}"
    try:
        response = requests.post(url, json=data, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Request error in {method}: {e}")
        return None


def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text}
    if reply_markup:
        data["reply_markup"] = reply_markup
    return send_request("sendMessage", data)


def get_chat_member(chat_id, user_id):
    data = {"chat_id": chat_id, "user_id": user_id}
    res = send_request("getChatMember", data)
    if res and res.get("ok"):
        status = res.get("result", {}).get("status")
        return status in ["member", "administrator", "creator"]
    return False


# کیبوردهای اصلی
def get_main_keyboard(user_id):
    is_admin = user_id == ADMIN_ID
    keyboard = [
        [{"text": "📢 ثبت تبلیغ کانال (جذب ممبر)"}],
        [{"text": "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)"}],
        [{"text": "💰 دریافت سکه"}, {"text": "👥 دعوت از دوستان"}],
        [{"text": "📋 لیست تبلیغ‌های من"}, {"text": "📂 لیست کانال/گروه‌های سفارشی"}],
        [{"text": "🗑️ حذف تبلیغ کانال"}, {"text": "💳 انتقال سکه"}],
        [
            {"text": "🎡 گردونه شانس"},
            {"text": "🎁 دریافت جایزه کانال"},
            {"text": "🎁 وارد کردن کد هدیه"},
        ],
        [{"text": "✏️ تغییر نام مستعار"}, {"text": "📞 پشتیبانی و ارتباط با ما"}],
        [{"text": "❓ راهنمای استفاده"}],
    ]
    if is_admin:
        keyboard.append([{"text": "🛠 پنل مدیریت"}])
    return {"keyboard": keyboard, "resize_keyboard": True}


def get_back_keyboard():
    return {
        "keyboard": [[{"text": "🔙 بازگشت به منوی اصلی"}]],
        "resize_keyboard": True,
    }


def is_nickname_taken(name, current_chat_id):
    for uid, nname in nicknames.items():
        if nname == name and uid != current_chat_id:
            return True
    return False


# حلقه پولینگ (بررسی پیام‌ها)
def run_polling():
    offset = 0
    logger.info("Bot polling started...")
    while True:
        try:
            updates = send_request(
                "getUpdates", {"offset": offset, "timeout": 30}
            )
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    offset = update["update_id"] + 1
                    handle_update(update)
            time.sleep(1)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)


def handle_update(update):
    message = update.get("message")
    if not message:
        return

    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user_data = message.get("from", {})
    first_name = user_data.get("first_name", "کاربر")

    if not chat_id:
        return

    # بررسی عضویت کاربر در سیستم
    if chat_id not in users_db:
        users_db[chat_id] = {
            "first_name": first_name,
            "joined_date": time.time(),
        }
        if chat_id not in wallets:
            wallets[chat_id] = 50  # سکه اولیه
        save_data()
        if chat_id not in nicknames and chat_id not in waiting_for_name:
            waiting_for_name.add(chat_id)
            send_message(
                chat_id,
                f"سلام {first_name} عزیز! خوش آمدی. لطفاً نام مستعار خود را وارد کنید:",
                get_back_keyboard(),
            )
            return

    # ثبت نام مستعار اولیه
    if chat_id in waiting_for_name:
        if text == "🔙 بازگشت به منوی اصلی":
            waiting_for_name.remove(chat_id)
            send_message(
                chat_id, "منوی اصلی:", get_main_keyboard(chat_id)
            )
            return
        if is_nickname_taken(text, chat_id):
            send_message(
                chat_id,
                "⚠️ این نام مستعار قبلاً توسط کاربر دیگری انتخاب شده است. لطفاً نام دیگری وارد کنید:",
                get_back_keyboard(),
            )
            return
        nicknames[chat_id] = text
        waiting_for_name.remove(chat_id)
        save_data()
        send_message(
            chat_id,
            f"✅ نام مستعار شما با موفقیت ثبت شد: **{text}**\nحالا می‌توانید از امکانات ربات استفاده کنید.",
            get_main_keyboard(chat_id),
        )
        return

    # دکمه بازگشت عمومی
    if text == "🔙 بازگشت به منوی اصلی":
        waiting_for_name_change.discard(chat_id)
        waiting_for_channel.discard(chat_id)
        waiting_for_deletion.discard(chat_id)
        waiting_for_referral_code.discard(chat_id)
        waiting_for_group_name.discard(chat_id)
        waiting_for_broadcast.discard(chat_id)
        waiting_for_gift_code.discard(chat_id)
        waiting_for_redeem_code.discard(chat_id)
        send_message(chat_id, "منوی اصلی:", get_main_keyboard(chat_id))
        return

    # تغییر نام مستعار
    if text == "✏️ تغییر نام مستعار":
        waiting_for_name_change.add(chat_id)
        send_message(
            chat_id,
            "لطفاً نام مستعار جدید خود را وارد کنید (دقت کنید نام تکراری نباشد):",
            get_back_keyboard(),
        )
        return

    if chat_id in waiting_for_name_change:
        if is_nickname_taken(text, chat_id):
            send_message(
                chat_id,
                "⚠️ این نام مستعار قبلاً ثبت شده است. لطفاً نام دیگری وارد کنید:",
                get_back_keyboard(),
            )
            return
        nicknames[chat_id] = text
        waiting_for_name_change.remove(chat_id)
        save_data()
        send_message(
            chat_id,
            f"✅ نام مستعار شما با موفقیت به **{text}** تغییر یافت.",
            get_main_keyboard(chat_id),
        )
        return

    # سایر منوها و دکمه‌ها
    if text == "📞 پشتیبانی و ارتباط با ما":
        send_message(
            chat_id,
            f"📞 راه‌های ارتباطی با پشتیبانی:\nآیدی ادمین: {ADMIN_SUPPORT_USERNAME}\nکانال اطلاع‌رسانی: {INFO_CHANNEL}",
            get_main_keyboard(chat_id),
        )
        return

    if text == "❓ راهنمای استفاده":
        send_message(
            chat_id,
            "❓ **راهنمای استفاده از ربات ممبرگیر:**\n\n1️⃣ با عضویت در کانال‌های دیگران سکه بگیرید.\n2️⃣ با سکه‌های خود برای کانال یا گروه خودتان تبلیغ ثبت کنید.\n3️⃣ کد دعوت خود را به دوستانتان بدهید تا سکه هدیه بگیرید.\n4️⃣ کدهای هدیه را وارد کنید و سکه رایگان بگیرید!",
            get_main_keyboard(chat_id),
        )
        return

    # وارد کردن کد هدیه توسط کاربر
    if text == "🎁 وارد کردن کد هدیه":
        waiting_for_redeem_code.add(chat_id)
        send_message(
            chat_id,
            "لطفاً کد هدیه خود را وارد کنید:",
            get_back_keyboard(),
        )
        return

    if chat_id in waiting_for_redeem_code:
        waiting_for_redeem_code.remove(chat_id)
        code = text.upper()
        if code not in gift_codes_db:
            send_message(
                chat_id,
                "❌ این کد هدیه نامعتبر است.",
                get_main_keyboard(chat_id),
            )
            return

        gift_info = gift_codes_db[code]
        if chat_id not in user_redeemed_codes:
            user_redeemed_codes[chat_id] = []

        if code in user_redeemed_codes[chat_id]:
            send_message(
                chat_id,
                "⚠️ شما قبلاً از این کد هدیه استفاده کرده‌اید.",
                get_main_keyboard(chat_id),
            )
            return

        if len(gift_info["redeemed_users"]) >= gift_info["max_uses"]:
            send_message(
                chat_id,
                "❌ ظرفیت این کد هدیه به پایان رسیده است.",
                get_main_keyboard(chat_id),
            )
            return

        # اعمال هدیه
        gift_info["redeemed_users"].append(chat_id)
        user_redeemed_codes[chat_id].append(code)
        wallets[chat_id] = wallets.get(chat_id, 0) + gift_info["amount"]
        save_data()

        send_message(
            chat_id,
            f"🎉 تبریک! کد هدیه با موفقیت اعمال شد و {gift_info['amount']} سکه به کیف پول شما اضافه گردید.",
            get_main_keyboard(chat_id),
        )
        return

    # پنل مدیریت و ساخت کد هدیه (توسط ادمین)
    if text == "🛠 پنل مدیریت" and chat_id == ADMIN_ID:
        keyboard = {
            "keyboard": [
                [{"text": "🎁 ساخت کد هدیه"}],
                [{"text": "📢 ارسال پیام همگانی"}],
                [{"text": "🔙 بازگشت به منوی اصلی"}],
            ],
            "resize_keyboard": True,
        }
        send_message(chat_id, "به پنل مدیریت خوش آمدید:", keyboard)
        return

    if text == "🎁 ساخت کد هدیه" and chat_id == ADMIN_ID:
        waiting_for_gift_code.add(chat_id)
        send_message(
            chat_id,
            "لطفاً کد هدیه، مبلغ سکه و حداکثر تعداد استفاده را به این فرمت ارسال کنید:\n`CODE AMOUNT MAX_USES`\nمثال: `GIFT100 50 10`",
            get_back_keyboard(),
        )
        return

    if chat_id in waiting_for_gift_code and chat_id == ADMIN_ID:
        waiting_for_gift_code.remove(chat_id)
        parts = text.split()
        if len(parts) != 3:
            send_message(
                chat_id,
                "❌ فرمت نامعتبر. لطفاً مطابق الگو وارد کنید: `CODE AMOUNT MAX_USES`",
                get_main_keyboard(chat_id),
            )
            return
        code, amount, max_uses = parts[0].upper(), parts[1], parts[2]
        if not amount.isdigit() or not max_uses.isdigit():
            send_message(
                chat_id,
                "❌ مبلغ و تعداد باید عدد باشند.",
                get_main_keyboard(chat_id),
            )
            return

        gift_codes_db[code] = {
            "amount": int(amount),
            "max_uses": int(max_uses),
            "redeemed_users": [],
        }
        save_data()
        send_message(
            chat_id,
            f"✅ کد هدیه `{code}` با مقدار {amount} سکه و ظرفیت {max_uses} نفر با موفقیت ساخته شد.",
            get_main_keyboard(chat_id),
        )
        return

    # پیش‌فرض پاسخ به دکمه‌های تعریف نشده یا عمومی
    send_message(
        chat_id,
        "دستور شما دریافت شد. از منوی زیر انتخاب کنید:",
        get_main_keyboard(chat_id),
    )


if __name__ == "__main__":
    # شروع وب‌سایت Flask در یک ترد جداگانه
    t_flask = threading.Thread(target=run_flask)
    t_flask.daemon = True
    t_flask.start()

    # شروع نخ Self-Ping
    t_ping = threading.Thread(target=self_ping)
    t_ping.daemon = True
    t_ping.start()

    # شروع پولینگ ربات
    run_polling()
