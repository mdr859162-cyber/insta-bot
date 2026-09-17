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
GROUP_CHAT_ID = "@instaXhubsaport"

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
        'video_link': 'NO_LINK',
        'min_withdraw': '100',
        'task_rate': '3',
        'ref_bonus': '10',
        'bot_status': 'ON',
        'welcome_msg': '✨ **আসসালামু আলাইকুম! INSTAXHUB বটে আপনাকে স্বাগতম** 🌟\n\n💼 আমাদের বটে কাজ করে সহজে ইনকাম করুন।',
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

# ==================== GROUP CHECK ====================
def check_mandatory_join(user_id):
    if is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(GROUP_CHAT_ID, user_id)
        if member.status in ['creator', 'administrator', 'member', 'restricted']:
            return True
        return False
    except Exception:
        return True

# ==================== REAL-TIME AUTO VALIDATION ENGINE ====================
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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=6)
        return response.status_code == 200
    except Exception:
        return True

# ==================== BACKGROUND AUTO-APPROVER ====================
def background_auto_approver():
    """ ৬ ঘণ্টা পর ব্যাকগ্রাউন্ডে অটো পেমেন্ট প্রদান """
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
                        try:
                            bot.send_message(ref_by, f"🎉 **রেফার বোনাস!** আপনার রেফার করা ইউজার ১ম কাজ সম্পন্ন করায় পেয়েছেন ৳{ref_bonus:.2f}", parse_mode="Markdown")
                        except Exception: pass

                    conn.commit()

                    try:
                        bot.send_message(u_id, f"🎉 **আপনার জমা দেওয়া কাজটি অটো-এপ্রুভ হয়েছে!**\n💰 ওয়ালেটে যোগ হয়েছে: **৳{task_rate:.2f}**", parse_mode="Markdown")
                    except Exception: pass
                else:
                    cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE id = ?", (t_id,))
                    conn.commit()
                    try:
                        bot.send_message(u_id, "❌ **আপনার অ্যাকাউন্টটি ইনস্টাগ্রামে খুঁজে না পাওয়ায় কাজটি রিজেক্ট করা হয়েছে।**", parse_mode="Markdown")
                    except Exception: pass

            conn.close()
        except Exception:
            pass
        
        time.sleep(30)

threading.Thread(target=background_auto_approver, daemon=True).start()

# ==================== MAIN MENU KEYBOARD ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💼 কাজ শুরু করুন 🚀"), types.KeyboardButton("💰 ব্যালেন্স & উইথড্র 💳"),
        types.KeyboardButton("📊 কাজের রিপোর্ট 📈"), types.KeyboardButton("📜 কাজের নিয়ম ⚠️"),
        types.KeyboardButton("👥 রেফার করুন 🎁"), types.KeyboardButton("🎬 আমি নতুন (কাজের ভিডিও) 🎬"),
        types.KeyboardButton("🆘 হেল্পлайн 📞")
    )
    return markup

def clear_user_session(chat_id, user_id):
    """ যেকোনো আটকে থাকা সেশন এবং ইনপুট হ্যান্ডলার ক্লিয়ার করার ফাংশন """
    bot.clear_step_handler_by_chat_id(chat_id=chat_id)
    if user_id in user_active_task:
        del user_active_task[user_id]

# ==================== START & REFERRAL ====================
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
            try:
                bot.send_message(referrer_id, "🎉 **একজন নতুন ইউজার আপনার রেফার লিংকে যুক্ত হয়েছেন!**", parse_mode="Markdown")
            except Exception: pass

        conn.commit()
    conn.close()

    welcome_text = get_setting("welcome_msg")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Start 🚀", callback_data="click_start"))
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ==================== WORK FLOW (NO TIMELOCK & FIXED SESSION) ====================
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)
    
    if get_setting("bot_status", "ON") == "OFF" and not is_admin(user_id):
        bot.send_message(user_id, "⚠️ **বট বর্তমানে রক্ষণাবেক্ষণের (Maintenance) জন্য বন্ধ আছে।**", parse_mode="Markdown")
        return

    if not check_mandatory_join(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 সাপোর্ট গ্রুপে জয়েন করুন", url=f"https://t.me/{GROUP_CHAT_ID.replace('@','')}"))
        bot.send_message(user_id, "❌ **কাজ করতে হলে আগে আমাদের সাপোর্ট গ্রুপে জয়েন করুন!**", reply_markup=markup, parse_mode="Markdown")
        return

    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    
    user_active_task[user_id] = {
        "username": ig_user,
        "password": ig_pass,
        "attempts": 0
    }

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন।"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"))
    markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
    
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.answer_callback_query(call.id, "এই কাজটি বাতিল হয়ে গেছে!", show_alert=True)
        return
    
    msg = bot.send_message(user_id, "🔑 **আপনার ইনস্টাগ্রাম অ্যাকাউন্টের সঠিক 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    
    # মেনু বাটনে ক্লিক করলে কাজের প্রসেস থেকে বের হয়ে যাওয়া
    if message.text in ["💼 কাজ শুরু করুন 🚀", "💰 ব্যালেন্স & উইথড্র 💳", "📊 কাজের রিপোর্ট 📈", "📜 কাজের নিয়ম ⚠️", "👥 রেফার করুন 🎁", "🎬 আমি নতুন (কাজের ভিডিও) 🎬", "🆘 হেল্পলাইন 📞"]:
        clear_user_session(message.chat.id, user_id)
        return

    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ **সেশন আউট!** নতুন করে কাজ শুরু করুন।", parse_mode="Markdown")
        return

    secret_key = message.text.strip().replace(" ", "").upper()
    
    # ২এফএ ব্যাকএন্ড চেক
    if not is_valid_2fa_secret(secret_key):
        user_active_task[user_id]["attempts"] += 1
        att = user_active_task[user_id]["attempts"]
        if att >= 3:
            clear_user_session(message.chat.id, user_id)
            bot.send_message(user_id, "⚠️ **পরপর ৩ বার ভুল 2FA Key দেওয়ায় কাজটি বাতিল হয়েছে। সঠিকভাবে আবার চেষ্টা করুন।**", parse_mode="Markdown")
        else:
            msg = bot.send_message(user_id, f"❌ **ভুল/অকার্যকর 2FA Key!** সঠিক সিক্রেট কি প্রদান করুন। (বাকি {3-att} বার)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_input)
        return

    try:
        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        user_active_task[user_id]["secret_key"] = secret_key
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("✅ একাউন্ট খোলা শেষ (Submit)", callback_data="finish_account"))
        markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
        
        msg_text = f"🔑 <b>আপনার 2FA OTP কোড:</b> <code>{totp_code}</code>\n\nকোডটি দিয়ে ২এফএ অন করে কাজ জমা দিতে নিচের বাটনে চাপুন।"
        bot.send_message(user_id, msg_text, reply_markup=markup, parse_mode="HTML")

    except Exception:
        clear_user_session(message.chat.id, user_id)
        bot.send_message(user_id, "❌ **2FA কোড জেনারেট করা সম্ভব হয়নি!**", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "finish_account")
def finish_account_submission(call):
    user_id = call.from_user.id
    if user_id not in user_active_task or "secret_key" not in user_active_task[user_id]:
        bot.answer_callback_query(call.id, "❌ এই কাজটি ইতিমধ্যেই বাতিল করা হয়েছে!", show_alert=True)
        return

    task_data = user_active_task[user_id]
    ig_user = task_data["username"]

    bot.answer_callback_query(call.id, "🔍 অ্যাকাউন্ট যাচাই করা হচ্ছে...", show_alert=False)

    if not verify_instagram_account_exists(ig_user):
        bot.send_message(user_id, f"⚠️ **কাজ রিজেক্ট হয়েছে!**\n\nবটের দেওয়া ইউজারনেম (`{ig_user}`) দিয়ে কোনো ইনস্টাগ্রাম অ্যাকাউন্ট খুঁজে পাওয়া যায়নি। সঠিক তথ্য দিয়ে জমা দিন।", parse_mode="Markdown")
        return

    clear_user_session(call.message.chat.id, user_id)
    now = int(time.time())
    auto_approve_time = now + (6 * 3600)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at, auto_approve_at) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)",
                   (user_id, task_data["username"], task_data["password"], task_data["secret_key"], now, auto_approve_time))
    conn.commit()
    conn.close()

    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass

    bot.send_message(user_id, "✅ **কাজ অটোমেটিক জমা নেওয়া হয়েছে!**\n\n৬ ঘণ্টার মধ্যে অ্যাকাউন্ট চূড়ান্ত যাচাইকরণ শেষে টাকা ওয়ালেটে যোগ হয়ে যাবে।", parse_mode="Markdown")

# ==================== OTHER BUTTON HANDLERS ====================
@bot.callback_query_handler(func=lambda call: call.data == "click_start")
def process_start_click(call):
    user_id = call.from_user.id
    if check_mandatory_join(user_id):
        bot.send_message(user_id, "🎉 **বটে আপনাকে স্বাগতম!**", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📢 আমাদের চ্যানেলে জয়েন হন 🚀", url=f"https://t.me/{GROUP_CHAT_ID.replace('@','')}"),
            types.InlineKeyboardButton("✅ জয়েন সম্পন্ন করেছি ⚡", callback_data="check_join")
        )
        bot.send_message(user_id, "⚠️ **বট ব্যবহার করতে সাপোর্ট গ্রুপে যুক্ত হোন!**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    user_id = call.from_user.id
    if check_mandatory_join(user_id):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        bot.send_message(user_id, "🎉 **ধন্যবাদ!**", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ আগে সাপোর্ট গ্রুপে জয়েন হন!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_action(call):
    user_id = call.from_user.id
    clear_user_session(call.message.chat.id, user_id)
    bot.send_message(user_id, "❌ **কাজ বাতিল করা হয়েছে!**", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ⚠️")
def handle_notice(message):
    clear_user_session(message.chat.id, message.from_user.id)
    bot.send_message(message.from_user.id, get_setting("notice_msg"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    clear_user_session(message.chat.id, message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
    bot.send_message(message.from_user.id, get_setting("helpline_msg"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎬 আমি নতুন (কাজের ভিডিও) 🎬")
def handle_video_guide(message):
    clear_user_session(message.chat.id, message.from_user.id)
    v_link = get_setting("video_link", "NO_LINK")
    markup = types.InlineKeyboardMarkup()
    if v_link != "NO_LINK": markup.add(types.InlineKeyboardButton("🎥 টিউটোরিয়াল ভিডিও", url=v_link))
    bot.send_message(message.from_user.id, "🎬 **ভিডিও গাইড দেখুন:**", reply_markup=markup, parse_mode="Markdown")

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

# ==================== REFERRAL DASHBOARD ====================
@bot.message_handler(func=lambda msg: msg.text == "👥 রেফার করুন 🎁")
def handle_ref(message):
    user_id = message.from_user.id
    clear_user_session(message.chat.id, user_id)
    
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_custom_text = get_setting("ref_msg")
    ref_bonus_rate = float(get_setting("ref_bonus", "10"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,))
    total_ref = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT u.user_id) 
        FROM users u 
        JOIN tasks t ON u.user_id = t.user_id 
        WHERE u.referred_by = ? AND t.status = 'APPROVED'
    """, (user_id,))
    earned_ref_count = cursor.fetchone()[0]
    total_ref_income = earned_ref_count * ref_bonus_rate
    conn.close()

    text = f"{ref_custom_text}\n\n📌 **প্রতি সফল রেফারে পাবেন:** ৳{ref_bonus_rate:.2f}\n🔗 **রেফার লিংক:** `{ref_link}`\n\n👥 মোট রেফারেল: **{total_ref}** জন\n💰 রেফার ইনকাম: **৳{total_ref_income:.2f}**"
    bot.send_message(user_id, text, parse_mode="Markdown")

# ==================== BALANCE & WITHDRAW SYSTEM ====================
user_withdraw_data = {}

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

@bot.callback_query_handler(func=lambda call: call.data in ["wd_bkash", "wd_nagad"])
def process_withdraw_method(call):
    user_id = call.from_user.id
    method = "বিকাশ" if call.data == "wd_bkash" else "নগদ"
    user_withdraw_data[user_id] = {"method": method}
    msg = bot.send_message(user_id, f"📱 **আপনার {method} নম্বর লিখুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_withdraw_number)

def get_withdraw_number(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data: return
    user_withdraw_data[user_id]["number"] = message.text.strip()
    msg = bot.send_message(user_id, "💵 **উইথড্র অ্যামাউন্ট (কত টাকা) লিখুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    user_id = message.from_user.id
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

        bot.send_message(user_id, "✅ **আপনার উইথড্র রিকোয়েস্টটি প্রসেসিং-এ আছে!**", parse_mode="Markdown")
        
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
        try: bot.send_message(u_id, f"❌ **আপনার উইথড্র রিকোয়েস্টটি বাতিল ও টাকা রিফান্ড করা হয়েছে।**", parse_mode="Markdown")
        except Exception: pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ❌ **REJECTED**", call.message.chat.id, call.message.message_id)

# ==================== ADMIN PANEL ====================
@bot.message_handler(commands=['admin'])
def admin_dashboard(message):
    if not is_admin(message.from_user.id): return
    
    bot_status = get_setting("bot_status", "ON")
    text = f"⚙️ **ADMIN PANEL (InstaXhub Engine)**\n\n🤖 বট স্ট্যাটাস: {'🟢 ON' if bot_status=='ON' else '🔴 OFF'}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="adm_stock"),
        types.InlineKeyboardButton("📥 স্টক ডাউনলোড (Excel)", callback_data="adm_dl_stock"),
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="adm_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_wd"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="adm_broadcast")
    )
    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callback_router(call):
    if not is_admin(call.from_user.id): return
    action = call.data

    if action == "adm_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
        pen = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
        app = cursor.fetchone()[0]
        conn.close()
        bot.send_message(call.from_user.id, f"📊 **স্টক অবস্থা:**\n⏳ পেন্ডিংয়ে আছে: {pen} টি\n✅ রেডি স্টক: {app} টি", parse_mode="Markdown")

    elif action == "adm_dl_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'APPROVED'")
        rows = cursor.fetchall()
        if not rows:
            bot.answer_callback_query(call.id, "স্টকে কোনো কাজ নেই!", show_alert=True)
            conn.close()
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Username", "Password", "Secret Key"])
        t_ids = []
        for r in rows:
            t_ids.append(r[0])
            ws.append([r[1], r[2], r[3]])

        cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(t_ids))})", t_ids)
        conn.commit()
        conn.close()

        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **রেডি স্টক এক্সেল ফাইল ডাউনলোড সম্পন্ন!**")

    elif action == "adm_rate":
        msg = bot.send_message(call.from_user.id, "💰 **কাজের রেট লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "task_rate", "রেট আপডেট হয়েছে!"))

    elif action == "adm_min_wd":
        msg = bot.send_message(call.from_user.id, "💳 **মিনিমাম উইথড্র লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "min_withdraw", "উইথড্র লিমিট আপডেট হয়েছে!"))

    elif action == "adm_ref_bonus":
        msg = bot.send_message(call.from_user.id, "🎁 **রেফার বোনাস লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "ref_bonus", "রেফার বোনাস আপডেট হয়েছে!"))

    elif action == "adm_broadcast":
        msg = bot.send_message(call.from_user.id, "📢 **ব্রডকাস্ট মেসেজটি লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_broadcast)

def set_and_reply(message, key, success_msg):
    set_setting(key, message.text.strip())
    bot.send_message(message.chat.id, f"✅ **{success_msg}**", parse_mode="Markdown")

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
            time.sleep(0.05)
        except Exception: pass
    bot.send_message(message.chat.id, f"✅ **{count} জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে!**", parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 InstaXhub Bot Active...")
    bot.infinity_polling(skip_pending=True)
