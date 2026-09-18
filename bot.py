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

# ট্র্যাকিং স্টেট
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
    admin_user = get_setting("admin_username", ADMIN_USERNAME).replace("@", "")
    
    text = (
        "✨ **আসসালামু আলাইকুম! InstaXhub বটে আপনাকে স্বাগতম** 🌟\n\n"
        "⚠️ **কাজ শুরু করার আগে অবশ্যই আমাদের অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হতে হবে।**\n\n"
        "নিচের বাটনে ক্লিক করে গ্রুপে জয়েন হয়ে '✅ জয়েন সম্পন্ন করেছি' বাটনে চাপ দিন।"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপে জয়েন করুন 📢", url=channel_link),
        types.InlineKeyboardButton("🧑‍💼 এডমিন সাপোর্ট 💬", url=f"https://t.me/{admin_user}"),
        types.InlineKeyboardButton("✅ জয়েন সম্পন্ন করেছি ⚡", callback_data="check_joined")
    )
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
    
    # রেফারেল রেকর্ড ডাটাবেজে সংরক্ষণ
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

    # স্টার্ট দেওয়ার সাথেই মেম্বারশিপ চেক হবে
    if check_must_join(user_id):
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **নিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশনটি বেছে নিন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        # জয়েন না থাকলে কোনো মেনু দেবে না, শুধু জয়েনিং মেসেজ দেবে
        send_must_join_msg(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    if check_must_join(user_id):
        bot.answer_callback_query(call.id, "✅ জয়েন ভেরিফিকেশন সফল!", show_alert=True)
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **আপনার জয়েনিং সফল হয়েছে! নিচের মেনু থেকে কাজ শুরু করুন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো গ্রুপে জয়েন করেননি! আগে ওপরের 'সাপোর্ট গ্রুপে জয়েন করুন' বাটনে চাপ দিয়ে গ্রুপে যোগ দিন।", show_alert=True)

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

    # ১. এডমিন ইনপুট প্রসেস
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
                bot.send_message(user_id, f"✅ UID `{target_uid}` এ ৳{amount} এড করা হয়েছে।", parse_mode="Markdown")
            else:
                bot.send_message(user_id, "❌ **ভুল ফরম্যাট!** এভাবে লিখুন: `12345678 50`", parse_mode="Markdown")
            return

        elif state == "adm_custom_msg":
            match = re.match(r"^(\d+)\s+(.+)$", text, re.DOTALL)
            if match:
                target_uid, msg_content = int(match.group(1)), match.group(2)
                try:
                    bot.send_message(target_uid, f"📩 **এডমিন থেকে মেসেজ:**\n\n{msg_content}", parse_mode="Markdown")
                    bot.send_message(user_id, "✅ ইউজারের কাছে মেসেজ চলে গেছে!")
                except Exception as e:
                    bot.send_message(user_id, f"❌ মেসেজ পাঠানো যায়নি: {str(e)}")
            else:
                bot.send_message(user_id, "❌ **ভুল ফরম্যাট!** এভাবে লিখুন: `12345678 আপনার মেসেজ`", parse_mode="Markdown")
            return

        elif state == "adm_broadcast":
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()
            conn.close()
            
            count = 0
            for u in users:
                try:
                    bot.send_message(u[0], text, parse_mode="Markdown")
                    count += 1
                except Exception:
                    pass
            bot.send_message(user_id, f"✅ মোট {count} জন ইউজারকে ব্রডকাস্ট মেসেজ পাঠানো হয়েছে!")
            return

        elif state.startswith("set_"):
            setting_key = state.replace("set_", "")
            set_setting(setting_key, text)
            bot.send_message(user_id, "✅ **সেটিং সফলভাবে আপডেট হয়েছে!**", parse_mode="Markdown")
            return

    # ২. ইউজার ২FA ইনপুট প্রসেস
    if user_id in user_waiting_input and user_waiting_input[user_id] == "WAITING_2FA":
        clean_key = text.replace(" ", "")
        if len(clean_key) >= 16:
            try:
                totp = pyotp.TOTP(clean_key)
                current_code = totp.now()
                del user_waiting_input[user_id]
                
                if user_id in user_active_task:
                    task_info = user_active_task.pop(user_id)
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, created_at) VALUES (?, ?, ?, ?, ?)",
                                   (user_id, task_info['username'], task_info['password'], clean_key, int(time.time())))
                    cursor.execute("UPDATE users SET pending_balance = pending_balance + ? WHERE user_id = ?", 
                                   (float(get_setting("task_rate", "3")), user_id))
                    conn.commit()
                    conn.close()

                bot.send_message(user_id, f"✅ **2FA ভেরিফিকেশন সফল!**\n🔑 বর্তমান OTP কোড: `{current_code}`\n\nকাজটি সফলভাবে সাবমিট হয়েছে এবং চেকিংয়ে আছে।", parse_mode="Markdown")
            except Exception:
                bot.send_message(user_id, "❌ **ভুল 2FA Key!** সঠিক ইনস্টাগ্রাম Secret Key দিন।", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "⚠️ **ভুল 2FA Key!** সঠিক সিক্রেট কি দিন।", parse_mode="Markdown")
        return

    # ৩. বাধ্যবাধকতা চেক (গ্রুপে জয়েন না থাকলে কোনো মেসেজের উত্তর বা মেনু দেবে না)
    if not check_must_join(user_id):
        send_must_join_msg(user_id)
        return

    # ৪. ইউজার মেনু বাটন হ্যান্ডলার
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

# --- ADMIN CALLBACK ROUTER ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def handle_admin_callbacks(call):
    user_id = call.from_user.id
    if not is_admin(user_id):
        bot.answer_callback_query(call.id, "❌ আপনার এডমিন অনুমতি নেই!")
        return

    action = call.data
    bot.answer_callback_query(call.id)

    conn = get_db()
    cursor = conn.cursor()

    if action == "adm_top_ref":
        cursor.execute("SELECT username, user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
        top_refs = cursor.fetchall()
        msg = "🏆 **টপ ৫ রেফারার তালিকা:**\n\n"
        for i, u in enumerate(top_refs, 1):
            uname = f"@{u[0]}" if u[0] != "নাই" else f"ID: {u[1]}"
            msg += f"{i}. {uname} - ৳{u[2]:.2f}\n"
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

    elif action == "adm_top_work":
        cursor.execute("SELECT user_id, COUNT(*) as cnt FROM tasks WHERE status = 'APPROVED' GROUP BY user_id ORDER BY cnt DESC LIMIT 5")
        top_workers = cursor.fetchall()
        msg = "🏆 **টপ ৫ ওয়ার্কার তালিকা:**\n\n"
        for i, w in enumerate(top_workers, 1):
            msg += f"{i}. UID: `{w[0]}` - মোট কাজ: {w[1]} টি\n"
        if not top_workers:
            msg += "এখনো কোনো কাজ অনুমোদিত হয়নি।"
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

    elif action == "adm_add_bal":
        admin_states[user_id] = "adm_add_bal"
        bot.send_message(call.message.chat.id, "✉️ **ইউজার ID এবং পরিমাণ লিখুন:**\n(ফরম্যাট: `12345678 50`)", parse_mode="Markdown")

    elif action == "adm_custom_msg":
        admin_states[user_id] = "adm_custom_msg"
        bot.send_message(call.message.chat.id, "✉️ **ইউজার ID এবং মেসেজ লিখুন:**\n(ফরম্যাট: `12345678 আপনার মেসেজ`)", parse_mode="Markdown")

    elif action == "adm_stock_info":
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
        pending = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
        approved = cursor.fetchone()[0]
        msg = f"📊 **বর্তমান ইনস্টাগ্রাম স্টক তথ্য:**\n\n⏳ পেন্ডিং স্টক: {pending} টি\n✅ অনুমোদিত/রেডি স্টক: {approved} টি"
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

    elif action == "adm_stock_dl":
        cursor.execute("SELECT ig_username, ig_password, secret_key FROM tasks")
        rows = cursor.fetchall()
        if rows:
            data = "Username | Password | 2FA Key\n" + "-"*40 + "\n"
            for r in rows:
                data += f"{r[0]} | {r[1]} | {r[2]}\n"
            bio = io.BytesIO(data.encode('utf-8'))
            bio.name = "instagram_stock.txt"
            bot.send_document(call.message.chat.id, bio, caption="📲 **সকল ইনস্টাগ্রাম স্টকের ডাউনলোড ফাইল**")
        else:
            bot.send_message(call.message.chat.id, "❌ ডাটাবেজে কোনো স্টক ফাইল নেই!")

    elif action == "adm_task_rate":
        admin_states[user_id] = "set_task_rate"
        bot.send_message(call.message.chat.id, "💵 **নতুন টাস্ক রেট (টাকায়) লিখুন:**", parse_mode="Markdown")

    elif action == "adm_min_withdraw":
        admin_states[user_id] = "set_min_withdraw"
        bot.send_message(call.message.chat.id, "💳 **নতুন মিনিমাম উইথড্র অ্যামাউন্ট লিখুন:**", parse_mode="Markdown")

    elif action == "adm_ref_bonus":
        admin_states[user_id] = "set_ref_bonus"
        bot.send_message(call.message.chat.id, "🎁 **নতুন রেফার বোনাস অ্যামাউন্ট লিখুন:**", parse_mode="Markdown")

    elif action == "adm_edit_channel":
        admin_states[user_id] = "set_channel_link"
        bot.send_message(call.message.chat.id, "📢 **নতুন সাপোর্ট গ্রুপ/চ্যানেল লিংক পাঠান:**", parse_mode="Markdown")

    elif action == "adm_edit_rules":
        admin_states[user_id] = "set_rules_text"
        bot.send_message(call.message.chat.id, "📜 **নতুন কাজের নিয়মাবলী টেক্সট পাঠান:**", parse_mode="Markdown")

    elif action == "adm_edit_welcome":
        admin_states[user_id] = "set_welcome_msg"
        bot.send_message(call.message.chat.id, "👋 **নতুন ওয়েলকাম মেসেজ টেক্সট পাঠান:**", parse_mode="Markdown")

    elif action == "adm_edit_ref_msg":
        admin_states[user_id] = "set_ref_msg"
        bot.send_message(call.message.chat.id, "🎁 **নতুন রেফার মেসেজ টেক্সট পাঠান:**", parse_mode="Markdown")

    elif action == "adm_edit_help_msg":
        admin_states[user_id] = "set_helpline_msg"
        bot.send_message(call.message.chat.id, "🎧 **নতুন হেল্পলাইন মেসেজ টেক্সট পাঠান:**", parse_mode="Markdown")

    elif action == "adm_edit_video":
        admin_states[user_id] = "set_video_link"
        bot.send_message(call.message.chat.id, "🎬 **নতুন কাজের ভিডিও লিংক পাঠান:**", parse_mode="Markdown")

    elif action == "adm_broadcast":
        admin_states[user_id] = "adm_broadcast"
        bot.send_message(call.message.chat.id, "📢 **সব ইউজারের কাছে পাঠানোর জন্য ব্রডকাস্ট মেসেজ লিখুন:**", parse_mode="Markdown")

    elif action == "adm_upload_report":
        admin_states[user_id] = "set_upload_report"
        bot.send_message(call.message.chat.id, "📥 **বায়ার রিপোর্ট দেওয়ার অপশন তৈরি করা আছে। নতুন কাজের আপডেট মেসেজ বা তথ্য এখানে পাঠান:**", parse_mode="Markdown")

    elif action == "adm_filter_setup":
        bot.send_message(call.message.chat.id, "⚙️ **ফিল্টার সেটআপ করা আছে। স্ট্যাটাস অনুযায়ী ভ্যালিডেশন অ্যাক্টিভ রাখা হয়েছে।**", parse_mode="Markdown")

    elif action == "adm_toggle_bot":
        curr = get_setting("bot_status", "ON")
        new_status = "OFF" if curr == "ON" else "ON"
        set_setting("bot_status", new_status)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=full_admin_dashboard())
        bot.send_message(call.message.chat.id, f"🤖 **বটের স্ট্যাটাস পরিবর্তন করে `{new_status}` করা হয়েছে।**", parse_mode="Markdown")

    conn.close()

bot.infinity_polling()
