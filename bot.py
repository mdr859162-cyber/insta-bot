import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import base64
import io
import openpyxl
import threading
import requests

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
ADMIN_USERNAME = "@Adiminsaport"
ADMIN_IDS = [8422485324]

bot = telebot.TeleBot(TOKEN)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0,
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
        created_at INTEGER,
        auto_approve_at INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS weekly_stats (
        user_id INTEGER PRIMARY KEY,
        ref_count INTEGER DEFAULT 0,
        work_count INTEGER DEFAULT 0
    )''')
    
    defaults = {
        'video_link': 'https://youtube.com',
        'group_chat_id': '@instaXhubsaport',
        'min_withdraw': '100',
        'task_rate': '3',
        'ref_bonus': '10',
        'bot_status': 'ON',
        'welcome_msg': '✨ **আসসালামু আলাইকুম! INSTAXHUB বটে আপনাকে স্বাগতম** 🌟\n\n💼 আমাদের বটে কাজ করতে হলে নিচে দেওয়া আমাদের অফিশিয়াল টেলিগ্রাম চ্যানেলে যুক্ত থাকুন।',
        'notice_msg': '📜 **কাজের নিয়মাবলী:**\n১. সঠিক তথ্য দিয়ে নতুন অ্যাকাউন্ট খুলুন।\n২. বটের দেওয়া ইউজারনেম ও পাসওয়ার্ড ব্যবহার করুন।\n৩. সঠিক 2FA Key প্রদান করুন।',
        'ref_msg': '🎁 **রেফার করে আনলিমিটেড আয় করুন!**',
        'helpline_msg': '🎧 **আমাদের সাপোর্ট টিম আপনার সেবায় নিয়োজিত!**\n\nযেকোনো সমস্যায় এডমিনের সাথে যোগাযোগ করুন।'
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

def clear_user_session(chat_id, user_id):
    bot.clear_step_handler_by_chat_id(chat_id=chat_id)
    if user_id in user_active_task:
        del user_active_task[user_id]

# ==================== GROUP CHECK ====================
def check_mandatory_join(user_id):
    if is_admin(user_id):
        return True
    group_id = get_setting("group_chat_id", "@instaXhubsaport")
    try:
        member = bot.get_chat_member(group_id, user_id)
        return member.status in ['creator', 'administrator', 'member', 'restricted']
    except Exception:
        return True

# ==================== VALIDATION ENGINE ====================
def is_valid_2fa_secret(secret_key):
    try:
        cleaned = secret_key.replace(" ", "").upper()
        if len(cleaned) < 16 or len(cleaned) > 32:
            return False
        base64.b32decode(cleaned, casefold=True)
        totp = pyotp.TOTP(cleaned)
        code = totp.now()
        return len(code) == 6 and code.isdigit()
    except Exception:
        return False

def verify_instagram_account_exists(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        return res.status_code == 200
    except Exception:
        return True

# ==================== BACKGROUND AUTO-APPROVER ====================
def background_auto_approver():
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor()
            now = int(time.time())
            
            cursor.execute("SELECT id, user_id, ig_username, secret_key FROM tasks WHERE status = 'PENDING' AND auto_approve_at <= ?", (now,))
            pending_tasks = cursor.fetchall()

            for task in pending_tasks:
                t_id, u_id, ig_user, secret_key = task
                if verify_instagram_account_exists(ig_user) and is_valid_2fa_secret(secret_key):
                    task_rate = float(get_setting("task_rate", "3"))
                    ref_bonus = float(get_setting("ref_bonus", "10"))

                    cursor.execute("UPDATE tasks SET status = 'APPROVED' WHERE id = ?", (t_id,))
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (task_rate, u_id))
                    cursor.execute("INSERT INTO weekly_stats (user_id, work_count) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET work_count = work_count + 1", (u_id,))

                    cursor.execute("SELECT referred_by FROM users WHERE user_id = ?", (u_id,))
                    u_info = cursor.fetchone()
                    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (u_id,))
                    app_count = cursor.fetchone()[0]

                    if app_count == 1 and u_info and u_info[0]:
                        ref_by = u_info[0]
                        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (ref_bonus, ref_by))
                        try: bot.send_message(ref_by, f"🎉 **রেফার বোনাস!** আপনার রেফার করা ইউজার ১ম কাজ সম্পন্ন করায় পেয়েছেন ৳{ref_bonus:.2f}", parse_mode="Markdown")
                        except Exception: pass

                    conn.commit()
                    try: bot.send_message(u_id, f"🎉 **আপনার কাজটি অটো-এপ্রুভ হয়েছে!**\n💰 ওয়ালেটে যোগ হয়েছে: **৳{task_rate:.2f}**", parse_mode="Markdown")
                    except Exception: pass
                else:
                    cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE id = ?", (t_id,))
                    conn.commit()
                    try: bot.send_message(u_id, "❌ **আপনার কাজটি রিজেক্ট করা হয়েছে।**", parse_mode="Markdown")
                    except Exception: pass

            conn.close()
        except Exception: pass
        time.sleep(30)

threading.Thread(target=background_auto_approver, daemon=True).start()

# ==================== MAIN MENU KEYBOARD ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💼 কাজ শুরু করুন 🚀"), types.KeyboardButton("💰 ব্যালেন্স & উইথড্র 💳"),
        types.KeyboardButton("📊 কাজের রিপোর্ট 📈"), types.KeyboardButton("📜 কাজের নিয়ম ⚠️"),
        types.KeyboardButton("👥 রেফার করুন 🎁"), types.KeyboardButton("🎬 আমি নতুন (কাজের ভিডিও) 🎬"),
        types.KeyboardButton("🆘 হেল্পলাইন 📞")
    )
    return markup

# ==================== USER HANDLERS ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)
    username = message.from_user.username or ""
    
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, referred_by, joined_date) VALUES (?, ?, ?, ?)",
                       (user_id, username, referrer_id, int(time.time())))
        if referrer_id:
            cursor.execute("INSERT INTO weekly_stats (user_id, ref_count) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET ref_count = ref_count + 1", (referrer_id,))
            conn.commit()
            try: bot.send_message(referrer_id, "🎉 **একজন নতুন ইউজার আপনার রেফার লিংকে যুক্ত হয়েছেন!**", parse_mode="Markdown")
            except Exception: pass
        conn.commit()
    conn.close()

    welcome_text = get_setting("welcome_msg")
    group_chat = get_setting("group_chat_id", "@instaXhubsaport").replace("@", "")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 সাপোর্ট গ্রুপে জয়েন করুন", url=f"https://t.me/{group_chat}"),
        types.InlineKeyboardButton("✅ জয়েন করেছি / Start 🚀", callback_data="click_start")
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "click_start")
def click_start_handler(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    if not check_mandatory_join(user_id):
        bot.send_message(user_id, "❌ **আপনি এখনও সাপোর্ট গ্রুপে জয়েন করেননি!** আগে জয়েন করুন।", parse_mode="Markdown")
        return
    bot.send_message(user_id, "স্বাগতম! নিচে মূল মেনু ব্যবহার করে কাজ শুরু করুন:", reply_markup=main_menu())

user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)
    
    if get_setting("bot_status", "ON") == "OFF" and not is_admin(user_id):
        bot.send_message(user_id, "⚠️ **বট বর্তমানে বন্ধ আছে।**", parse_mode="Markdown")
        return

    if not check_mandatory_join(user_id):
        group_chat = get_setting("group_chat_id", "@instaXhubsaport").replace("@", "")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 সাপোর্ট গ্রুপে জয়েন করুন", url=f"https://t.me/{group_chat}"))
        bot.send_message(user_id, "❌ **কাজ করতে হলে আগে আমাদের গ্রুপে জয়েন করুন!**", reply_markup=markup, parse_mode="Markdown")
        return

    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass, "attempts": 0}

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন।"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"))
    markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_handler(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id, "কাজটি বাতিল করা হয়েছে!", show_alert=False)
    clear_user_session(call.message.chat.id, user_id)
    try:
        bot.edit_message_text("❌ **এই কাজটি বাতিল করা হয়েছে।** নতুন কাজ করতে আবার বাটনে চাপ দিন।", 
                              call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ এই কাজটি বাতিল হয়ে গেছে! নতুন কাজ শুরু করুন।")
        return
    msg = bot.send_message(user_id, "🔑 **আপনার ইনস্টাগ্রাম অ্যাকাউন্টের সঠিক 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    if message.text in ["💼 কাজ শুরু করুন 🚀", "💰 ব্যালেন্স & উইথড্র 💳", "📊 কাজের রিপোর্ট 📈", "📜 কাজের নিয়ম ⚠️", "👥 রেফার করুন 🎁", "🎬 আমি নতুন (কাজের ভিডিও) 🎬", "🆘 হেল্পলাইন 📞"]:
        clear_user_session(message.chat.id, user_id)
        return

    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ **সেশন আউট!** নতুন করে কাজ শুরু করুন।", parse_mode="Markdown")
        return

    secret_key = message.text.strip().replace(" ", "").upper()
    if not is_valid_2fa_secret(secret_key):
        user_active_task[user_id]["attempts"] += 1
        att = user_active_task[user_id]["attempts"]
        if att >= 3:
            clear_user_session(message.chat.id, user_id)
            bot.send_message(user_id, "⚠️ **পরপর ৩ বার ভুল 2FA Key দেওয়ায় কাজটি বাতিল হয়েছে।**", parse_mode="Markdown")
        else:
            msg = bot.send_message(user_id, f"❌ **ভুল/অকার্যকর 2FA Key!** সঠিক সিক্রেট কি দিন। (বাকি {3-att} বার)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_input)
        return

    try:
        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        user_active_task[user_id]["secret_key"] = secret_key
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("✅ একাউন্ট খোলা শেষ (Submit)", callback_data="finish_account"))
        markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
        bot.send_message(user_id, f"🔑 <b>আপনার 2FA OTP কোড:</b> <code>{totp_code}</code>\n\nকোডটি দিয়ে ২এফএ অন করে জমা দিন।", reply_markup=markup, parse_mode="HTML")
    except Exception:
        clear_user_session(message.chat.id, user_id)
        bot.send_message(user_id, "❌ **2FA কোড জেনারেট সম্ভব হয়নি!**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "finish_account")
def finish_account_submission(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    if user_id not in user_active_task or "secret_key" not in user_active_task[user_id]:
        bot.send_message(user_id, "❌ এই কাজটি বাতিল হয়েছে! নতুন কাজ শুরু করুন।")
        return

    task_data = user_active_task[user_id]
    clear_user_session(call.message.chat.id, user_id)
    now = int(time.time())

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at, auto_approve_at) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)",
                   (user_id, task_data["username"], task_data["password"], task_data["secret_key"], now, now + 21600))
    conn.commit()
    conn.close()

    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass
    bot.send_message(user_id, "✅ **কাজ জমা নেওয়া হয়েছে!** ৬ ঘণ্টার মধ্যে ভেরিফাই হয়ে যাবে।", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎬 আমি নতুন (কাজের ভিডিও) 🎬")
def handle_video_guide(message):
    clear_user_session(message.chat.id, message.from_user.id)
    v_link = get_setting("video_link", "https://youtube.com")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎥 টিউটোরিয়াল ভিডিও দেখুন", url=v_link))
    bot.send_message(message.from_user.id, "🎬 **নিচের বাটনে চাপ দিয়ে ভিডিও গাইড দেখে নিন:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    clear_user_session(message.chat.id, message.from_user.id)
    admin_clean = ADMIN_USERNAME.replace('@','')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 সরাসরি এডমিন সাপোর্ট", url=f"https://t.me/{admin_clean}"))
    bot.send_message(message.from_user.id, get_setting("helpline_msg"), reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ⚠️")
def handle_notice(message):
    clear_user_session(message.chat.id, message.from_user.id)
    bot.send_message(message.from_user.id, get_setting("notice_msg"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📊 কাজের রিপোর্ট 📈")
def handle_report(message):
    clear_user_session(message.chat.id, message.from_user.id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (message.from_user.id,))
    app = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (message.from_user.id,))
    pen = cursor.fetchone()[0]
    conn.close()
    bot.send_message(message.from_user.id, f"📊 **আপনার কাজের রিপোর্ট:**\n\n✅ সফল কাজ: **{app}** টি\n⏳ পেন্ডিং কাজ: **{pen}** টি", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👥 রেফার করুন 🎁")
def handle_ref(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_bonus_rate = float(get_setting("ref_bonus", "10"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    total_ref = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT u.user_id) FROM users u JOIN tasks t ON u.user_id = t.user_id WHERE u.referred_by = ? AND t.status = 'APPROVED'", (user_id,))
    earned_ref_count = cursor.fetchone()[0]
    conn.close()

    text = f"{get_setting('ref_msg')}\n\n📌 **প্রতি সফল রেফারে পাবেন:** ৳{ref_bonus_rate:.2f}\n🔗 **রেফার লিংক:** `{ref_link}`\n\n👥 মোট রেফারেল: **{total_ref}** জন\n💰 রেফার ইনকাম: **৳{earned_ref_count * ref_bonus_rate:.2f}**"
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স & উইথড্র 💳")
def handle_balance(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    bal = res[0] if res else 0.0
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    pending_count = cursor.fetchone()[0]
    min_wd = float(get_setting("min_withdraw", "100"))
    conn.close()

    text = f"📊 **আপনার অ্যাকাউন্ট তথ্য:**\n\n💰 **ব্যালেন্স:** ৳{bal:.2f}\n⏳ **পেন্ডিং কাজ:** {pending_count} টি"
    if bal < min_wd:
        text += f"\n\n❌ সর্বনিম্ন উইথড্র **৳{min_wd:.0f}**"
        bot.send_message(user_id, text, parse_mode="Markdown")
        return

    text += "\n\n💳 **মেথড পছন্দ করুন:**"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"), types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# ==================== FULL ADMIN CONTROL DASHBOARD ====================
@bot.message_handler(commands=['admin'])
def admin_dashboard(message):
    if not is_admin(message.from_user.id): return
    
    bot_status = get_setting("bot_status", "ON")
    status_text = "🟢 ON" if bot_status == "ON" else "🔴 OFF"
    text = f"⚙️ **ADMIN CONTROL DASHBOARD** ⚙️\n\n🤖 বট স্ট্যাটাস: {status_text}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🏆 টপ ৫ রেফারার", callback_data="adm_top_ref"),
        types.InlineKeyboardButton("🏆 টপ ৫ ওয়ার্কার", callback_data="adm_top_work"),
        types.InlineKeyboardButton("🔄 রিসেট টপ রেফারার", callback_data="adm_rst_ref"),
        types.InlineKeyboardButton("🔄 রিসেট টপ ওয়ার্কার", callback_data="adm_rst_work"),
        types.InlineKeyboardButton("✉️ সেন্ড কাস্টম মেসেজ", callback_data="adm_custom_msg"),
        types.InlineKeyboardButton("💰 এড ব্যালেন্স", callback_data="adm_add_bal"),
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="adm_stock"),
        types.InlineKeyboardButton("📬 স্টক ডাউনলোড", callback_data="adm_dl_stock"),
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="adm_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_wd"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton("🔘 বট OFF করুন" if bot_status=="ON" else "🔘 বট ON করুন", callback_data="adm_toggle_bot"),
        types.InlineKeyboardButton("📢 জয়েন চ্যানেল এডিট", callback_data="adm_edt_group"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="adm_edt_notice"),
        types.InlineKeyboardButton("👋 ওয়েলকাম মেসেজ", callback_data="adm_edt_welcome"),
        types.InlineKeyboardButton("🎁 রেফার মেসেজ", callback_data="adm_edt_ref"),
        types.InlineKeyboardButton("🎧 হেল্পলাইন মেসেজ", callback_data="adm_edt_help"),
        types.InlineKeyboardButton("🎬 ভিডিও লিংক এডিট", callback_data="adm_edt_video"),
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="adm_broadcast")
    )
    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callback_router(call):
    if not is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id)
    action = call.data
    uid = call.from_user.id

    conn = get_db()
    cursor = conn.cursor()

    if action == "adm_top_ref":
        cursor.execute("SELECT user_id, ref_count FROM weekly_stats ORDER BY ref_count DESC LIMIT 5")
        rows = cursor.fetchall()
        msg = "🏆 **টপ ৫ রেফারার:**\n\n"
        for i, r in enumerate(rows, 1): msg += f"{i}. ID: `{r[0]}` - {r[1]} জন\n"
        bot.send_message(uid, msg or "কোনো তথ্য পাওয়া যায়নি।", parse_mode="Markdown")

    elif action == "adm_top_work":
        cursor.execute("SELECT user_id, work_count FROM weekly_stats ORDER BY work_count DESC LIMIT 5")
        rows = cursor.fetchall()
        msg = "🏆 **টপ ৫ ওয়ার্কার:**\n\n"
        for i, r in enumerate(rows, 1): msg += f"{i}. ID: `{r[0]}` - {r[1]} টি কাজ\n"
        bot.send_message(uid, msg or "কোনো তথ্য পাওয়া যায়নি।", parse_mode="Markdown")

    elif action == "adm_rst_ref":
        cursor.execute("UPDATE weekly_stats SET ref_count = 0")
        conn.commit()
        bot.send_message(uid, "✅ **টপ রেফারার লিস্ট রিসেট করা হয়েছে!**")

    elif action == "adm_rst_work":
        cursor.execute("UPDATE weekly_stats SET work_count = 0")
        conn.commit()
        bot.send_message(uid, "✅ **টপ ওয়ার্কার লিস্ট রিসেট করা হয়েছে!**")

    elif action == "adm_toggle_bot":
        curr = get_setting("bot_status", "ON")
        new_s = "OFF" if curr == "ON" else "ON"
        set_setting("bot_status", new_s)
        bot.send_message(uid, f"✅ **বট স্ট্যাটাস পরিবর্তন করে {new_s} করা হয়েছে!**")

    elif action == "adm_stock":
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
        pen = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
        app = cursor.fetchone()[0]
        bot.send_message(uid, f"📊 **স্টক অবস্থা:**\n\n⏳ পেন্ডিং: **{pen}** টি\n✅ রেডি স্টক: **{app}** টি", parse_mode="Markdown")

    elif action == "adm_dl_stock":
        cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'APPROVED'")
        rows = cursor.fetchall()
        if not rows:
            bot.send_message(uid, "স্টকে কোনো কাজ নেই!")
            conn.close()
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Username", "Password", "Secret Key"])
        t_ids = [r[0] for r in rows]
        for r in rows: ws.append([r[1], r[2], r[3]])
        cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(t_ids))})", t_ids)
        conn.commit()
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        bot.send_document(uid, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **রেডি স্টক এক্সেল ডাউনলোড সম্পন্ন!**")

    elif action == "adm_add_bal":
        m = bot.send_message(uid, "👤 **যে ইউজারের ওয়ালেটে টাকা পাঠাতে চান তার User ID টি লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(m, process_add_bal_id)

    elif action == "adm_custom_msg":
        m = bot.send_message(uid, "👤 **যে ইউজারকে বার্তা পাঠাতে চান তার User ID লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(m, process_custom_msg_id)

    elif action == "adm_rate":
        m = bot.send_message(uid, "💰 **নতুন টাস্ক রেট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "task_rate", "টাস্ক রেট আপডেট হয়েছে!"))

    elif action == "adm_min_wd":
        m = bot.send_message(uid, "💳 **নতুন মিনিমাম উইথড্র লিমিট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "min_withdraw", "উইথড্র লিমিট আপডেট হয়েছে!"))

    elif action == "adm_ref_bonus":
        m = bot.send_message(uid, "🎁 **নতুন রেফার বোনাস লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "ref_bonus", "রেফার বোনাস আপডেট হয়েছে!"))

    elif action == "adm_edt_group":
        m = bot.send_message(uid, "📢 **নতুন টেলিগ্রাম সাপোর্ট চ্যানেলের ইউজারনেম লিখুন (যেমন: @instaXhubsaport):**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "group_chat_id", "চ্যানেল/গ্রুপ আপডেট হয়েছে!"))

    elif action == "adm_edt_notice":
        m = bot.send_message(uid, "📜 **নতুন কাজের নিয়মাবলী টেক্সট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "notice_msg", "কাজের নিয়ম আপডেট হয়েছে!"))

    elif action == "adm_edt_welcome":
        m = bot.send_message(uid, "👋 **নতুন ওয়েলকাম টেক্সট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "welcome_msg", "ওয়েলকাম টেক্সট আপডেট হয়েছে!"))

    elif action == "adm_edt_ref":
        m = bot.send_message(uid, "🎁 **নতুন রেফার টেক্সট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "ref_msg", "রেফার টেক্সট আপডেট হয়েছে!"))

    elif action == "adm_edt_help":
        m = bot.send_message(uid, "🎧 **নতুন হেল্পলাইন টেক্সট লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "helpline_msg", "হেল্পলাইন মেসেজ আপডেট হয়েছে!"))

    elif action == "adm_edt_video":
        m = bot.send_message(uid, "🎬 **নতুন ইউটিউব ভিডিও লিংকটি লিখুন:**")
        bot.register_next_step_handler(m, lambda msg: set_and_reply(msg, "video_link", "ভিডিও লিংক আপডেট হয়েছে!"))

    elif action == "adm_broadcast":
        m = bot.send_message(uid, "📢 **সব ইউজারের উদ্দেশ্যে ব্রডকাস্ট মেসেজটি লিখুন:**")
        bot.register_next_step_handler(m, process_broadcast)

    conn.close()

def set_and_reply(message, key, success_msg):
    set_setting(key, message.text.strip())
    bot.send_message(message.chat.id, f"✅ **{success_msg}**", parse_mode="Markdown")

def process_add_bal_id(message):
    try:
        target_id = int(message.text.strip())
        m = bot.send_message(message.chat.id, f"💵 **ID `{target_id}` এর জন্য কত টাকা যোগ করতে চান?**", parse_mode="Markdown")
        bot.register_next_step_handler(m, lambda msg: process_add_bal_amt(msg, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ **সঠিক ইউজার আইডি লিখুন!**")

def process_add_bal_amt(message, target_id):
    try:
        amt = float(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ **ID `{target_id}` এ ৳{amt:.2f} সফলভাবে যুক্ত হয়েছে!**", parse_mode="Markdown")
        try: bot.send_message(target_id, f"🎉 **এডমিন আপনার ওয়ালেটে ৳{amt:.2f} যোগ করেছেন!**", parse_mode="Markdown")
        except Exception: pass
    except Exception:
        bot.send_message(message.chat.id, "❌ **সঠিক পরিমাণ লিখুন!**")

def process_custom_msg_id(message):
    try:
        target_id = int(message.text.strip())
        m = bot.send_message(message.chat.id, f"✉️ **ID `{target_id}` কে পাঠানোর মেসেজটি লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(m, lambda msg: process_custom_msg_send(msg, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ **সঠিক ইউজার আইডি লিখুন!**")

def process_custom_msg_send(message, target_id):
    try:
        bot.send_message(target_id, f"📩 **এডমিন থেকে বার্তা:**\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ **মেসেজ সফলভাবে পাঠানো হয়েছে!**")
    except Exception:
        bot.send_message(message.chat.id, "❌ **মেসেজ পাঠানো সম্ভব হয়নি!**")

def process_broadcast(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    count = 0
    for u in users:
        try:
            bot.send_message(u[0], message.text, parse_mode="Markdown")
            count += 1
            time.sleep(0.04)
        except Exception: pass
    bot.send_message(message.chat.id, f"✅ **{count} জন ইউজারের কাছে ব্রডকাস্ট পাঠানো হয়েছে!**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["wd_bkash", "wd_nagad"])
def process_withdraw_method(call):
    bot.answer_callback_query(call.id)
    user_id = call.from_user.id
    method = "বিকাশ" if call.data == "wd_bkash" else "নগদ"
    user_withdraw_data = getattr(process_withdraw_method, 'user_withdraw_data', {})
    user_withdraw_data[user_id] = {"method": method}
    process_withdraw_method.user_withdraw_data = user_withdraw_data
    msg = bot.send_message(user_id, f"📱 **আপনার {method} নম্বর লিখুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_withdraw_number)

def get_withdraw_number(message):
    user_id = message.from_user.id
    user_withdraw_data = getattr(process_withdraw_method, 'user_withdraw_data', {})
    if user_id not in user_withdraw_data: return
    user_withdraw_data[user_id]["number"] = message.text.strip()
    msg = bot.send_message(user_id, "💵 **উইথড্র অ্যামাউন্ট (কত টাকা) লিখুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    user_id = message.from_user.id
    user_withdraw_data = getattr(process_withdraw_method, 'user_withdraw_data', {})
    if user_id not in user_withdraw_data: return
    try:
        amount = float(message.text.strip())
        wd_info = user_withdraw_data.pop(user_id)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = cursor.fetchone()[0]
        min_wd = float(get_setting("min_withdraw", "100"))

        if amount < min_wd or amount > balance:
            bot.send_message(user_id, "❌ **ভুল পরিমাণ দেওয়া হয়েছে!**", parse_mode="Markdown")
            conn.close()
            return

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

        bot.send_message(user_id, "✅ **আপনার উইথড্র রিকোয়েস্ট প্রসেসিং-এ আছে!**", parse_mode="Markdown")
        
        admin_msg = f"📩 **নতুন উইথড্র রিকোয়েস্ট:**\n👤 ইউজার: `{user_id}`\n💵 পরিমাণ: ৳{amount:.2f}\n💳 মেথড: {wd_info['method']}\n📱 নম্বর: `{wd_info['number']}`"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"wdapp_{user_id}_{amount}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"wdrej_{user_id}_{amount}"))

        for aid in ADMIN_IDS:
            try: bot.send_message(aid, admin_msg, reply_markup=markup, parse_mode="Markdown")
            except Exception: pass
    except Exception:
        bot.send_message(user_id, "❌ **সঠিক সংখ্যা লিখুন!**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wdapp_") or call.data.startswith("wdrej_"))
def handle_withdraw_approval(call):
    if not is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id)
    action, u_id, amt = call.data.split("_")
    u_id, amt = int(u_id), float(amt)
    
    if action == "wdapp":
        try: bot.send_message(u_id, f"🎉 **আপনার ৳{amt:.2f} টাকার উইথড্র সম্পন্ন হয়েছে!**", parse_mode="Markdown")
        except Exception: pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ✅ **APPROVED**", call.message.chat.id, call.message.message_id)
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, u_id))
        conn.commit()
        conn.close()
        try: bot.send_message(u_id, f"❌ **আপনার উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে।**", parse_mode="Markdown")
        except Exception: pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ❌ **REJECTED**", call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    print("🤖 InstaXhub Bot Full System Active...")
    bot.infinity_polling(skip_pending=True)
