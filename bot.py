import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import re
import io

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
ADMIN_IDS = [8422485324]
SUPPORT_GROUP_LINK = "https://t.me/instaXhubsaport"
SUPPORT_GROUP_USERNAME = "@instaXhubsaport"
ADMIN_USERNAME = "Adiminsaport"

bot = telebot.TeleBot(TOKEN)

# Tracking states
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
        'welcome_msg': '✨ **আসসালামু আলাইকুম! InstaXhub বটে আপনাকে স্বাগতম** 🌟\n\n💼 আমাদের বটে ইনস্টাগ্রাম অ্যাকাউন্ট দিয়ে আপনি খুব সহজেই প্রতিদিন চমৎকার ইনকাম করতে পারবেন। এটি একটি ১০০% অটোমেটেড ও বিশ্বস্ত প্ল্যাটফর্ম।',
        'ref_msg': '🎁 **আপনার রেফারেল লিংক ব্যবহার করে বন্ধুদের ইনভাইট করুন এবং বোনাস পান!**',
        'helpline_msg': '📞 **হেল্পলাইন প্যানেল:**\n\nযেকোনো সমস্যায় নিচে যোগাযোগ করুন:',
        'rules_text': '📜 **কাজের নিয়মাবলী:**\n\n১. বটের দেওয়া ইউজারনেম দিয়ে ইনস্টাগ্রাম আইডি খুলুন।\n২. সঠিক ২FA Secret Key দিন।',
        'video_link': 'https://youtube.com',
        'channel_link': SUPPORT_GROUP_LINK,
        'admin_username': ADMIN_USERNAME,
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

def send_must_join_msg(chat_id):
    channel_link = get_setting("channel_link", SUPPORT_GROUP_LINK)
    
    text = (
        "⚠️ **আমাদের বটে কাজ করার জন্য অবশ্যই অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হন।**"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 অফিশিয়াল সাপোর্ট গ্রুপে জয়েন করুন", url=channel_link),
        types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_joined")
    )
    
    # জয়েন না করা পর্যন্ত মেনু কিবোর্ড রিমুভ রাখা হবে
    remove_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

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
        types.InlineKeyboardButton("💵 টাস্ক রেট", callback_data="adm_task_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_withdraw"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton(status_btn, callback_data="adm_toggle_bot"),
        types.InlineKeyboardButton("📢 জয়েন চ্যানেল এডিট", callback_data="adm_edit_channel"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="adm_edit_rules"),
        types.InlineKeyboardButton("👋 ওয়েলকাম মেসেজ", callback_data="adm_edit_welcome"),
        types.InlineKeyboardButton("🎁 রেফার মেসেজ", callback_data="adm_edit_ref_msg"),
        types.InlineKeyboardButton("🎧 হেল্পলাইন মেসেজ", callback_data="adm_edit_help_msg"),
        types.InlineKeyboardButton("🎬 ভিডিও লিংক এডিট", callback_data="adm_edit_video"),
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("📥 বায়ার রিপোর্ট আপলোড", callback_data="adm_upload_report"),
        types.InlineKeyboardButton("⚙️ রিপোর্ট ফিল্টার সেটআপ", callback_data="adm_filter_setup")
    )
    return markup

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "নাই"
    
    args = message.text.split()
    ref_by = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, referred_by, joined_date) VALUES (?, ?, ?, ?)",
                       (user_id, username, ref_by, int(time.time())))
        if ref_by and ref_by != user_id:
            ref_bonus = float(get_setting("ref_bonus", "1"))
            cursor.execute("UPDATE users SET balance = balance + ?, total_balance = total_balance + ? WHERE user_id = ?", (ref_bonus, ref_bonus, ref_by))
            try:
                bot.send_message(ref_by, f"🎉 আপনার রেফারেল লিংকে একজন নতুন ইউজার যুক্ত হয়েছে! আপনি ৳{ref_bonus} বোনাস পেয়েছেন।")
            except:
                pass
    conn.commit()
    conn.close()

    # ১. ভেরিফাই করবে জয়েন আছে কিনা
    if check_must_join(user_id):
        # জয়েন থাকলে মূল ওয়েলকাম মেসেজ ও মেনু বাটন পাঠাবে
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **নিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশনটি বেছে নিন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        # জয়েন না থাকলে শুধু নোটিফিকেশন ও ২ টি বাটন পাঠাবে
        send_must_join_msg(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    if check_must_join(user_id):
        bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=False)
        
        # সফল হলে মেনু বাটন দেয়া হবে
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **আপনার জয়েনিং সফল হয়েছে! নিচের মেনু থেকে কাজ শুরু করুন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        # জয়েন না থাকলে পপ-আপ অ্যালার্ট নোটিফিকেশন দেবে
        bot.answer_callback_query(
            call.id, 
            "⚠️ দয়া করে আগে আমাদের অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হন, তারপরে কাজ শুরু করুন!", 
            show_alert=True
        )

@bot.message_handler(commands=['admin'])
def handle_admin_cmd(message):
    if is_admin(message.from_user.id):
        status = get_setting("bot_status", "ON")
        bot.send_message(message.chat.id, f"⚙️ **ADMIN CONTROL DASHBOARD** ⚙️\n\n🤖 **বট স্ট্যাটাস:** 🟢 {status}", reply_markup=full_admin_dashboard(), parse_mode="Markdown")

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
        bot.send_message(user_id, "🔍 **ইনস্টাগ্রাম অ্যাকাউন্ট ভেরিফাই করা হচ্ছে...**\n\n🔑 **আপনার ইনস্টাগ্রামের সঠিক 2FA Secret Key টি মেসেজে পাঠান:**", parse_mode="Markdown")

# ==================== MAIN ROUTER ====================
@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Must Join Enforcement for any message
    if not check_must_join(user_id):
        send_must_join_msg(user_id)
        return

    # User menu handling only when joined
    if text == "💼 কাজ শুরু করুন 🚀":
        if get_setting("bot_status", "ON") == "OFF":
            bot.send_message(user_id, "🚫 **বর্তমানে বট সাময়িকভাবে বন্ধ আছে!** পরে চেষ্টা করুন।")
            return
        
        task_rate = get_setting("task_rate", "3")
        ig_user, ig_pass = generate_credentials()
        user_active_task[user_id] = {"username": ig_user, "password": ig_pass}

        msg = f"🤖 **নতুন ইনস্টাগ্রাম আইডি তৈরির কাজ:**\n\n💰 **পাবেন:** ৳{task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nউপরের তথ্য দিয়ে ইনস্টাগ্রাম আইডি খুলে ২FA সেটআপ করুন এবং নিচের বাটনে ক্লিক করুন।"
        
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
        min_w = get_setting("min_withdraw", "100")
        
        msg = f"👤 **ইউজার প্রোফাইল:**\n\n🆔 **UID:** `{user_id}`\n💵 **বর্তমান ব্যালেন্স:** ৳{c_bal:.2f} BDT\n⏳ **পেন্ডিং ব্যালেন্স:** ৳{p_bal:.2f} BDT\n💰 **মোট অর্জিত ব্যালেন্স:** ৳{t_bal:.2f} BDT\n\n💳 **মিনিমাম উইথড্র:** ৳{min_w} BDT"
        bot.send_message(user_id, msg, parse_mode="Markdown")

    elif text == "📊 কাজের রিপোর্ট 📈":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
        pending_cnt = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
        approved_cnt = cursor.fetchone()[0]
        
        cursor.execute("SELECT pending_balance, total_balance FROM users WHERE user_id = ?", (user_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        p_bal = user_data[0] if user_data else 0.0
        t_bal = user_data[1] if user_data else 0.0

        report_msg = (
            f"📊 **আপনার কাজের আপডেট রিপোর্ট:**\n\n"
            f"⏳ **পেন্ডিং কাজ:** {pending_cnt} টি (৳{p_bal:.2f})\n"
            f"✅ **অনুমোদিত কাজ:** {approved_cnt} টি\n"
            f"💰 **মোট কাজের ইনকাম:** ৳{t_bal:.2f} BDT"
        )
        bot.send_message(user_id, report_msg, parse_mode="Markdown")

    elif text == "📜 কাজের নিয়ম ⚠️":
        bot.send_message(user_id, get_setting("rules_text"), parse_mode="Markdown")

    elif text == "🎬 কাজের ভিডিও 🎬":
        v_link = get_setting("video_link", "https://youtube.com")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 টিউটোরিয়াল দেখুন", url=v_link))
        bot.send_message(user_id, "🎬 **কাজের ভিডিও দেখতে নিচে ক্লিক করুন:**", reply_markup=markup)

    elif text == "👥 রেফার করুন 🎁":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        ref_bonus = get_setting("ref_bonus", "1")
        custom_ref_msg = get_setting("ref_msg")
        msg = f"{custom_ref_msg}\n\n🔗 **আপনার রেফারেল লিংক:**\n`{ref_link}`\n\nপ্রতিটি সফল রেফারে পাবেন ৳{ref_bonus} বোনাস!"
        bot.send_message(user_id, msg, parse_mode="Markdown")

    elif text == "🆘 হেল্পলাইন 📞":
        channel_link = get_setting("channel_link", SUPPORT_GROUP_LINK)
        admin_user = get_setting("admin_username", ADMIN_USERNAME).replace("@", "")
        custom_help_msg = get_setting("helpline_msg")
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🧑‍💼 Admin Support", url=f"https://t.me/{admin_user}"),
            types.InlineKeyboardButton("👥 Support Group", url=channel_link)
        )
        bot.send_message(user_id, custom_help_msg, reply_markup=markup, parse_mode="Markdown")

bot.infinity_polling()
