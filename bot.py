import json
import os
import random
import threading
import time
import requests
from flask import Flask

# ---------------- CONFIGURATION ----------------
TOKEN = "*******"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
ADMIN_IDS = [123456789]  # آیدی عددی ادمین (برای تست جایگزین کن یا بعداً اضافه کن)
INFO_CHANNEL = "@ettela_resani_member"
SUPPORT_ID = "@kia_karfarma"

# File database
DB_FILE = "bot_database.json"

# Global States & Databases
users_db = {}  # chat_id: {"name": str, "ref_by": int}
wallets = {}  # chat_id: int (coins)
campaigns_db = {}  # channel_username: {"owner": chat_id, "views_left": int}
history_db = {}  # chat_id: [list of joined channel usernames]
rewarded_info_channel = []  # list of chat_ids who got info channel bonus
user_task = {}  # chat_id: target channel to join for coins
waiting_for_name = []  # list of chat_ids waiting to enter initial nickname
waiting_for_name_change = []  # list of chat_ids waiting to change nickname
waiting_for_channel = []  # list of chat_ids waiting to submit ad channel
waiting_for_deletion = []  # list of chat_ids waiting to delete ad channel
waiting_for_referral_code = []  # list of chat_ids waiting to enter invite code
waiting_for_transfer_dest = []  # chat_id: step 1 transfer (dest chat_id)
waiting_for_transfer_amount = {}  # chat_id: step 2 transfer (amount)
transfer_temp_dest = {}  # chat_id: temp stored destination
created_groups_db = {}  # order_id: {"owner": chat_id, "name": str, "status": "بررسی"}
waiting_for_group_name = []  # list of chat_ids waiting to enter group/channel name
waiting_for_broadcast = []  # list of admin chat_ids waiting for broadcast message
last_lucky_wheel = {}  # chat_id: timestamp of last spin

# --- NEW: Gift Codes Database ---
gift_codes_db = {}  # code: reward_amount
user_redeemed_codes = {}  # chat_id: [list of redeemed codes]
waiting_for_gift_code = []  # list of chat_ids waiting to enter gift code
waiting_for_new_gift_code = []  # admin waiting for "CODE AMOUNT"

last_check_time = {}  # chat_id: timestamp for anti-flood
last_update_id = 0


# ---------------- DATABASE FUNCTIONS ----------------
def load_database():
  global users_db, wallets, campaigns_db, history_db, rewarded_info_channel
  global created_groups_db, last_lucky_wheel, gift_codes_db, user_redeemed_codes
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        users_db = {int(k): v for k, v in data.get("users_db", {}).items()}
        wallets = {int(k): v for k, v in data.get("wallets", {}).items()}
        campaigns_db = data.get("campaigns_db", {})
        history_db = {
            int(k): v for k, v in data.get("history_db", {}).items()
        }
        rewarded_info_channel = [
            int(i) for i in data.get("rewarded_info_channel", [])
        ]
        created_groups_db = {
            k: v for k, v in data.get("created_groups_db", {}).items()
        }
        last_lucky_wheel = {
            int(k): v for k, v in data.get("last_lucky_wheel", {}).items()
        }
        gift_codes_db = data.get("gift_codes_db", {})
        user_redeemed_codes = {
            int(k): v for k, v in data.get("user_redeemed_codes", {}).items()
        }
    except Exception as e:
      print(f"Error loading DB: {e}")


def save_database():
  data = {
      "users_db": users_db,
      "wallets": wallets,
      "campaigns_db": campaigns_db,
      "history_db": history_db,
      "rewarded_info_channel": rewarded_info_channel,
      "created_groups_db": created_groups_db,
      "last_lucky_wheel": last_lucky_wheel,
      "gift_codes_db": gift_codes_db,
      "user_redeemed_codes": user_redeemed_codes,
  }
  try:
    with open(DB_FILE, "w", encoding="utf-8") as f:
      json.dump(data, f, ensure_ascii=False, indent=4)
  except Exception as e:
    print(f"Error saving DB: {e}")


# ---------------- HELPER FUNCTIONS ----------------
def is_nickname_taken(name, current_chat_id):
  for uid, udata in users_db.items():
    if uid != current_chat_id and udata.get("name") == name:
      return True
  return False


def send_message(chat_id, text, reply_markup=None):
  url = f"{BASE_URL}/sendMessage"
  payload = {"chat_id": chat_id, "text": text}
  if reply_markup:
    payload["reply_markup"] = json.dumps(reply_markup)
  try:
    requests.post(url, json=payload, timeout=10)
  except Exception as e:
    print(f"Error sending message: {e}")


def check_chat_member(chat_id, channel_username):
  url = f"{BASE_URL}/getChatMember"
  payload = {"chat_id": channel_username, "user_id": chat_id}
  try:
    response = requests.post(url, json=payload, timeout=10)
    res_json = response.json()
    if res_json.get("ok"):
      status = res_json.get("result", {}).get("status")
      if status in ["member", "administrator", "creator"]:
        return True
  except Exception as e:
    print(f"Error checking membership: {e}")
  return False


def get_main_keyboard(chat_id):
  is_admin = chat_id in ADMIN_IDS
  keyboard = [
      [{"text": "💰 دریافت سکه"}, {"text": "📢 ثبت تبلیغ کانال (جذب ممبر)"}],
      [{"text": "👥 دعوت از دوستان"}, {"text": "👤 پروفایل من"}],
      [{"text": "🎁 وارد کردن کد هدیه"}, {"text": "🎡 گردونه شانس"}],
      [{"text": "🎁 دریافت جایزه کانال"}, {"text": "💳 انتقال سکه"}],
      [{"text": "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)"}],
      [{"text": "📋 لیست تبلیغ‌های من"}, {"text": "📂 لیست کانال/گروه‌های سفارشی"}],
      [{"text": "🗑️ حذف تبلیغ کانال"}, {"text": "✏️ تغییر نام مستعار"}],
      [{"text": "📞 پشتیبانی و ارتباط با ما"}, {"text": "❓ راهنمای استفاده"}],
  ]
  if is_admin:
    keyboard.append([{"text": "🛠 پنل مدیریت"}])
  return {"keyboard": keyboard, "resize_keyboard": True}


def get_back_keyboard():
  return {
      "keyboard": [[{"text": "🔙 بازگشت به منوی اصلی"}]],
      "resize_keyboard": True,
  }


def clear_user_states(chat_id):
  for state_list in [
      waiting_for_name,
      waiting_for_name_change,
      waiting_for_channel,
      waiting_for_deletion,
      waiting_for_referral_code,
      waiting_for_group_name,
      waiting_for_broadcast,
      waiting_for_gift_code,
      waiting_for_new_gift_code,
  ]:
    if chat_id in state_list:
      state_list.remove(chat_id)
  waiting_for_transfer_dest.pop(chat_id, None)
  waiting_for_transfer_amount.pop(chat_id, None)
  transfer_temp_dest.pop(chat_id, None)
  user_task.pop(chat_id, None)


# ---------------- MESSAGE HANDLER ----------------
def handle_message(message):
  chat_id = message.get("chat", {}).get("id")
  text = message.get("text", "").strip()
  if not chat_id or not text:
    return

  # Check if user is registered
  if chat_id not in users_db and chat_id not in waiting_for_name:
    waiting_for_name.append(chat_id)
    send_message(
        chat_id,
        "سلام! 🌟 به ربات جذب ممبر خوش آمدید.\nلطفاً یک **نام مستعار** برای خود"
        " انتخاب کنید و ارسال کنید:",
        get_back_keyboard(),
    )
    return

  # Handle Back Button
  if text == "🔙 بازگشت به منوی اصلی":
    clear_user_states(chat_id)
    send_message(chat_id, "به منوی اصلی برگشتیم:", get_main_keyboard(chat_id))
    return

  # 1. Initial Name Registration State
  if chat_id in waiting_for_name:
    if is_nickname_taken(text, chat_id):
      send_message(
          chat_id,
          "⚠️ این نام مستعار قبلاً توسط کاربر دیگری انتخاب شده است. لطفاً نام"
          " دیگری انتخاب کنید:",
      )
      return
    users_db[chat_id] = {"name": text, "ref_by": None}
    wallets[chat_id] = 50  # Initial reward
    waiting_for_name.remove(chat_id)
    save_database()
    send_message(
        chat_id,
        f"✅ ثبت‌نام شما با موفقیت انجام شد، {text} عزیز!\n🎁 ۵۰ سکه هدیه اولیه"
        " به حساب شما واریز شد.",
        get_main_keyboard(chat_id),
    )
    return

  # 2. Nickname Change State
  if chat_id in waiting_for_name_change:
    if is_nickname_taken(text, chat_id):
      send_message(
          chat_id,
          "⚠️ این نام مستعار قبلاً ثبت شده است. لطفاً نام دیگری وارد کنید:",
      )
      return
    users_db[chat_id]["name"] = text
    waiting_for_name_change.remove(chat_id)
    save_database()
    send_message(
        chat_id,
        f"✅ نام مستعار شما با موفقیت به **{text}** تغییر یافت.",
        get_main_keyboard(chat_id),
    )
    return

  # 3. Enter Referral Code State
  if chat_id in waiting_for_referral_code:
    waiting_for_referral_code.remove(chat_id)
    if not text.isdigit():
      send_message(
          chat_id,
          "❌ کد دعوت نامعتبر است. فقط از اعداد استفاده کنید.",
          get_main_keyboard(chat_id),
      )
      return
    inviter_id = int(text)
    if inviter_id == chat_id:
      send_message(
          chat_id,
          "❌ شما نمی‌توانید کد دعوت خودتان را وارد کنید!",
          get_main_keyboard(chat_id),
      )
      return
    if inviter_id not in users_db:
      send_message(
          chat_id,
          "❌ کاربری با این کد دعوت پیدا نشد.",
          get_main_keyboard(chat_id),
      )
      return
    if users_db[chat_id].get("ref_by"):
      send_message(
          chat_id,
          "❌ شما قبلاً کد دعوت وارد کرده‌اید!",
          get_main_keyboard(chat_id),
      )
      return

    users_db[chat_id]["ref_by"] = inviter_id
    wallets[chat_id] = wallets.get(chat_id, 0) + 10
    wallets[inviter_id] = wallets.get(inviter_id, 0) + 10
    save_database()

    send_message(
        chat_id,
        "🎉 کد دعوت با موفقیت ثبت شد و ۱۰ سکه هدیه گرفتید!",
        get_main_keyboard(chat_id),
    )
    send_message(
        inviter_id,
        "🎁 یک نفر با کد دعوت شما وارد ربات شد و ۱۰ سکه پاداش گرفتید!",
    )
    return

  # 4. Submit Channel Ad State
  if chat_id in waiting_for_channel:
    waiting_for_channel.remove(chat_id)
    channel = text if text.startswith("@") else f"@{text}"
    if wallets.get(chat_id, 0) < 50:
      send_message(
          chat_id,
          "❌ موجودی شما برای ثبت تبلیغ کافی نیست (حداقل ۵۰ سکه نیاز است).",
          get_main_keyboard(chat_id),
      )
      return

    campaigns_db[channel] = {"owner": chat_id, "views_left": 25}
    wallets[chat_id] -= 50
    save_database()
    admin_guide = (
        f"✅ کانال شما با موفقیت ثبت شد!\n📌 {channel}\n\n📖 **راهنمای ادمین"
        " کردن ربات:**\nلطفاً ربات ما را به عنوان ادمین با دسترسی‌های کامل در"
        f" کانال خود ({channel}) اضافه کنید تا ربات بتواند عضویت کاربران را به"
        " درستی بررسی کند."
    )
    send_message(chat_id, admin_guide, get_main_keyboard(chat_id))
    return

  # 5. Delete Channel Ad State
  if chat_id in waiting_for_deletion:
    waiting_for_deletion.remove(chat_id)
    channel = text if text.startswith("@") else f"@{text}"
    if channel in campaigns_db and campaigns_db[channel]["owner"] == chat_id:
      del campaigns_db[channel]
      save_database()
      send_message(
          chat_id,
          f"🗑️ تبلیغ کانال {channel} با موفقیت حذف شد.",
          get_main_keyboard(chat_id),
      )
    else:
      send_message(
          chat_id,
          "❌ شما تبلیغ فعالی با این آیدی در ربات ندارید.",
          get_main_keyboard(chat_id),
      )
    return

  # 6. Coin Transfer States
  if chat_id in waiting_for_transfer_dest:
    if not text.isdigit():
      waiting_for_transfer_dest.pop(chat_id, None)
      send_message(
          chat_id,
          "❌ آیدی مقصد نامعتبر است. عملیات لغو شد.",
          get_main_keyboard(chat_id),
      )
      return
    dest_id = int(text)
    if dest_id == chat_id:
      waiting_for_transfer_dest.pop(chat_id, None)
      send_message(
          chat_id,
          "❌ نمی‌توانید به خودتان سکه انتقال دهید!",
          get_main_keyboard(chat_id),
      )
      return
    if dest_id not in users_db:
      waiting_for_transfer_dest.pop(chat_id, None)
      send_message(
          chat_id,
          "❌ کاربری با این آیدی در ربات ثبت‌نام نکرده است.",
          get_main_keyboard(chat_id),
      )
      return

    waiting_for_transfer_dest.pop(chat_id, None)
    transfer_temp_dest[chat_id] = dest_id
    waiting_for_transfer_amount[chat_id] = True
    send_message(
        chat_id,
        "💳 چه تعداد سکه می‌خواهید انتقال دهید؟ (فکر کنید موجودی فعلی‌تان چقدر"
        " است و عدد را بفرستید):",
        get_back_keyboard(),
    )
    return

  if chat_id in waiting_for_transfer_amount:
    waiting_for_transfer_amount.pop(chat_id, None)
    dest_id = transfer_temp_dest.pop(chat_id, None)
    if not text.isdigit() or int(text) <= 0:
      send_message(
          chat_id, "❌ مقدار سکه نامعتبر است.", get_main_keyboard(chat_id)
      )
      return
    amount = int(text)
    if wallets.get(chat_id, 0) < amount:
      send_message(
          chat_id,
          "❌ موجودی سکه شما برای این انتقال کافی نیست.",
          get_main_keyboard(chat_id),
      )
      return

    wallets[chat_id] -= amount
    wallets[dest_id] = wallets.get(dest_id, 0) + amount
    save_database()
    send_message(
        chat_id,
        f"✅ تعداد {amount} سکه با موفقیت به کاربر {dest_id} انتقال یافت.",
        get_main_keyboard(chat_id),
      )
    send_message(
        dest_id,
        f"💳 مقدار {amount} سکه از طرف کاربر {chat_id} به حساب شما واریز شد!",
    )
    return

  # 7. Custom Group/Channel Order State
  if chat_id in waiting_for_group_name:
    waiting_for_group_name.remove(chat_id)
    if wallets.get(chat_id, 0) < 1000:
      send_message(
          chat_id,
          "❌ موجودی شما برای سفارش ساخت کانال/گروه کافی نیست (۱۰۰۰ سکه نیاز"
          " است).",
          get_main_keyboard(chat_id),
      )
      return

    wallets[chat_id] -= 1000
    order_id = str(random.randint(10000, 99999))
    created_groups_db[order_id] = {
        "owner": chat_id,
        "name": text,
        "status": "در حال بررسی",
    }
    save_database()
    send_message(
        chat_id,
        f"✨ سفارش ساخت کانال/گروه شما با موضوع '{text}' ثبت شد!\nکد پیگیری:"
        f" `{order_id}`\nتوسط ادمین بررسی و به زودی به شما اطلاع داده می‌شود.",
        get_main_keyboard(chat_id),
    )
    for adm in ADMIN_IDS:
      send_message(
          adm,
          f"📢 سفارش ساخت جدید!\nکاربر: {chat_id}\nموضوع: {text}\nکد پیگیری:"
          f" {order_id}",
      )
    return

  # 8. Broadcast State (Admin)
  if chat_id in waiting_for_broadcast and chat_id in ADMIN_IDS:
    waiting_for_broadcast.remove(chat_id)
    success_count = 0
    for uid in users_db.keys():
      try:
        send_message(uid, f"📢 پیام همگانی از مدیریت:\n\n{text}")
        success_count += 1
      except:
        pass
    send_message(
        chat_id,
        f"✅ پیام همگانی با موفقیت به {success_count} کاربر ارسال شد.",
        get_main_keyboard(chat_id),
    )
    return

  # --- NEW: 9. Enter Gift Code State ---
  if chat_id in waiting_for_gift_code:
    waiting_for_gift_code.remove(chat_id)
    code = text.upper()
    if code not in gift_codes_db:
      send_message(
          chat_id,
          "❌ کد هدیه وارد شده نامعتبر یا منقضی شده است.",
          get_main_keyboard(chat_id),
      )
      return

    redeemed_list = user_redeemed_codes.get(chat_id, [])
    if code in redeemed_list:
      send_message(
          chat_id,
          "❌ شما قبلاً از این کد هدیه استفاده کرده‌اید!",
          get_main_keyboard(chat_id),
      )
      return

    reward = gift_codes_db[code]
    wallets[chat_id] = wallets.get(chat_id, 0) + reward
    redeemed_list.append(code)
    user_redeemed_codes[chat_id] = redeemed_list
    save_database()

    send_message(
        chat_id,
        f"🎉 تبریک! کد هدیه با موفقیت اعمال شد و {reward} سکه به حساب شما واریز"
        " شد.",
        get_main_keyboard(chat_id),
    )
    return

  # --- NEW: 10. Admin Create Gift Code State ---
  if chat_id in waiting_for_new_gift_code and chat_id in ADMIN_IDS:
    waiting_for_new_gift_code.remove(chat_id)
    parts = text.split()
    if len(parts) != 2 or not parts[1].isdigit():
      send_message(
          chat_id,
          "❌ فرمت اشتباه است. لطفاً به صورت `CODE AMOUNT` وارد کنید (مثلا:"
          " `GIFT50 50`).",
          get_main_keyboard(chat_id),
      )
      return

    code = parts[0].upper()
    amount = int(parts[1])
    gift_codes_db[code] = amount
    save_database()
    send_message(
        chat_id,
        f"✅ کد هدیه `{code}` با مبلغ {amount} سکه با موفقیت ساخته شد!",
        get_main_keyboard(chat_id),
    )
    return

  # ---------------- MENU BUTTONS ----------------
  if text == "💰 دریافت سکه":
    # Anti-leave penalty check
    joined_list = history_db.get(chat_id, [])
    penalized = 0
    survived_list = []
    for ch in joined_list:
      if check_chat_member(chat_id, ch):
        survived_list.append(ch)
      else:
        penalized += 3

    if penalized > 0:
      wallets[chat_id] = max(0, wallets.get(chat_id, 0) - penalized)
      send_message(
          chat_id,
          f"⚠️ شما از {penalized // 3} کانال لفت دادید! به ازای هر کدام ۳ سکه"
          f" ({penalized} سکه کل) از موجودی‌تان کسر شد.",
      )

    history_db[chat_id] = survived_list
    save_database()

    # Pick a random campaign user hasn't joined yet
    available_channels = []
    for ch, cdata in campaigns_db.items():
      if cdata["owner"] != chat_id and ch not in survived_list:
        if cdata["views_left"] > 0:
          available_channels.append(ch)

    if not available_channels:
      send_message(
          chat_id,
          "❌ در حال حاضر کانال جدیدی برای عضویت وجود ندارد. لطفاً بعداً سر"
          " بزنید.",
          get_main_keyboard(chat_id),
      )
      return

    target_ch = random.choice(available_channels)
    user_task[chat_id] = target_ch

    earn_kb = {
        "keyboard": [
            [{"text": "✅ بررسی عضویت"}],
            [{"text": "🔙 بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True,
    }
    send_message(
        chat_id,
        f"📢 لطفاً در کانال زیر عضو شوید و سپس روی دکمه «✅ بررسی عضویت» کلیک"
        f" کنید:\n\n🔗 {target_ch}\n🎁 پاداش: ۵ سکه",
        earn_kb,
    )
    return

  elif text == "✅ بررسی عضویت":
    # Rate limiting (3 seconds)
    now = time.time()
    if now - last_check_time.get(chat_id, 0) < 3:
      send_message(
          chat_id,
          "⏳ لطفاً کمی صبر کنید، درخواست شما خیلی سریع ارسال شده است.",
      )
      return
    last_check_time[chat_id] = now

    target_ch = user_task.get(chat_id)
    if not target_ch:
      send_message(
          chat_id,
          "❌ ماموریتی انتخاب نشده است. از منوی «💰 دریافت سکه» شروع کنید.",
          get_main_keyboard(chat_id),
      )
      return

    if check_chat_member(chat_id, target_ch):
      wallets[chat_id] = wallets.get(chat_id, 0) + 5
      user_task.pop(chat_id, None)

      # Decrease campaign views
      if target_ch in campaigns_db:
        campaigns_db[target_ch]["views_left"] -= 1
        if campaigns_db[target_ch]["views_left"] <= 0:
          del campaigns_db[target_ch]

      # Add to history
      if chat_id not in history_db:
        history_db[chat_id] = []
      if target_ch not in history_db[chat_id]:
        history_db[chat_id].append(target_ch)

      save_database()
      send_message(
          chat_id,
          "🎉 تبریک! عضویت شما تأیید شد و ۵ سکه به حساب شما اضافه شد.",
          get_main_keyboard(chat_id),
      )
    else:
      send_message(
          chat_id,
          "❌ شما هنوز در کانال موردنظر عضو نشده‌اید یا ربات در کانال ادمین نیست."
          " لطفاً عضو شوید و دوباره تلاش کنید.",
      )
    return

  elif text == "📢 ثبت تبلیغ کانال (جذب ممبر)":
    waiting_for_channel.append(chat_id)
    send_message(
        chat_id,
        "📢 لطفاً آیدی کانال خود را با فرمت `@channel` ارسال کنید.\n💵 هزینه ثبت"
        " تبلیغ: ۵۰ سکه (برای ۲۵ بازدید/پیشنهاد)",
        get_back_keyboard(),
    )
    return

  elif text == "👥 دعوت از دوستان":
    invite_link = f"https://ble.ir/member-gir-bot?start={chat_id}"
    send_message(
        chat_id,
        f"👥 **سیستم دعوت از دوستان:**\n\nکد دعوت اختصاصی شما (آیدی عددی شما):"
        f" `{chat_id}`\n\nهمچنین می‌توانید لینک زیر را برای دوستان خود"
        f" بفرستید:\n{invite_link}\n\n🎁 به ازای هر دوستی که با کد شما وارد"
        " ربات شود، ۱۰ سکه پاداش می‌گیرید!\n\nاگر کسی به شما کد دعوت داده، از"
        " طریق دکمه زیر وارد کنید:",
        {
            "keyboard": [
                [{"text": "➕ وارد کردن کد دعوت معرف"}],
                [{"text": "🔙 بازگشت به منوی اصلی"}],
            ],
            "resize_keyboard": True,
        },
    )
    return

  elif text == "➕ وارد کردن کد دعوت معرف":
    waiting_for_referral_code.append(chat_id)
    send_message(
        chat_id,
        "📥 لطفاً کد دعوت (آیدی عددی) معرف خود را ارسال کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "👤 پروفایل من":
    name = users_db[chat_id].get("name", "نامشخص")
    coin = wallets.get(chat_id, 0)
    my_channels = [
        ch for ch, cdata in campaigns_db.items() if cdata["owner"] == chat_id
    ]
    send_message(
        chat_id,
        f"👤 **پروفایل شما:**\n\n🏷️ نام مستعار: {name}\n🆔 آیدی عددی: `{chat_id}`\n💰"
        f" موجودی سکه: {coin}\n📢 کانال‌های ثبت‌شده برای تبلیغ:"
        f" {len(my_channels)} کانال",
        get_main_keyboard(chat_id),
    )
    return

  elif text == "🎁 وارد کردن کد هدیه":
    waiting_for_gift_code.append(chat_id)
    send_message(
        chat_id,
        "🎁 لطفاً کد هدیه خود را وارد کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "🎡 گردونه شانس":
    now = time.time()
    last_spin = last_lucky_wheel.get(chat_id, 0)
    if now - last_spin < 86400:  # 24 hours
      hours_left = int((86400 - (now - last_spin)) // 3600)
      send_message(
          chat_id,
          f"⏳ شما امروز از گردونه شانس استفاده کرده‌اید. لطفاً پس از"
          f" {hours_left} ساعت دیگر دوباره امتحان کنید.",
          get_main_keyboard(chat_id),
      )
      return

    prize = random.choice([5, 10, 15, 20, 30, 50])
    last_lucky_wheel[chat_id] = now
    wallets[chat_id] = wallets.get(chat_id, 0) + prize
    save_database()
    send_message(
        chat_id,
        f"🎡 چرخش گردونه شانس انجام شد!\n🎉 تبریک! شما برنده {prize} سکه"
        " شتید!",
        get_main_keyboard(chat_id),
    )
    return

  elif text == "🎁 دریافت جایزه کانال":
    if chat_id in rewarded_info_channel:
      send_message(
          chat_id,
          "❌ شما قبلاً جایزه این کانال را دریافت کرده‌اید!",
          get_main_keyboard(chat_id),
      )
      return

    if check_chat_member(chat_id, INFO_CHANNEL):
      rewarded_info_channel.append(chat_id)
      wallets[chat_id] = wallets.get(chat_id, 0) + 10
      save_database()
      send_message(
          chat_id,
          "🎉 تبریک! عضویت شما در کانال اطلاع‌رسانی تأیید شد و ۱۰ سکه جایزه گرفتید!",
          get_main_keyboard(chat_id),
      )
    else:
      send_message(
          chat_id,
          f"❌ شما هنوز در کانال اطلاع‌رسانی ما ({INFO_CHANNEL}) عضو نشده‌اید."
          " ابتدا عضو شوید و دوباره تلاش کنید.",
          get_main_keyboard(chat_id),
      )
    return

  elif text == "💳 انتقال سکه":
    waiting_for_transfer_dest[chat_id] = True
    send_message(
        chat_id,
        "💳 لطفاً آیدی عددی کاربر مقصد برای انتقال سکه را وارد کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "✨ سفارش ساخت کانال/گروه جدید (۱۰۰۰ سکه)":
    waiting_for_group_name.append(chat_id)
    send_message(
        chat_id,
        "✨ سفارش ساخت کانال یا گروه جدید:\n💵 هزینه: ۱۰۰۰ سکه\n\nلطفاً موضوع یا"
        " نام دلخواه کانال/گروه خود را ارسال کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "📋 لیست تبلیغ‌های من":
    my_channels = [
        f"📌 {ch} (بازدید باقی‌مانده: {cdata['views_left']})"
        for ch, cdata in campaigns_db.items()
        if cdata["owner"] == chat_id
    ]
    if not my_channels:
      send_message(
          chat_id,
          "📂 شما هیچ تبلیغ فعالی در ربات ندارید.",
          get_main_keyboard(chat_id),
      )
    else:
      send_message(
          chat_id,
          "📋 **لیست تبلیغ‌های فعال شما:**\n\n" + "\n".join(my_channels),
          get_main_keyboard(chat_id),
      )
    return

  elif text == "📂 لیست کانال/گروه‌های سفارشی":
    my_orders = [
        f"🔹 کد: `{oid}` | موضوع: {odata['name']} | وضعیت: {odata['status']}"
        for oid, odata in created_groups_db.items()
        if odata["owner"] == chat_id
    ]
    if not my_orders:
      send_message(
          chat_id,
          "📂 شما هیچ سفارش ساخت کانال یا گروهی ثبت نکرده‌اید.",
          get_main_keyboard(chat_id),
      )
    else:
      send_message(
          chat_id,
          "📂 **سفارش‌های ساخت شما:**\n\n" + "\n".join(my_orders),
          get_main_keyboard(chat_id),
      )
    return

  elif text == "🗑️ حذف تبلیغ کانال":
    waiting_for_deletion.append(chat_id)
    send_message(
        chat_id,
        "🗑️ لطفاً آیدی کانالی که می‌خواهید تبلیغ آن حذف شود را وارد کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "✏️ تغییر نام مستعار":
    waiting_for_name_change.append(chat_id)
    send_message(
        chat_id,
        "✏️ لطفاً نام مستعار جدید خود را ارسال کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "📞 پشتیبانی و ارتباط با ما":
    send_message(
        chat_id,
        f"📞 برای ارتباط با پشتیبانی و ارسال پیشنهادات با ادمین در ارتباط"
        f" باشید:\n{SUPPORT_ID}",
        get_main_keyboard(chat_id),
    )
    return

  elif text == "❓ راهنمای استفاده":
    guide_text = (
        "❓ **راهنمای استفاده از ربات جذب ممبر:**\n\n1️⃣ **دریافت سکه:** با عضویت"
        " در کانال‌های دیگران سکه بگیرید.\n2️⃣ **ثبت تبلیغ:** با خرج کردن سکه‌ها،"
        " کانال خودتان را در معرض دید بگذارید.\n3️⃣ **دعوت از دوستان:** با کد دعوت"
        " خودتان دوستانتان را دعوت کنید.\n4️⃣ **گردونه شانس:** هر ۲۴ ساعت شانس"
        " خود را امتحان کنید.\n5️⃣ **کد هدیه:** کدهایی که در کانال اطلاع‌رسانی"
        " می‌گذاریم را وارد کنید و جایزه بگیرید!"
    )
    send_message(chat_id, guide_text, get_main_keyboard(chat_id))
    return

  elif text == "🛠 پنل مدیریت" and chat_id in ADMIN_IDS:
    total_users = len(users_db)
    total_coins = sum(wallets.values())
    total_campaigns = len(campaigns_db)
    total_orders = len(created_groups_db)
    admin_kb = {
        "keyboard": [
            [{"text": "📢 ارسال پیام همگانی"}],
            [{"text": "🎁 ساخت کد هدیه"}],
            [{"text": "🔙 بازگشت به منوی اصلی"}],
        ],
        "resize_keyboard": True,
    }
    send_message(
        chat_id,
        f"🛠 **پنل مدیریت ربات:**\n\n👥 کل کاربران: {total_users}\n💰 مجموع"
        f" سکه‌های در گردش: {total_coins}\n📢 تبلیغ‌های فعال: {total_campaigns}\n📂"
        f" سفارش‌های ساخت: {total_orders}",
        admin_kb,
    )
    return

  elif text == "📢 ارسال پیام همگانی" and chat_id in ADMIN_IDS:
    waiting_for_broadcast.append(chat_id)
    send_message(
        chat_id,
        "📢 لطفاً پیام مورد نظر خود را برای ارسال همگانی به همه کاربران ارسال"
        " کنید:",
        get_back_keyboard(),
    )
    return

  elif text == "🎁 ساخت کد هدیه" and chat_id in ADMIN_IDS:
    waiting_for_new_gift_code.append(chat_id)
    send_message(
        chat_id,
        "🎁 لطفاً کد هدیه و مقدار سکه را با فرمت زیر ارسال کنید (مثال: `EID1405"
        " 100`):",
        get_back_keyboard(),
    )
    return

  else:
    send_message(
        chat_id,
        "❌ دستور نامعتبر است. از دکمه‌های کیبورد استفاده کنید.",
        get_main_keyboard(chat_id),
    )


# ---------------- POLLING LOOP ----------------
def run_bot():
  global last_update_id
  load_database()
  print("Bot started polling...")
  while True:
    try:
      url = f"{BASE_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
      response = requests.get(url, timeout=35)
      data = response.json()
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


# ---------------- FLASK SERVER FOR RENDER ----------------
app = Flask(__name__)


@app.route("/")
def home():
  return "Bale Member-Gir Bot is running!"


def self_ping():
  render_url = os.environ.get("RENDER_EXTERNAL_URL")
  if render_url:
    while True:
      time.sleep(300)  # every 5 minutes
      try:
        requests.get(render_url)
      except:
        pass


if __name__ == "__main__":
  # Start bot polling in a background thread
  bot_thread = threading.Thread(target=run_bot, daemon=True)
  bot_thread.start()

  # Start self-ping thread
  ping_thread = threading.Thread(target=self_ping, daemon=True)
  ping_thread.start()

  # Start Flask web server
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)
