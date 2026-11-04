import json
import os
import random
import threading
import time
from flask import Flask, request
import requests

# ---------------- CONFIGURATION ----------------
TOKEN = "*******"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"

ADMIN_ID = "YOUR_ADMIN_CHAT_ID"  # شناسه عددی ادمین خودت را اینجا وارد کن یا بگذار همین بماند
INFO_CHANNEL = "@ettela_resani_member"
SUPPORT_ID = "@kia_karfarma"

DB_FILE = "bot_database.json"
db_lock = threading.Lock()

# ---------------- DATABASES & STATES ----------------
users_db = {}
wallets = {}
campaigns_db = {}
history_db = {}
rewarded_info_channel = []
user_task = {}
waiting_for_name = set()
waiting_for_name_change = set()
waiting_for_channel = set()
waiting_for_deletion = set()
waiting_for_referral_code = set()
is_entering_ref_code = set()
waiting_for_transfer_dest = {}
waiting_for_transfer_amount = {}
transfer_temp_dest = {}
created_groups_db = {}
waiting_for_group_name = set()
waiting_for_broadcast = set()
last_lucky_wheel = {}
gift_codes_db = {}  # format: {code: {"amount": X, "max_uses": Y, "uses": 0}}
user_redeemed_codes = {}  # format: {chat_id: [code1, code2]}
waiting_for_gift_code = set()
waiting_for_new_gift_code = set()

last_update_id = 0
user_last_click = {}  # Rate limiting for buttons

# ---------------- PERSISTENCE (JSON) ----------------
def load_database():
  global users_db, wallets, campaigns_db, history_db, rewarded_info_channel
  global created_groups_db, gift_codes_db, user_redeemed_codes
  with db_lock:
    if os.path.exists(DB_FILE):
      try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
          data = json.load(f)
          users_db.update(data.get("users_db", {}))
          wallets.update(data.get("wallets", {}))
          campaigns_db.update(data.get("campaigns_db", {}))
          history_db.update(data.get("history_db", {}))
          rewarded_info_channel.extend(data.get("rewarded_info_channel", []))
          created_groups_db.update(data.get("created_groups_db", {}))
          gift_codes_db.update(data.get("gift_codes_db", {}))
          user_redeemed_codes.update(data.get("user_redeemed_codes", {}))
      except Exception as e:
        print(f"Error loading database: {e}")


def save_database():
  with db_lock:
    data = {
        "users_db": users_db,
        "wallets": wallets,
        "campaigns_db": campaigns_db,
        "history_db": history_db,
        "rewarded_info_channel": rewarded_info_channel,
        "created_groups_db": created_groups_db,
        "gift_codes_db": gift_codes_db,
        "user_redeemed_codes": user_redeemed_codes,
    }
    try:
      with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
      print(f"Error saving database: {e}")


# ---------------- BALE API HELPERS ----------------
def send_message(chat_id, text, reply_markup=None):
  url = f"{BASE_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": text}
  if reply_markup:
    payload["reply_markup"] = reply_markup
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Send message error: {e}")


def get_chat_member(chat_id, user_id):
  url = f"{BASE_URL}/getChatMember"
  payload = {"chat_id": chat_id, "user_id": user_id}
  try:
    res = requests.post(url, json=payload, timeout=10).json()
    if res.get("ok"):
      status = res.get("result", {}).get("status")
      return status in ["member", "administrator", "creator"]
  except Exception as e:
    print(f"Check membership error: {e}")
  return False


def get_main_keyboard(chat_id):
  admin_btn = []
  if str(chat_id) == str(ADMIN_ID):
    admin_btn = [
        [{"text": "🛠 پنل مدیریت"}, {"text": "📢 ارسال پیام همگانی"}],
        [{"text": "🎁 ساخت کد هدیه"}],
    ]

  return {
      "keyboard": [
          [
              {"text": "📢 ثبت تبلیغ کانال (جذب ممبر)"},
              {"text": "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)"},
          ],
          [{"text": "💰 دریافت سکه"}, {"text": "👥 دعوت از دوستان"}],
          [{"text": "📋 لیست تبلیغ‌های من"}, {"text": "📂 لیست کانال/گروه‌های سفارشی"}],
          [{"text": "🗑️ حذف تبلیغ کانال"}, {"text": "🎡 گردونه شانس"}],
          [{"text": "💳 انتقال سکه"}, {"text": "🎁 وارد کردن کد هدیه"}],
          [{"text": "🎁 دریافت جایزه کانال"}, {"text": "✏️ تغییر نام مستعار"}],
          [{"text": "📞 پشتیبانی و ارتباط با ما"}, {"text": "❓ راهنمای استفاده"}],
      ]
      + admin_btn,
      "resize_keyboard": True,
  }


def get_back_keyboard():
  return {
      "keyboard": [[{"text": "🔙 بازگشت به منوی اصلی"}]],
      "resize_keyboard": True,
  }


def is_nickname_taken(name, current_chat_id):
  for cid, uinfo in users_db.items():
    if str(cid) != str(current_chat_id) and uinfo.get("nickname") == name:
      return True
  return False


# ---------------- MESSAGE HANDLER ----------------
def handle_message(message):
  chat_id = str(message.get("chat", {}).get("id"))
  text = message.get("text", "").strip()
  if not chat_id or not text:
    return

  # Register user if not exists
  if chat_id not in users_db:
    users_db[chat_id] = {"nickname": None, "joined_at": time.time()}
    wallets[chat_id] = 50  # 50 initial coins
    save_database()
    waiting_for_name.add(chat_id)
    send_message(
        chat_id,
        "سلام! به ربات ممبرگیر خوش آمدید.\nلطفاً نام مستعار خود را وارد کنید:",
        get_back_keyboard(),
    )
    return

  # Handle Back Button
  if text == "🔙 بازگشت به منوی اصلی":
    waiting_for_name.discard(chat_id)
    waiting_for_name_change.discard(chat_id)
    waiting_for_channel.discard(chat_id)
    waiting_for_deletion.discard(chat_id)
    waiting_for_referral_code.discard(chat_id)
    is_entering_ref_code.discard(chat_id)
    waiting_for_transfer_dest.pop(chat_id, None)
    waiting_for_transfer_amount.pop(chat_id, None)
    transfer_temp_dest.pop(chat_id, None)
    waiting_for_group_name.discard(chat_id)
    waiting_for_broadcast.discard(chat_id)
    waiting_for_gift_code.discard(chat_id)
    waiting_for_new_gift_code.discard(chat_id)

    send_message(
        chat_id, "به منوی اصلی برگشتیم:", get_main_keyboard(chat_id)
    )
    return

  # Handle Nickname registration
  if chat_id in waiting_for_name:
    if is_nickname_taken(text, chat_id):
      send_message(
          chat_id,
          "❌ این نام مستعار قبلاً توسط کاربر دیگری انتخاب شده است. لطفاً نام دیگری وارد کنید:",
          get_back_keyboard(),
      )
      return
    users_db[chat_id]["nickname"] = text
    waiting_for_name.remove(chat_id)
    save_database()
    send_message(
        chat_id,
        f"✅ نام مستعار شما با موفقیت ثبت شد!\n۵۰ سکه هدیه اولیه به حساب شما واریز شد.",
        get_main_keyboard(chat_id),
    )
    return

  # Handle Nickname change
  if chat_id in waiting_for_name_change:
    if is_nickname_taken(text, chat_id):
      send_message(
          chat_id,
          "❌ این نام مستعار تکراری است. لطفاً نام دیگری انتخاب کنید:",
          get_back_keyboard(),
      )
      return
    users_db[chat_id]["nickname"] = text
    waiting_for_name_change.remove(chat_id)
    save_database()
    send_message(
        chat_id,
        f"✅ نام مستعار شما با موفقیت به «{text}» تغییر یافت.",
        get_main_keyboard(chat_id),
    )
    return

  # Handle Gift Code redemption input
  if chat_id in waiting_for_gift_code:
    waiting_for_gift_code.remove(chat_id)
    code = text.upper()
    if code not in gift_codes_db:
      send_message(
          chat_id,
          "❌ کد هدیه نامعتبر است یا وجود ندارد.",
          get_main_keyboard(chat_id),
      )
      return

    code_info = gift_codes_db[code]
    if code_info["uses"] >= code_info["max_uses"]:
      send_message(
          chat_id,
          "❌ ظرفیت این کد هدیه به اتمام رسیده است.",
          get_main_keyboard(chat_id),
      )
      return

    if chat_id not in user_redeemed_codes:
      user_redeemed_codes[chat_id] = []

    if code in user_redeemed_codes[chat_id]:
      send_message(
          chat_id,
          "❌ شما قبلاً از این کد هدیه استفاده کرده‌اید.",
          get_main_keyboard(chat_id),
      )
      return

    # Apply gift code
    code_info["uses"] += 1
    user_redeemed_codes[chat_id].append(code)
    amount = code_info["amount"]
    wallets[chat_id] = wallets.get(chat_id, 0) + amount
    save_database()
    send_message(
        chat_id,
        f"🎉 تبریک! کد هدیه با موفقیت اعمال شد و {amount} سکه به کیف پول شما اضافه گردید.",
        get_main_keyboard(chat_id),
    )
    return

  # Admin: Create Gift Code input
  if chat_id in waiting_for_new_gift_code and str(chat_id) == str(ADMIN_ID):
    waiting_for_new_gift_code.remove(chat_id)
    parts = text.split()
    if len(parts) != 3:
      send_message(
          chat_id,
          "❌ فرمت نامعتبر است.\nلطفاً به شکل زیر ارسال کنید:\nCODE AMOUNT MAX_USES\nمثلا: `GIFT100 50 10`",
          get_main_keyboard(chat_id),
      )
      return
    code, amount_str, max_uses_str = parts
    try:
      amount = int(amount_str)
      max_uses = int(max_uses_str)
      gift_codes_db[code.upper()] = {
          "amount": amount,
          "max_uses": max_uses,
          "uses": 0,
      }
      save_database()
      send_message(
          chat_id,
          f"✅ کد هدیه `{code.upper()}` با مقدار {amount} سکه و ظرفیت {max_uses} نفر ساخته شد.",
          get_main_keyboard(chat_id),
      )
    except ValueError:
      send_message(
          chat_id,
          "❌ مقادیر سکه و تعداد باید عدد باشند.",
          get_main_keyboard(chat_id),
      )
    return

  # Menu Options
  if text == "✏️ تغییر نام مستعار":
    waiting_for_name_change.add(chat_id)
    send_message(
        chat_id, "لطفاً نام مستعار جدید خود را وارد کنید:", get_back_keyboard()
    )

  elif text == "🎁 وارد کردن کد هدیه":
    waiting_for_gift_code.add(chat_id)
    send_message(chat_id, "لطفاً کد هدیه خود را وارد کنید:", get_back_keyboard())

  elif text == "🎁 ساخت کد هدیه" and str(chat_id) == str(ADMIN_ID):
    waiting_for_new_gift_code.add(chat_id)
    send_message(
        chat_id,
        "لطفاً اطلاعات کد هدیه را به شکل زیر بفرستید:\n`CODE AMOUNT MAX_USES`",
        get_back_keyboard(),
    )

  elif text == "📞 پشتیبانی و ارتباط با ما":
    send_message(
        chat_id,
        f"📞 برای ارتباط با پشتیبانی به ایدی زیر پیام دهید:\n{SUPPORT_ID}\n\n📢 همچنین کانال اطلاع‌رسانی ما:\n{INFO_CHANNEL}",
        get_main_keyboard(chat_id),
    )

  elif text == "❓ راهنمای استفاده":
    send_message(
        chat_id,
        "❓ راهنمای ربات ممبرگیر:\n\n1️⃣ با دریافت سکه از طریق عضویت در کانال‌ها، سکه جمع کنید.\n2️⃣ با ثبت تبلیغ کانال خود، ممبر واقعی جذب کنید.\n3️⃣ با دعوت از دوستانتان با کد دعوت اختصاصی خود، جایزه بگیرید.",
        get_main_keyboard(chat_id),
    )

  else:
    send_message(
        chat_id,
        "دستور نامعتبر است. از منوی زیر استفاده کنید:",
        get_main_keyboard(chat_id),
    )


# ---------------- FLASK & WEB SERVER ----------------
app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
  return "Bot is running and live!"


@app.route(f"/bot{TOKEN}", methods=["POST"])
def webhook():
  return "OK", 200


# Self-ping to keep render alive
def self_ping():
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if render_url:
    while True:
      try:
        requests.get(render_url, timeout=10)
      except Exception:
        pass
      time.sleep(300)


# ---------------- POLLING LOOP ----------------
def run_bot():
  global last_update_id
  load_database()
  print("Bot started polling loop...")
  while True:
    try:
      url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
      response = requests.get(url, timeout=35)
      data = response.json()
      print(f"Polling response: {data}")

      if data.get("ok"):
        for update in data.get("result", []):
          last_update_id = update["update_id"]
          message = update.get("message")
          if message:
            threading.Thread(
                target=handle_message, args=(message,), daemon=True
            ).start()
    except Exception as e:
      print(f"Polling error: {e}")
      time.sleep(3)


if __name__ == "__main__":
  threading.Thread(target=run_bot, daemon=True).start()
  threading.Thread(target=self_ping, daemon=True).start()
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
