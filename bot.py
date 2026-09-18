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
TOKEN = "YOUR_BOT_TOKEN_HERE"  # আপনার বটের টোকেন দিন
ADMIN_IDS = [8422485324]       # আপনার এডমিন আইডি

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
        created_at INTEGER
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    defaults = {
        'task_rate': '3',
        'welcome_msg': '✨ **INSTAXHUB বটে আপনাকে স্বাগতম!**',
        'report_mode': 'COLOR',       # COLOR অথবা TEXT
        'pass_match': 'GREEN',        # পাস ফিল্টার
        'fail_match': 'WHITE'         # রিজেক্ট ফিল্টার
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

# ==================== POINT 3: INSTAGRAM USERNAME CHECK ====================
def check_instagram_username_exists(username):
    """ইনস্টাগ্রামে এই ইউজারনেমে সত্যিই অ্যাকাউন্ট খোলা হয়েছে কি না তা চেক করে"""
    url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            return True, "EXISTS"
        elif response.status_code == 404:
            return False, "NOT_FOUND"
        else:
            return True, "UNKNOWN"  # কোনো রেট লিমিট থাকলে বাইপাস
    except Exception:
        return True, "UNKNOWN"

# ==================== POINT 4: 2FA CHECK & OTP GENERATION ====================
def verify_2fa_and_get_otp(secret_key):
    """২এফএ কি যাচাই করে ৬ ডিজিটের ওটিপি কোড প্রদান করে"""
    try:
        cleaned = secret_key.replace(" ", "").strip().upper()
        if len(cleaned) < 16 or len(cleaned) > 32:
            return False, None
        base64.b32decode(cleaned, casefold=True)
        totp = pyotp.TOTP(cleaned)
        code = totp.now()
        if len(code) == 6 and code.isdigit():
            return True, code
        return False, None
    except Exception:
        return False, None

# ==================== KEYBOARDS ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("💼 কাজ শুরু করুন 🚀"), types.KeyboardButton("💰 ব্যালেন্স & উইথড্র 💳"),
        types.KeyboardButton("📊 কাজের রিপোর্ট 📈"), types.KeyboardButton("📜 কাজের নিয়ম ⚠️"),
        types.KeyboardButton("👥 রেফার করুন 🎁"), types.KeyboardButton("🆘 হেল্পলাইন 📞")
    )
    return markup

def admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 বায়ার রিপোর্ট আপলোড", callback_data="admin_upload_report"),
        types.InlineKeyboardButton("⚙️ রিপোর্ট ফিল্টার সেটআপ", callback_data="admin_config_filter")
    )
    return markup

# ==================== USER WORKFLOW ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                   (user_id, username, int(time.time())))
    conn.commit()
    conn.close()

    bot.send_message(user_id, get_setting("welcome_msg"), reply_markup=main_menu(), parse_mode="Markdown")

@bot.message_handler(commands=['admin'])
def handle_admin_cmd(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🛠 **এডমিন কন্ট্রোল প্যানেল:**", reply_markup=admin_menu(), parse_mode="Markdown")

user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass, "attempts": 0}

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন।"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# --- POINT 3 IN ACTION: CHECK USERNAME BEFORE ASKING 2FA ---
@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ এই কাজটি বাতিল হয়ে গেছে! নতুন কাজ শুরু করুন।")
        return

    ig_username = user_active_task[user_id]["username"]
    bot.send_message(user_id, "🔍 **ইনস্টাগ্রাম অ্যাকাউন্ট ভেরিফাই করা হচ্ছে...**")

    # ইউজারনেম চেক
    exists, status = check_instagram_username_exists(ig_username)
    if not exists and status == "NOT_FOUND":
        bot.send_message(
            user_id, 
            f"❌ **অ্যাকাউন্ট খুঁজে পাওয়া যায়নি!**\n\nদয়া করে আগে বটের দেওয়া ইউজারনেম (`{ig_username}`) দিয়ে ইনস্টাগ্রাম অ্যাকাউন্টটি তৈরি করুন, তারপর '🔑 2FA Set' বাটনে চাপ দিন।",
            parse_mode="Markdown"
        )
        return

    msg = bot.send_message(user_id, "✅ **অ্যাকাউন্ট পাওয়া গেছে!**\n🔑 **আপনার ইনস্টাগ্রামের সঠিক 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

# --- POINT 4 IN ACTION: 2FA CHECK & GENERATE OTP ---
def process_2fa_input(message):
    user_id = message.from_user.id
    if user_id not in user_active_task:
        return

    raw_input = message.text.strip()
    is_valid, otp_code = verify_2fa_and_get_otp(raw_input)

    if not is_valid:
        user_active_task[user_id]["attempts"] += 1
        att = user_active_task[user_id]["attempts"]
        if att >= 3:
            del user_active_task[user_id]
            bot.send_message(user_id, "❌ **পরপর ৩ বার ভুল 2FA Key দেওয়ায় কাজটি বাতিল করা হয়েছে!**")
        else:
            msg = bot.send_message(user_id, f"⚠️ **ভুল 2FA Key!** সঠিক ১৬-৩২ অক্ষরের সিক্রেট কি দিন। (বাকি চেষ্টা: {3-att} বার)")
            bot.register_next_step_handler(msg, process_2fa_input)
        return

    cleaned_key = raw_input.replace(" ", "").upper()
    task_data = user_active_task[user_id]
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at) VALUES (?, ?, ?, ?, 'PENDING', ?)",
                   (user_id, task_data["username"], task_data["password"], cleaned_key, int(time.time())))
    conn.commit()
    conn.close()

    del user_active_task[user_id]
    
    # ২এফএ সফল হলে ওটিপি কোড প্রিন্ট করে ইউজারকে কনফার্মেশন দেওয়া
    bot.send_message(
        user_id, 
        f"✅ **2FA ভেরিফিকেশন সফল!**\n\n🔢 **জেনারেট হওয়া OTP:** `{otp_code}`\n📌 **স্ট্যাটাস:** কাজ জমা নেওয়া হয়েছে। বায়ারের রিপোর্ট আপলোডের পর অ্যাকাউন্টে টাকা যুক্ত হবে।", 
        parse_mode="Markdown"
    )

# ==================== ADMIN FILTER SETUP & REPORT PROCESSING ====================

# --- POINT 1 IN ACTION: COLOR & TEXT FILTER SETUP ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_config_filter")
def admin_config_filter_start(call):
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎨 কালার বেসড (Color)", callback_data="set_mode_COLOR"),
        types.InlineKeyboardButton("📝 টেক্সট বেসড (Text)", callback_data="set_mode_TEXT")
    )
    bot.send_message(call.message.chat.id, "⚙️ **বায়ারের রিপোর্ট চেকিং মোড বেছে নিন:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("set_mode_"))
def set_mode_handler(call):
    mode = call.data.split("_")[2]
    set_setting("report_mode", mode)
    bot.answer_callback_query(call.id)
    
    if mode == "COLOR":
        msg = bot.send_message(call.message.chat.id, "🎨 **সঠিক (Pass) কাজের সেল কালার লিখে দিন:**\n(যেমন: GREEN, RED, BLUE, WHITE)")
        bot.register_next_step_handler(msg, save_pass_rule)
    else:
        msg = bot.send_message(call.message.chat.id, "📝 **সঠিক (Pass) কাজের জন্য যে টেক্সট থাকবে তা লিখে দিন:**\n(যেমন: Pass, Approved, Done, Success)")
        bot.register_next_step_handler(msg, save_pass_rule)

def save_pass_rule(message):
    set_setting("pass_match", message.text.strip().upper())
    mode = get_setting("report_mode")
    if mode == "COLOR":
        msg = bot.send_message(message.chat.id, "🎨 **বাতিল (Fail) কাজের সেল কালার লিখে দিন:**\n(যেমন: WHITE, RED, NO COLOR)")
        bot.register_next_step_handler(msg, save_fail_rule)
    else:
        msg = bot.send_message(message.chat.id, "📝 **বাতিল (Fail) কাজের জন্য যে টেক্সট থাকবে তা লিখে দিন:**\n(যেমন: Fail, Rejected, Invalid, Bad)")
        bot.register_next_step_handler(msg, save_fail_rule)

def save_fail_rule(message):
    set_setting("fail_match", message.text.strip().upper())
    mode = get_setting("report_mode")
    p_val = get_setting("pass_match")
    f_val = get_setting("fail_match")
    
    bot.send_message(message.chat.id, f"✅ **ফিল্টার সেটআপ সফল!**\n\n📌 **মোড:** {mode}\n✅ **Pass কন্ডিশন:** `{p_val}`\n❌ **Fail কন্ডিশন:** `{f_val}`", parse_mode="Markdown")

# --- POINT 2 IN ACTION: AUTO PAYOUT & NOTIFICATIONS ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_upload_report")
def ask_report_file(call):
    bot.answer_callback_query(call.id)
    p_val = get_setting("pass_match")
    f_val = get_setting("fail_match")
    mode = get_setting("report_mode")
    
    msg = bot.send_message(
        call.message.chat.id, 
        f"📤 **বায়ারের রিপোর্ট ফাইল (.xlsx) সেন্ড করুন:**\n\nবর্তমান ফিল্টার:\n🔹 **মোড:** {mode}\n🔹 **Pass:** `{p_val}`\n🔹 **Fail:** `{f_val}`\n\n*(পরিবর্তন করতে চাইলে আগে ফিল্টার সেটআপ করুন)*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_excel_report)

def process_excel_report(message):
    if not message.document or not message.document.file_name.endswith('.xlsx'):
        bot.send_message(message.chat.id, "❌ **দয়া করে একটি সঠিক .xlsx এক্সেল ফাইল পাঠান!**")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    
    file_stream = openpyxl.load_workbook(filename=io.BytesIO(downloaded_file), data_only=True)
    sheet = file_stream.active

    mode = get_setting("report_mode", "COLOR")
    pass_rule = get_setting("pass_match", "GREEN")
    fail_rule = get_setting("fail_match", "WHITE")
    task_rate = float(get_setting("task_rate", "3"))

    conn = get_db()
    cursor = conn.cursor()

    approved_count = 0
    rejected_count = 0

    for row in sheet.iter_rows(min_row=1):
        username_cell = row[0] # কলাম A তে ইউজারনেম
        status_cell = row[1] if len(row) > 1 else row[0] # কলাম B তে টেক্সট স্ট্যাটাস
        
        ig_username = str(username_cell.value).strip() if username_cell.value else None
        if not ig_username:
            continue

        is_approved = False
        is_rejected = False

        if mode == "COLOR":
            fill = username_cell.fill
            color_hex = ""
            if fill and fill.start_color and fill.start_color.rgb:
                color_hex = str(fill.start_color.rgb).upper()

            if pass_rule in ["GREEN", "98FB98", "00FF00"] and ("00FF" in color_hex or "98FB" in color_hex or "34A853" in color_hex):
                is_approved = True
            elif pass_rule in ["RED", "FF0000"] and "FF00" in color_hex:
                is_approved = True
            elif pass_rule in ["WHITE", "NO COLOR", "00000000"] and (color_hex in ["00000000", "FFFFFFFF", ""] or not fill.fill_type):
                is_approved = True

            if fail_rule in ["WHITE", "NO COLOR", "00000000"] and (color_hex in ["00000000", "FFFFFFFF", ""] or not fill.fill_type):
                is_rejected = True
            elif fail_rule in ["RED", "FF0000"] and "FF00" in color_hex:
                is_rejected = True

        elif mode == "TEXT":
            cell_text = str(status_cell.value).strip().upper() if status_cell.value else ""
            if pass_rule in cell_text:
                is_approved = True
            elif fail_rule in cell_text:
                is_rejected = True

        cursor.execute("SELECT user_id FROM tasks WHERE ig_username = ? AND status = 'PENDING'", (ig_username,))
        task = cursor.fetchone()

        if task:
            user_id = task[0]
            if is_approved:
                cursor.execute("UPDATE tasks SET status = 'APPROVED' WHERE ig_username = ?", (ig_username,))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (task_rate, user_id))
                approved_count += 1
                try:
                    bot.send_message(user_id, f"🎉 **অভিনন্দন!** আপনার ইউজারনেম `{ig_username}` কাজটি সফল হয়েছে এবং ৳{task_rate} টাকা অ্যাকাউন্টে যুক্ত হয়েছে।", parse_mode="Markdown")
                except Exception: pass
            
            elif is_rejected:
                cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE ig_username = ?", (ig_username,))
                rejected_count += 1
                try:
                    bot.send_message(user_id, f"❌ **দুঃখিত!** আপনার ইউজারনেম `{ig_username}` কাজটি বায়ার দ্বারা বাতিল হয়েছে।", parse_mode="Markdown")
                except Exception: pass

    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id, 
        f"📊 **রিপোর্ট প্রসেসিং সম্পন্ন!**\n\n✅ এপ্রুভড কাজ: {approved_count} টি\n❌ রিজেক্টেড কাজ: {rejected_count} টি\n\nসংশ্লিষ্ট ইউজারদের অ্যাকাউন্টে টাকা ও নোটিফিকেশন পাঠানো হয়েছে।"
    )

bot.infinity_polling()
