import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import base64
import requests
import openpyxl
import io

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
ADMIN_IDS = [8422485324]
SUPPORT_GROUP_LINK = "https://t.me/instaXhubsaport"
SUPPORT_GROUP_USERNAME = "@instaXhubsaport"  # সাপোর্ট গ্রুপের সঠিক Username
ADMIN_USERNAME = "Adiminsaport"

bot = telebot.TeleBot(TOKEN)

# ট্র্যাকিং ডিকশনারি
admin_states = {}
user_active_task = {}

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
        'welcome_msg': '✨ **INSTAXHUB বটে আপনাকে স্বাগতম!**\n\nবট ব্যবহার করতে অবশ্যই নিচে দেওয়া সাপোর্ট গ্রুপে জয়েন থাকতে হবে।',
        'rules_text': '📜 **কাজের নিয়মাবলী:**\n\n১. বটের দেওয়া ইউজারনেম দিয়ে ইনস্টাগ্রাম আইডি খুলুন।\n২. সঠিক ২FA Secret Key দিন।\n৩. বায়ার ফাইল চেক করার পর পেমেন্ট মেইন ব্যালেন্সে যুক্ত হবে।',
        'video_link': 'https://youtube.com',
        'channel_link': SUPPORT_GROUP_LINK,
        'ref_msg': '🎁 আপনার রেফারেল লিংক শেয়ার করে ইনকাম করুন!',
        'help_msg': '📞 সহায়তার জন্য এডমিন অথবা গ্রুপে যোগাযোগ করুন।',
        'report_mode': 'COLOR',
        'pass_match': 'GREEN',
        'fail_match': 'WHITE',
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
    text = "⚠️ **সতর্কবার্তা!**\n\nবট ব্যবহার করার জন্য আপনাকে বাধ্যতামূলক আমাদের সাপোর্ট গ্রুপে জয়েন হতে হবে। জয়েন না করলে মেনু বাটন আসবে না।\n\nগ্রুপে জয়েন করে নিচে **'✅ জয়েন করেছি'** বাটনে চাপ দিন।"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপে জয়েন করুন", url=channel_link),
        types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_joined")
    )
    # রিপ্লাই কিবোর্ড রিমুভ করে দেওয়া হচ্ছে যাতে জয়েন না করে কাজ না করতে পারে
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
        types.InlineKeyboardButton("🏆 টপ ৫ রেফারার", callback_data="adm_top_ref"),
        types.InlineKeyboardButton("🏆 টপ ৫ ওয়ার্কার", callback_data="adm_top_work"),
        types.InlineKeyboardButton("✉️ সেন্ড কাস্টম মেসেজ", callback_data="adm_custom_msg"),
        types.InlineKeyboardButton("💰 এড ব্যালেন্স", callback_data="adm_add_bal"),
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="adm_stock_info"),
        types.InlineKeyboardButton("📲 স্টক ডাউনলোড", callback_data="adm_stock_dl"),
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="adm_task_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_withdraw"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton(status_btn, callback_data="adm_toggle_bot"),
        types.InlineKeyboardButton("📢 জয়েন চ্যানেল এডিট", callback_data="adm_edit_channel"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="adm_edit_rules"),
        types.InlineKeyboardButton("👋 ওয়েলকাম মেসেজ", callback_data="adm_welcome_msg"),
        types.InlineKeyboardButton("🎁 রেফার মেসেজ", callback_data="adm_ref_msg"),
        types.InlineKeyboardButton("🎧 হেল্পলাইন মেসেজ", callback_data="adm_help_msg"),
        types.InlineKeyboardButton("🎬 ভিডিও লিংক এডিট", callback_data="adm_edit_video"),
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("📤 বায়ার রিপোর্ট আপলোড (.xlsx)", callback_data="admin_upload_report"),
        types.InlineKeyboardButton("⚙️ রিপোর্ট ফিল্টার সেটআপ", callback_data="admin_config_filter")
    )
    return markup

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "নাই"
    
    args = message.text.split()
    referred_by = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, referred_by, joined_date) VALUES (?, ?, ?, ?)",
                   (user_id, username, referred_by, int(time.time())))
    conn.commit()
    conn.close()

    # বাধ্যতামূলক গ্রুপ জয়েন চেক
    if not check_must_join(user_id):
        # রিমুভ কিবোর্ড মেসেজ
        rm = types.ReplyKeyboardRemove()
        bot.send_message(user_id, "🔒 **বট আনলক করতে সাপোর্ট গ্রুপে জয়েন করুন!**", reply_markup=rm)
        send_must_join_msg(user_id)
        return

    text = get_setting("welcome_msg")
    bot.send_message(user_id, text, reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    if check_must_join(user_id):
        bot.answer_callback_query(call.id, "✅ জয়েন ভেরিফিকেশন সফল!", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        text = get_setting("welcome_msg")
        bot.send_message(user_id, text, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো গ্রুপে জয়েন করেননি!", show_alert=True)

@bot.message_handler(commands=['admin'])
def handle_admin_cmd(message):
    if is_admin(message.from_user.id):
        bot_status = get_setting("bot_status", "ON")
        bot.send_message(
            message.chat.id, 
            f"⚙️ **ADMIN CONTROL DASHBOARD** ⚙️\n\n🤖 **বট স্ট্যাটাস:** 🟢 {bot_status}", 
            reply_markup=full_admin_dashboard(), 
            parse_mode="Markdown"
        )

# ==================== MAIN ROUTER ====================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    # ১. এডমিন কমান্ড ইনপুট প্রসেসিং (স্টেট বেসড)
    if is_admin(user_id) and user_id in admin_states:
        state = admin_states.pop(user_id)
        
        if state == "adm_add_bal":
            process_add_bal(message)
        elif state == "adm_custom_msg":
            process_custom_msg(message)
        elif state == "adm_broadcast":
            process_broadcast(message)
        elif state.startswith("set_"):
            setting_key = state.replace("set_", "")
            set_setting(setting_key, text.strip())
            bot.send_message(user_id, f"✅ **আপডেট সফল হয়েছে!**\nনতুন মান: `{text.strip()}`", parse_mode="Markdown")
        return

    # ২. বাধ্যতামূলক চ্যানেল জয়েন গার্ড (Must Join Guard)
    if not check_must_join(user_id):
        send_must_join_msg(user_id)
        return

    # ৩. ইউজার মেনু অ্যাকশনস
    if text == "💼 কাজ শুরু করুন 🚀":
        handle_work(message)
    elif text == "💰 ব্যালেন্স & উইথড্র 💳":
        handle_balance(message)
    elif text == "📊 কাজের রিপোর্ট 📈":
        handle_report(message)
    elif text == "📜 কাজের নিয়ম ⚠️":
        rules = get_setting("rules_text", "📜 **কাজের নিয়মাবলী পাওয়া যায়নি!**")
        bot.send_message(user_id, rules, parse_mode="Markdown")
    elif text == "🎬 কাজের ভিডিও 🎬":
        vid_link = get_setting("video_link", "https://youtube.com")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 ভিডিও টিউটোরিয়াল দেখুন", url=vid_link))
        bot.send_message(user_id, "🎬 **কাজের ভিডিও দেখতে নিচের বাটনে ক্লিক করুন:**", reply_markup=markup, parse_mode="Markdown")
    elif text == "👥 রেফার করুন 🎁":
        handle_referral(message)
    elif text == "🆘 হেল্পলাইন 📞":
        help_msg = get_setting("help_msg", "📞 **হেল্পলাইন & সাপোর্ট Centre:**")
        channel_link = get_setting("channel_link", SUPPORT_GROUP_LINK)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("👨‍💻 Admin Support", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"),
            types.InlineKeyboardButton("👥 Group Support", url=channel_link)
        )
        bot.send_message(user_id, help_msg, reply_markup=markup, parse_mode="Markdown")

# --- FUNCTIONS ---
def handle_balance(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, pending_balance, total_balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    curr_bal = res[0] if res else 0.0
    pend_bal = res[1] if res else 0.0
    tot_bal = res[2] if res else 0.0
    min_w = get_setting("min_withdraw", "100")
    
    text = f"👤 **ইউজার প্রোফাইল:**\n\n🆔 **UID:** `{user_id}`\n💵 **বর্তমান ব্যালেন্স:** ৳{curr_bal:.2f} BDT\n⏳ **পেন্ডিং ব্যালেন্স:** ৳{pend_bal:.2f} BDT\n💰 **মোট ব্যালেন্স:** ৳{tot_bal:.2f} BDT\n\n⚠️ সর্বনিম্ন উইথড্র **৳{min_w} BDT**।"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 উইথড্র রিকোয়েস্ট দিন", callback_data="req_withdraw"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

def handle_report(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
    app_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    pen_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'REJECTED'", (user_id,))
    rej_cnt = cursor.fetchone()[0]
    conn.close()

    text = f"📊 **কাজের রিপোর্ট:**\n\n✅ এপ্রুভড: {app_cnt} টি\n⏳ পেন্ডিং: {pen_cnt} টি\n❌ রিজেক্টেড: {rej_cnt} টি"
    bot.send_message(user_id, text, parse_mode="Markdown")

def handle_referral(message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_bonus = get_setting("ref_bonus", "1")
    
    text = f"🎁 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n💰 **বোনাস:** প্রতি রেফারে ৳{ref_bonus} BDT"
    bot.send_message(user_id, text, parse_mode="Markdown")

def handle_work(message):
    bot_status = get_setting("bot_status", "ON")
    if bot_status == "OFF":
        bot.send_message(message.chat.id, "⚠️ **বট অফলাইনে আছে!**")
        return

    user_id = message.from_user.id
    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass, "attempts": 0}

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"),
        types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# --- ADMIN PROCESSORS (FIXED) ---
def process_add_bal(message):
    try:
        parts = message.text.strip().split()
        target_uid = int(parts[0])
        amount = float(parts[1])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_uid))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ UID `{target_uid}` এ ৳{amount} টাকা সফলভাবে যুক্ত করা হয়েছে।", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ **ভুল ফরম্যাট!** চেষ্টা করুন: `12345678 50` (ID এবং টাকার মাঝে একটি স্পেস দিন)")

def process_custom_msg(message):
    try:
        parts = message.text.strip().split(" ", 1)
        target_uid = int(parts[0])
        text_to_send = parts[1]
        bot.send_message(target_uid, f"📩 **মেসেজ:**\n\n{text_to_send}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ ইউজারের কাছে মেসেজ পাঠানো হয়েছে!")
    except Exception:
        bot.send_message(message.chat.id, "❌ **ভুল ফরম্যাট!** চেষ্টা করুন: `12345678 আপনার মেসেজ`")

def process_broadcast(message):
    text_to_send = message.text
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    success = 0
    for u in users:
        try:
            bot.send_message(u[0], text_to_send, parse_mode="Markdown")
            success += 1
            time.sleep(0.04)
        except Exception:
            pass
    bot.send_message(message.chat.id, f"📢 **ব্রডকাস্ট সম্পন্ন!** মোট {success} জন পেয়েছেন।")

# --- ADMIN CALLBACKS ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def handle_admin_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ অনুমতি নেই!")
        return

    action = call.data
    bot.answer_callback_query(call.id)

    if action in ["adm_task_rate", "adm_min_withdraw", "adm_ref_bonus", "adm_edit_channel", "adm_edit_rules", "adm_welcome_msg", "adm_ref_msg", "adm_help_msg", "adm_edit_video"]:
        prompt_map = {
            "adm_task_rate": ("নতুন টাস্ক রেট (টাকায়) লিখুন:", "set_task_rate"),
            "adm_min_withdraw": ("নতুন মিনিমাম উইথড্র টাকা লিখুন:", "set_min_withdraw"),
            "adm_ref_bonus": ("নতুন রেফার বোনাস টাকা লিখুন:", "set_ref_bonus"),
            "adm_edit_channel": ("নতুন সাপোর্ট গ্রুপ/চ্যানেল লিংক দিন:", "set_channel_link"),
            "adm_edit_rules": ("নতুন কাজের নিয়মাবলী লিখুন:", "set_rules_text"),
            "adm_welcome_msg": ("নতুন ওয়েলকাম মেসেজ লিখুন:", "set_welcome_msg"),
            "adm_ref_msg": ("নতুন রেফার মেসেজ লিখুন:", "set_ref_msg"),
            "adm_help_msg": ("নতুন হেল্পলাইন মেসেজ লিখুন:", "set_help_msg"),
            "adm_edit_video": ("নতুন ভিডিও টিউটোরিয়াল লিংক দিন:", "set_video_link")
        }
        msg_text, state_name = prompt_map[action]
        admin_states[user_id] = state_name
        bot.send_message(call.message.chat.id, f"📝 **{msg_text}**", parse_mode="Markdown")

    elif action == "adm_add_bal":
        admin_states[user_id] = "adm_add_bal"
        bot.send_message(call.message.chat.id, "💰 **ইউজার ID এবং টাকার পরিমাণ একসাথে পাঠান:**\n(ফরম্যাট: `12345678 50`)", parse_mode="Markdown")

    elif action == "adm_custom_msg":
        admin_states[user_id] = "adm_custom_msg"
        bot.send_message(call.message.chat.id, "✉️ **ইউজার ID এবং মেসেজ একসাথে লিখুন:**\n(ফরম্যাট: `12345678 আপনার মেসেজ`)", parse_mode="Markdown")

    elif action == "adm_broadcast":
        admin_states[user_id] = "adm_broadcast"
        bot.send_message(call.message.chat.id, "📢 **ব্রডকাস্ট মেসেজটি লিখুন:**", parse_mode="Markdown")

bot.infinity_polling()
