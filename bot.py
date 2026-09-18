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
ADMIN_USERNAME = "Adiminsaport"

bot = telebot.TeleBot(TOKEN)

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
        'welcome_msg': '✨ **INSTAXHUB বটে আপনাকে স্বাগতম!**\n\nকাজের সমস্ত আপডেট ও সহায়তার জন্য আমাদের অফিশিয়াল সাপোর্ট গ্রুপে জয়েন থাকা বাধ্যতামূলক।',
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

# ==================== REAL INSTAGRAM CHECK ====================
def check_instagram_username_exists(username):
    """ইনস্টাগ্রাম প্রোফাইল সার্চ ভ্যালিডেশন"""
    url = f"https://www.instagram.com/{username}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=6)
        if response.status_code == 200 and "profilePage_" in response.text:
            return True, "EXISTS"
        elif response.status_code == 404 or "Page Not Found" in response.text:
            return False, "NOT_FOUND"
        else:
            return False, "NOT_FOUND"
    except Exception:
        return False, "NOT_FOUND"

# ==================== 2FA & OTP CHECK ====================
def verify_2fa_and_get_otp(secret_key):
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

def full_admin_dashboard():
    """সম্পূর্ণ এডমিন কন্ট্রোল ড্যাশবোর্ড"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    status = get_setting("bot_status", "ON")
    status_btn = "🔴 বট OFF করুন" if status == "ON" else "🟢 বট ON করুন"
    
    markup.add(
        types.InlineKeyboardButton("🏆 টপ ৫ রেফারার", callback_data="adm_top_ref"),
        types.InlineKeyboardButton("🏆 টপ ৫ ওয়ার্কার", callback_data="adm_top_work"),
        types.InlineKeyboardButton("🔄 রিচেট টপ রেফারার", callback_data="adm_reset_ref"),
        types.InlineKeyboardButton("🔄 রিসেট টপ ওয়ার্কার", callback_data="adm_reset_work"),
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
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                   (user_id, username, int(time.time())))
    conn.commit()
    conn.close()

    text = get_setting("welcome_msg")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপে জয়েন করুন", url=SUPPORT_GROUP_LINK))
    
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")
    bot.send_message(user_id, "নিচের মেনু থেকে আপনার অপশন সিলেক্ট করুন:", reply_markup=main_menu())

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

# --- BALANCE & WITHDRAW SECTION ---
@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স & উইথড্র 💳")
def handle_balance(message):
    user_id = message.from_user.id
    username = message.from_user.username or "নাই"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, pending_balance, total_balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    curr_bal = res[0] if res else 0.0
    pend_bal = res[1] if res else 0.0
    tot_bal = res[2] if res else 0.0
    min_w = get_setting("min_withdraw", "100")
    
    text = f"👤 **ইউজার প্রোফাইল:**\n\n" \
           f"🆔 **আপনার UID:** `{user_id}`\n" \
           f"👤 **ইউজারনেম:** @{username}\n\n" \
           f"💵 **বর্তমান ব্যালেন্স:** ৳{curr_bal:.2f} BDT\n" \
           f"⏳ **পেন্ডিং ব্যালেন্স:** ৳{pend_bal:.2f} BDT\n" \
           f"💰 **মোট ব্যালেন্স:** ৳{tot_bal:.2f} BDT\n\n" \
           f"⚠️ **উইথড্র নিয়ম:** বিকাশ এবং নগদের মাধ্যমে উইথড্র করতে পারবেন। সর্বনিম্ন উইথড্র **৳{min_w} BDT**। ব্যালেন্স ৳{min_w} না হলে উইথড্র রিকোয়েস্ট দেওয়া যাবে না।"
           
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💳 উইথড্র রিকোয়েস্ট দিন", callback_data="req_withdraw"))
    
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "req_withdraw")
def withdraw_callback(call):
    user_id = call.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    curr_bal = res[0] if res else 0.0
    min_w = float(get_setting("min_withdraw", "100"))
    
    if curr_bal < min_w:
        bot.answer_callback_query(call.id, f"❌ আপনার ব্যালেন্স ৳{min_w} টাকার কম! বর্তমানে উইথড্র করতে পারবেন না।", show_alert=True)
    else:
        bot.answer_callback_query(call.id)
        bot.send_message(user_id, "✅ উইথড্র প্রসেস করার জন্য আপনার বিকাশ/নগদ নম্বর এবং পরিমাণ এডমিনকে জানান।")

# --- HELPLINE BUTTON FIX ---
@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    text = "📞 **হেল্পলাইন & সাপোর্ট Centre:**\n\nযেকোনো প্রশ্ন, সমস্যা বা পেমেন্ট সংক্রান্ত বিষয়ে সহায়তার জন্য নিচের বাটনগুলোতে ক্লিক করুন:"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👨‍💻 Admin Support", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"),
        types.InlineKeyboardButton("👥 Group Support", url=SUPPORT_GROUP_LINK)
    )
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

# --- WORKFLOW & REAL INSTAGRAM VALIDATION WITH CANCEL TASK OPTION ---
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass, "attempts": 0}

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন অথবা কাজ করতে না চাইলে বাতিল করুন।"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"),
        types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

# --- CANCEL TASK HANDLER ---
@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_callback(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if user_id in user_active_task:
        del user_active_task[user_id]
        bot.send_message(user_id, "🚫 **আপনার কাজ সফলভাবে বাতিল করা হয়েছে!**\nআপনি চাইলে '💼 কাজ শুরু করুন 🚀' বাটনে চেপে যেকোনো সময় নতুন কাজ নিতে পারেন।", parse_mode="Markdown")
    else:
        bot.send_message(user_id, "⚠️ আপনার কোনো সক্রিয় কাজ চালু নেই।")

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ এই কাজটি বাতিল হয়ে গেছে! নতুন কাজ শুরু করুন।")
        return

    ig_username = user_active_task[user_id]["username"]
    bot.send_message(user_id, "🔍 **ইনস্টাগ্রাম অ্যাকাউন্ট ভেরিফাই করা হচ্ছে...**")

    # আসল ইনস্টাগ্রাম প্রোফাইল চেক
    exists, status = check_instagram_username_exists(ig_username)
    if not exists:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
        
        bot.send_message(
            user_id, 
            f"❌ **অ্যাকাউন্ট খুঁজে পাওয়া যায়নি!**\n\nদয়া করে আগে বটের দেওয়া ইউজারনেম (`{ig_username}`) দিয়ে ইনস্টাগ্রাম অ্যাকাউন্টটি সঠিক নিয়ম মেনে খুলুন, তারপর '🔑 2FA Set' বাটনে চাপ দিন।",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        return

    msg = bot.send_message(user_id, "✅ **অ্যাকাউন্ট পাওয়া গেছে!**\n🔑 **আপনার ইনস্টাগ্রামের সঠিক 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

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
    task_rate = float(get_setting("task_rate", "3"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at) VALUES (?, ?, ?, ?, 'PENDING', ?)",
                   (user_id, task_data["username"], task_data["password"], cleaned_key, int(time.time())))
    
    # পেন্ডিং ব্যালেন্স আপডেট
    cursor.execute("UPDATE users SET pending_balance = pending_balance + ? WHERE user_id = ?", (task_rate, user_id))
    conn.commit()
    conn.close()

    del user_active_task[user_id]
    
    bot.send_message(
        user_id, 
        f"✅ **2FA ভেরিফিকেশন সফল!**\n\n🔢 **জেনারেট হওয়া OTP:** `{otp_code}`\n📌 **স্ট্যাটাস:** কাজ জমা নেওয়া হয়েছে (পেন্ডিং)। বায়ারের রিপোর্ট আপলোডের পর টাকা মেইন ব্যালেন্সে যুক্ত হবে।", 
        parse_mode="Markdown"
    )

# ==================== REPORT & EXCEL PROCESSING ====================
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
        msg = bot.send_message(call.message.chat.id, "📝 **সঠিক (Pass) কাজের টেক্সট লিখে দিন:**\n(যেমন: Pass, Approved, Done)")
        bot.register_next_step_handler(msg, save_pass_rule)

def save_pass_rule(message):
    set_setting("pass_match", message.text.strip().upper())
    mode = get_setting("report_mode")
    if mode == "COLOR":
        msg = bot.send_message(message.chat.id, "🎨 **বাতিল (Fail) কাজের সেল কালার লিখে দিন:**\n(যেমন: WHITE, RED, NO COLOR)")
        bot.register_next_step_handler(msg, save_fail_rule)
    else:
        msg = bot.send_message(message.chat.id, "📝 **বাতিল (Fail) কাজের টেক্সট লিখে দিন:**\n(যেমন: Fail, Rejected, Invalid)")
        bot.register_next_step_handler(msg, save_fail_rule)

def save_fail_rule(message):
    set_setting("fail_match", message.text.strip().upper())
    p_val = get_setting("pass_match")
    f_val = get_setting("fail_match")
    bot.send_message(message.chat.id, f"✅ **ফিল্টার সেটআপ সফল!**\n\n📌 **Pass:** `{p_val}`\n❌ **Fail:** `{f_val}`", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_upload_report")
def ask_report_file(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "📤 **বায়ারের রিপোর্ট ফাইল (.xlsx) সেন্ড করুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_excel_report)

def process_excel_report(message):
    if not message.document or not message.document.file_name.endswith('.xlsx'):
        bot.send_message(message.chat.id, "❌ **দয়া করে একটি সঠিক .xlsx ফাইল পাঠান!**")
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
        username_cell = row[0]
        status_cell = row[1] if len(row) > 1 else row[0]
        
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
                cursor.execute("UPDATE users SET balance = balance + ?, pending_balance = pending_balance - ?, total_balance = total_balance + ? WHERE user_id = ?", 
                               (task_rate, task_rate, task_rate, user_id))
                approved_count += 1
                try:
                    bot.send_message(user_id, f"🎉 **অভিনন্দন!** আপনার ইউজারনেম `{ig_username}` কাজটি সফল হয়েছে এবং ৳{task_rate} টাকা মেইন ব্যালেন্সে যুক্ত হয়েছে।", parse_mode="Markdown")
                except Exception: pass
            
            elif is_rejected:
                cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE ig_username = ?", (ig_username,))
                cursor.execute("UPDATE users SET pending_balance = pending_balance - ? WHERE user_id = ?", (task_rate, user_id))
                rejected_count += 1
                try:
                    bot.send_message(user_id, f"❌ **দুঃখিত!** আপনার ইউজারনেম `{ig_username}` কাজটি বাতিল হয়েছে।", parse_mode="Markdown")
                except Exception: pass

    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id, 
        f"📊 **রিপোর্ট প্রসেসিং সম্পন্ন!**\n\n✅ এপ্রুভড: {approved_count} টি\n❌ রিজেক্টেড: {rejected_count} টি"
    )

bot.infinity_polling()
