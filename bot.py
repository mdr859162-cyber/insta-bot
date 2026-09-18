import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import re

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
ADMIN_IDS = [8422485324]
SUPPORT_GROUP_LINK = "https://t.me/instaXhubsaport"
SUPPORT_GROUP_USERNAME = "@instaXhubsaport"
ADMIN_USERNAME = "Adiminsaport"

bot = telebot.TeleBot(TOKEN)

# ট্র্যাকিং
admin_states = {}
user_active_task = {}
user_waiting_input = {}

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0,
        pending_balance REAL DEFAULT 0.0,
        total_balance REAL DEFAULT 0.0,
        referred_by INTEGER,
        joined_date INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ig_username TEXT,
        ig_password TEXT,
        secret_key TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    defaults = {
        'task_rate': '3',
        'min_withdraw': '100',
        'ref_bonus': '1',
        'welcome_msg': '✨ **INSTAXHUB বটে আপনাকে স্বাগতম!**',
        'rules_text': '📜 **কাজের নিয়মাবলী:**\n\n১. বটের দেওয়া ইউজারনেম দিয়ে ইনস্টাগ্রাম আইডি খুলুন।\n২. সঠিক ২FA Secret Key দিন।',
        'video_link': 'https://youtube.com',
        'channel_link': SUPPORT_GROUP_LINK,
        'bot_status': 'ON'
    }
    
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

init_db()

def get_db():
    return sqlite3.connect("bot_database.db")

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_setting(key, default=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else default

def set_setting(key, value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def generate_credentials():
    username = "ig_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
    password = "Pass#" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
    return username, password

# ==================== MUST JOIN CHECK ====================
def check_must_join(user_id):
    if is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(SUPPORT_GROUP_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception:
        return False

def send_must_join_msg(user_id):
    channel_link = get_setting("channel_link", SUPPORT_GROUP_LINK)
    text = "⚠️ **সতর্কবার্তা!**\n\nবট ব্যবহার করার জন্য আপনাকে বাধ্যতামূলক আমাদের সাপোর্ট গ্রুপে জয়েন হতে হবে।"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপে জয়েন করুন", url=channel_link),
        types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_joined")
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# ==================== KEYBOARDS ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💼 কাজ শুরু করুন 🚀"), types.KeyboardButton("💰 ব্যালেন্স & উইথড্র 💳"),
        types.KeyboardButton("📊 কাজের রিপোর্ট 📈"), types.KeyboardButton("📜 কাজের নিয়ম ⚠️"),
        types.KeyboardButton("👥 রেফার করুন 🎁"), types.KeyboardButton("🎬 কাজের ভিডিও 🎬"),
        types.KeyboardButton("🆘 হেল্পলাইন 📞")
    )
    return markup

def full_admin_dashboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    status = get_setting("bot_status", "ON")
    status_btn = "🔴 বট OFF করুন" if status == "ON" else "🟢 বট ON করুন"
    
    markup.add(
        types.InlineKeyboardButton("✉️ সেন্ড কাস্টম মেসেজ", callback_data="adm_custom_msg"),
        types.InlineKeyboardButton("💰 এড ব্যালেন্স", callback_data="adm_add_bal"),
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="adm_task_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_withdraw"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton(status_btn, callback_data="adm_toggle_bot"),
        types.InlineKeyboardButton("📢 জয়েন চ্যানেল এডিট", callback_data="adm_edit_channel"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="adm_edit_rules"),
        types.InlineKeyboardButton("🎬 ভিডিও লিংক এডিট", callback_data="adm_edit_video")
    )
    return markup

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "নাই"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                   (user_id, username, int(time.time())))
    conn.commit()
    conn.close()

    if not check_must_join(user_id):
        bot.send_message(user_id, "🔒 **বট আনলক করতে সাপোর্ট গ্রুপে জয়েন করুন!**", reply_markup=types.ReplyKeyboardRemove())
        send_must_join_msg(user_id)
        return

    text = get_setting("welcome_msg")
    bot.send_message(user_id, text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    if check_must_join(user_id):
        bot.answer_callback_query(call.id, "✅ জয়েন ভেরিফিকেশন সফল!", show_alert=True)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, get_setting("welcome_msg"), reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো গ্রুপে জয়েন করেননি!", show_alert=True)

@bot.message_handler(commands=['admin'])
def handle_admin_cmd(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "⚙️ **ADMIN CONTROL PANEL**", reply_markup=full_admin_dashboard(), parse_mode="Markdown")

# --- WORK & 2FA CALLBACKS ---
@bot.callback_query_handler(func=lambda call: call.data in ["get_2fa", "cancel_task"])
def handle_task_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "cancel_task":
        if user_id in user_active_task:
            del user_active_task[user_id]
        bot.answer_callback_query(call.id, "কাজ বাতিল করা হয়েছে")
        bot.edit_message_text("🚫 **আপনার কাজটি বাতিল করা হয়েছে!**\nনতুন কাজ নিতে '💼 কাজ শুরু করুন 🚀' বাটনে ক্লিক করুন।", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        
    elif call.data == "get_2fa":
        bot.answer_callback_query(call.id)
        user_waiting_input[user_id] = "WAITING_2FA"
        bot.send_message(user_id, "🔍 **ইনস্টাগ্রাম অ্যাকাউন্ট ভেরিফাই করা হচ্ছে...**\n\n🔑 **আপনার ইনস্টাগ্রামের সঠিক 2FA Key টি মেসেজে পাঠান:**", parse_mode="Markdown")

# ==================== MAIN ROUTER ====================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()

    # ১. এডমিন মোড ইনপুট
    if is_admin(user_id) and user_id in admin_states:
        state = admin_states.pop(user_id)
        
        if state == "adm_add_bal":
            match = re.match(r"^(\d+)\s+([\d\.]+)$", text)
            if match:
                target_uid, amount = int(match.group(1)), float(match.group(2))
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET balance = balance + ?, total_balance = total_balance + ? WHERE user_id = ?", (amount, amount, target_uid))
                conn.commit()
                conn.close()
                bot.send_message(user_id, f"✅ UID `{target_uid}` এ ৳{amount} টাকা এড করা হয়েছে।", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "❌ **ভুল ফরম্যাট!** এভাবে লিখুন: `12345678 50` (মাঝে একটি স্পেস দিন)", parse_mode="Markdown")
            return

        elif state == "adm_custom_msg":
            match = re.match(r"^(\d+)\s+(.+)$", text, re.DOTALL)
            if match:
                target_uid, msg_content = int(match.group(1)), match.group(2)
                try:
                    bot.send_message(target_uid, f"📩 **মেসেজ:**\n\n{msg_content}", parse_mode="Markdown")
                    bot.send_message(user_id, "✅ ইউজারের কাছে মেসেজ চলে গেছে!")
                except Exception as e:
                    bot.send_message(user_id, f"❌ মেসেজ পাঠানো যায়নি: {str(e)}")
            else:
                bot.send_message(user_id, "❌ **ভুল ফরম্যাট!** এভাবে লিখুন: `12345678 আপনার মেসেজ`", parse_mode="Markdown")
            return

        elif state.startswith("set_"):
            setting_key = state.replace("set_", "")
            set_setting(setting_key, text)
            bot.send_message(user_id, f"✅ **সেটিং আপডেট হয়েছে!**", parse_mode="Markdown")
            return

    # ২. ইউজার ২FA ইনপুট প্রসেস
    if user_id in user_waiting_input and user_waiting_input[user_id] == "WAITING_2FA":
        if len(text.replace(" ", "")) >= 16:
            try:
                totp = pyotp.TOTP(text.replace(" ", ""))
                current_code = totp.now()
                del user_waiting_input[user_id]
                
                # সেভ টাস্ক
                if user_id in user_active_task:
                    task_info = user_active_task.pop(user_id)
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, created_at) VALUES (?, ?, ?, ?, ?)",
                                   (user_id, task_info['username'], task_info['password'], text, int(time.time())))
                    cursor.execute("UPDATE users SET pending_balance = pending_balance + ? WHERE user_id = ?", 
                                   (float(get_setting("task_rate", "3")), user_id))
                    conn.commit()
                    conn.close()

                bot.send_message(user_id, f"✅ **2FA ভেরিফিকেশন সফল!**\n🔑 বর্তমান OTP কোড: `{current_code}`\n\nকাজটি বায়ার চেকিংয়ে পাঠানো হয়েছে।", parse_mode="Markdown")
            except Exception:
                bot.send_message(user_id, "❌ **ভুল 2FA Key!** সঠিক সিক্রেট কি ইনপুট দিন।", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "⚠️ **ভুল 2FA Key!** সঠিক ১৬-৩২ অক্ষরের সিক্রেট কি দিন।", parse_mode="Markdown")
        return

    # ৩. বাধ্যবাধকতা চেক
    if not check_must_join(user_id):
        send_must_join_msg(user_id)
        return

    # ৪. মূল বাটনের কাজসমূহ
    if text == "💼 কাজ শুরু করুন 🚀":
        task_rate = get_setting("task_rate", "3")
        ig_user, ig_pass = generate_credentials()
        user_active_task[user_id] = {"username": ig_user, "password": ig_pass}

        msg = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন।"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"),
            types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
        )
        bot.send_message(user_id, msg, reply_markup=markup, parse_mode="Markdown")

    elif text == "💰 ব্যালেন্স & উইথড্র 💳":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance, pending_balance, total_balance FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        conn.close()
        
        c_bal = res[0] if res else 0.0
        p_bal = res[1] if res else 0.0
        t_bal = res[2] if res else 0.0
        
        msg = f"👤 **ইউজার প্রোফাইল:**\n\n🆔 **UID:** `{user_id}`\n💵 **বর্তমান ব্যালেন্স:** ৳{c_bal:.2f} BDT\n⏳ **পেন্ডিং ব্যালেন্স:** ৳{p_bal:.2f} BDT\n💰 **মোট ব্যালেন্স:** ৳{t_bal:.2f} BDT"
        bot.send_message(user_id, msg, parse_mode="Markdown")

    elif text == "📜 কাজের নিয়ম ⚠️":
        bot.send_message(user_id, get_setting("rules_text"), parse_mode="Markdown")

    elif text == "🎬 কাজের ভিডিও 🎬":
        v_link = get_setting("video_link", "https://youtube.com")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 টিউটোরিয়াল দেখুন", url=v_link))
        bot.send_message(user_id, "🎬 **কাজের ভিডিও দেখতে নিচে ক্লিক করুন:**", reply_markup=markup, parse_mode="Markdown")

    elif text == "👥 রেফার করুন 🎁":
        bot_info = bot.get_me()
        bot.send_message(user_id, f"🎁 **রেফার লিংক:** https://t.me/{bot_info.username}?start={user_id}", parse_mode="Markdown")

    elif text == "🆘 হেল্পলাইন 📞":
        channel_link = get_setting("channel_link", SUPPORT_GROUP_LINK)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👥 গ্রুপ সাপোর্ট", url=channel_link))
        bot.send_message(user_id, "📞 **হেল্পলাইন প্যানেল:**", reply_markup=markup)

# --- ADMIN CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def handle_admin_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ অনুমতি নেই!")
        return

    action = call.data
    bot.answer_callback_query(call.id)

    if action == "adm_add_bal":
        admin_states[user_id] = "adm_add_bal"
        bot.send_message(call.message.chat.id, "💰 **ইউজার ID এবং টাকার পরিমাণ পাঠান:**\n\nউদাহরণ: `7252355835 50`", parse_mode="Markdown")

    elif action == "adm_custom_msg":
        admin_states[user_id] = "adm_custom_msg"
        bot.send_message(call.message.chat.id, "✉️ **ইউজার ID এবং মেসেজ একসাথে লিখুন:**\n\nউদাহরণ: `7252355835 আপনার মেসেজ`", parse_mode="Markdown")

bot.infinity_polling()
