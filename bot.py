import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import io
import openpyxl
from threading import Thread

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
SUPPORT_GROUP = "https://t.me/instaXhubsaport"
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
        joined_date INTEGER,
        is_blocked INTEGER DEFAULT 0
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
        'notice_msg': '📜 **কাজের নিয়মাবলী:**\n১. সঠিক তথ্য দিয়ে অ্যাকাউন্ট খুলুন।\n২. সঠিক 2FA Key প্রদান করুন।',
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

def check_mandatory_join(user_id):
    try:
        member = bot.get_chat_member(GROUP_CHAT_ID, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return False

# ==================== BACKGROUND CHECKER ====================
def background_task_checker():
    while True:
        try:
            time.sleep(60)
            conn = get_db()
            cursor = conn.cursor()
            
            six_hours_ago = int(time.time()) - 21600
            cursor.execute("SELECT id, user_id FROM tasks WHERE status = 'PENDING' AND created_at <= ?", (six_hours_ago,))
            pending_tasks = cursor.fetchall()
            
            task_rate = float(get_setting("task_rate", "3"))
            ref_bonus = float(get_setting("ref_bonus", "10"))
            
            for task in pending_tasks:
                t_id, u_id = task
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
                        bot.send_message(ref_by, f"🎉 **আপনার রেফারেল প্রথম কাজ সম্পন্ন করেছে!** আপনি পেয়েছেন **৳{ref_bonus:.2f} বোনাস**!", parse_mode="Markdown")
                    except Exception:
                        pass
                
                try:
                    bot.send_message(u_id, f"🎉 **অভিনন্দন!** আপনার কাজ সফল হয়েছে এবং ব্যালেন্সে **৳{task_rate:.2f}** যোগ হয়েছে।", parse_mode="Markdown")
                except Exception:
                    pass
                    
            conn.commit()
            conn.close()
        except Exception as e:
            print("Checker Error:", e)

Thread(target=background_task_checker, daemon=True).start()

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

# ==================== START & REFERRAL NOTIFICATION ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
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
                ref_bonus_val = get_setting("ref_bonus", "10")
                bot.send_message(
                    referrer_id,
                    f"🎉 **আপনার রেফার লিংকে একজন নতুন ইউজার যুক্ত হয়েছেন!**\n\n📌 ইউজারটি তার প্রথম কাজ সফলভাবে সম্পন্ন করলেই আপনি **৳{ref_bonus_val}** রেফার বোনাস পাবেন!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        conn.commit()
    conn.close()

    welcome_text = get_setting("welcome_msg")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Start 🚀", callback_data="click_start"))
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

# ==================== REFERRAL DASHBOARD ====================
@bot.message_handler(func=lambda msg: msg.text == "👥 রেফার করুন 🎁")
def handle_ref(message):
    user_id = message.from_user.id
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

    text = f"{ref_custom_text}\n\n📌 **প্রতি সফল রেফারে পাবেন:** ৳{ref_bonus_rate:.2f} বোনাস!\n\n🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\n📊 **আপনার রেফারেল সামারি:**\n👥 মোট রেফারেল: **{total_ref}** জন\n💰 রেফার থেকে মোট ইনকাম: **৳{total_ref_income:.2f}**"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📜 রেফার হিস্টোরি", callback_data="ref_history"))
    
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "ref_history")
def show_ref_history(call):
    user_id = call.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, joined_date FROM users WHERE referred_by = ? ORDER BY joined_date DESC LIMIT 20", (user_id,))
    refs = cursor.fetchall()
    
    if not refs:
        bot.answer_callback_query(call.id, "আপনার মাধ্যমে এখনো কেউ যুক্ত হয়নি!", show_alert=True)
        conn.close()
        return

    text = "📜 **আপনার রেফারেল হিস্টোরি (সর্বশেষ ২০ জন):**\n\n"
    for idx, r in enumerate(refs, 1):
        u_name = f"@{r[1]}" if r[1] else f"User {r[0]}"
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (r[0],))
        has_done_job = cursor.fetchone()[0] > 0
        st = "✅ সফল (বোনাস যুক্ত)" if has_done_job else "⏳ কাজ পেন্ডিং"
        text += f"{idx}. {u_name} - {st}\n"
        
    conn.close()
    bot.send_message(user_id, text, parse_mode="Markdown")

# ==================== OTHER BUTTON HANDLERS ====================
@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ⚠️")
def handle_notice(message):
    bot.send_message(message.from_user.id, get_setting("notice_msg"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
    bot.send_message(message.from_user.id, get_setting("helpline_msg"), reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎬 আমি নতুন (কাজের ভিডিও) 🎬")
def handle_video_guide(message):
    v_link = get_setting("video_link", "NO_LINK")
    markup = types.InlineKeyboardMarkup()
    if v_link != "NO_LINK":
        markup.add(types.InlineKeyboardButton("🎥 কাজের ভিডিও টিউটোরিয়াল", url=v_link))
    else:
        markup.add(types.InlineKeyboardButton("🎥 কাজের ভিডিও শীঘ্রই আসছে...", callback_data="none"))
    bot.send_message(message.from_user.id, "🎬 **ভিডিও গাইড:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📊 কাজের রিপোর্ট 📈")
def handle_report(message):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (message.from_user.id,))
    app = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (message.from_user.id,))
    pen = cursor.fetchone()[0]
    conn.close()
    bot.send_message(message.from_user.id, f"📈 **রিপোর্ট:**\n\n✅ সফল: {app} টি\n⏳ পেন্ডিং: {pen} টি", parse_mode="Markdown")

# ==================== WORK SYSTEM ====================
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    
    if get_setting("bot_status", "ON") == "OFF" and not is_admin(user_id):
        bot.send_message(user_id, "⚠️ **বট বর্তমানে রক্ষণাবেক্ষণের (Maintenance) জন্য বন্ধ আছে।**", parse_mode="Markdown")
        return

    if not check_mandatory_join(user_id):
        bot.send_message(user_id, "❌ **কাজ করতে হলে আগে সাপোর্ট গ্রুপে জয়েন করুন!**")
        return

    current_task_rate = get_setting("task_rate", "3")
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass, "attempts": 0}

    text = f"🤖 **নতুন কাজের তথ্য:**\n\n💰 **এই কাজটির জন্য পাবেন:** ৳{current_task_rate}\n👤 **Username:** `{ig_user}`\n🔑 **Password:** `{ig_pass}`\n\nআইডি খুলে 2FA সেটআপ করে নিচের বাটনে ক্লিক করুন।"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"))
    markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
    
    sent_msg = bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")
    user_active_task[user_id]["msg_id"] = sent_msg.message_id

@bot.callback_query_handler(func=lambda call: call.data == "click_start")
def process_start_click(call):
    user_id = call.from_user.id
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 আমাদের চ্যানেলে জয়েন হন 🚀", url=SUPPORT_GROUP),
        types.InlineKeyboardButton("✅ জয়েন সম্পন্ন করেছি ⚡", callback_data="check_join")
    )
    bot.send_message(user_id, "⚠️ **বট ব্যবহার করতে সাপোর্ট গ্রুপে যুক্ত হোন!**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    user_id = call.from_user.id
    if check_mandatory_join(user_id):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception: pass
        bot.send_message(user_id, "🎉 **ধন্যবাদ আমাদের সাথে যুক্ত হওয়ার জন্য!**", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ আগে সাপোর্ট গ্রুপে জয়েন হন!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_action(call):
    user_id = call.from_user.id
    if user_id in user_active_task:
        del user_active_task[user_id]
        
    try:
        bot.edit_message_text(
            "❌ **আপনার কাজটি বাতিল করা হয়েছে!**\n\nনতুন কাজের জন্য আবার '💼 কাজ শুরু করুন 🚀' বাটনে চাপ দিন।",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    except Exception:
        bot.send_message(user_id, "❌ **আপনার কাজ বাতিল করা হয়েছে।**")

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.answer_callback_query(call.id, "এই কাজটির সেশন আউট বা বাতিল হয়ে গেছে!", show_alert=True)
        return
    msg = bot.send_message(user_id, "🔑 **আপনার 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    if user_id not in user_active_task: return

    secret_key = message.text.strip().replace(" ", "").upper()
    try:
        if len(secret_key) < 16: raise ValueError()
        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        
        user_active_task[user_id]["secret_key"] = secret_key
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f"📋 {totp_code}", callback_data=f"copy_{totp_code}"))
        markup.add(types.InlineKeyboardButton("✅ একাউন্ট খোলা শেষ", callback_data="finish_account"))
        bot.send_message(user_id, "অ্যাকাউন্ট খোলা শেষ হলে নিচের বাটনে চাপ দিন:", reply_markup=markup)

    except Exception:
        user_active_task[user_id]["attempts"] += 1
        att = user_active_task[user_id]["attempts"]
        if att >= 3:
            msg_id = user_active_task[user_id].get("msg_id")
            del user_active_task[user_id]
            if msg_id:
                try: bot.delete_message(message.chat.id, msg_id)
                except Exception: pass
            bot.send_message(user_id, "❌ **পরপর ৩ বার ভুল 2FA Key দেওয়ায় কাজটি বাতিল করা হয়েছে!**", parse_mode="Markdown")
        else:
            msg = bot.send_message(user_id, f"❌ **ভুল 2FA Key!** আপনার আর মাত্র {3-att} বার সুযোগ আছে। সঠিক Key টি আবার দিন:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_input)

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def handle_copy_code(call):
    bot.answer_callback_query(call.id, f"কপি হয়েছে: {call.data.split('_')[1]}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "finish_account")
def finish_account_submission(call):
    user_id = call.from_user.id
    if user_id not in user_active_task or "secret_key" not in user_active_task[user_id]: return

    task_data = user_active_task.pop(user_id)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at) VALUES (?, ?, ?, ?, 'PENDING', ?)",
                   (user_id, task_data["username"], task_data["password"], task_data["secret_key"], int(time.time())))
    conn.commit()
    conn.close()

    bot.send_message(user_id, "✅ **কাজ জমা নেওয়া হয়েছে!** ৬ ঘণ্টার মধ্যে চেক করে টাকা যোগ করা হবে।", parse_mode="Markdown")

# ==================== WITHDRAW SYSTEM ====================
user_withdraw_data = {}

@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স & উইথড্র 💳")
def handle_balance(message):
    user_id = message.from_user.id
    
    if get_setting("bot_status", "ON") == "OFF" and not is_admin(user_id):
        bot.send_message(user_id, "⚠️ **বট বর্তমানে রক্ষণাবেক্ষণের (Maintenance) জন্য বন্ধ আছে।**", parse_mode="Markdown")
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    bal = res[0] if res else 0.0
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    pending = cursor.fetchone()[0]
    conn.close()

    min_wd = float(get_setting("min_withdraw", "100"))
    text = f"📊 **আপনার অ্যাকাউন্ট তথ্য:**\n\n💰 **ব্যালেন্স:** ৳{bal:.2f}\n⏳ **পেন্ডিং কাজ:** {pending} টি"

    if bal < min_wd:
        bot.send_message(user_id, f"{text}\n\n❌ সর্বনিম্ন উইথড্র **৳{min_wd:.0f}**", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"), types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(user_id, f"{text}\n\n💳 **মেথড পছন্দ করুন:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["wd_bkash", "wd_nagad"])
def process_withdraw_method(call):
    user_id = call.from_user.id
    method = "বিকাশ" if call.data == "wd_bkash" else "নগদ"
    user_withdraw_data[user_id] = {"method": method}
    msg = bot.send_message(user_id, f"📱 **আপনার {method} নম্বরটি লিখুন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_withdraw_number)

def get_withdraw_number(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data: return
    user_withdraw_data[user_id]["number"] = message.text.strip()
    msg = bot.send_message(user_id, "💵 **কত টাকা উইথড্র করতে চান?**", parse_mode="Markdown")
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
            bot.send_message(user_id, "❌ **ভুল অ্যামাউন্ট!**")
            conn.close()
            return

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

        bot.send_message(user_id, "✅ **আপনার উইথড্র রিকোয়েস্টটি প্রসেসিং-এ আছে।**", parse_mode="Markdown")
        
        admin_msg = f"📩 **নতুন উইথড্র রিকোয়েস্ট:**\n\n👤 ইউজার: `{user_id}`\n💵 পরিমাণ: ৳{amount:.2f}\n💳 মেথড: {wd_info['method']}\n📱 নম্বর: `{wd_info['number']}`"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"wdapp_{user_id}_{amount}"),
                   types.InlineKeyboardButton("❌ Reject", callback_data=f"wdrej_{user_id}_{amount}"))

        for aid in ADMIN_IDS:
            try: bot.send_message(aid, admin_msg, reply_markup=markup, parse_mode="Markdown")
            except Exception: pass
    except Exception:
        bot.send_message(user_id, "❌ **সঠিক নম্বর টাইপ করুন!**")

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
        try: bot.send_message(u_id, f"❌ **আপনার ৳{amt:.2f} টাকার উইথড্র বাতিল ও রিফান্ড করা হয়েছে।**", parse_mode="Markdown")
        except Exception: pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ❌ **REJECTED**", call.message.chat.id, call.message.message_id)

# ==================== ADVANCED ADMIN DASHBOARD ====================
@bot.message_handler(commands=['admin'])
def admin_dashboard(message):
    if not is_admin(message.from_user.id): return
    
    bot_status = get_setting("bot_status", "ON")
    status_icon = "🟢 ON" if bot_status == "ON" else "🔴 OFF (Maintenance)"
    
    text = f"⚙️ **ADMIN CONTROL DASHBOARD** ⚙️\n\n🤖 **বট স্ট্যাটাস:** {status_icon}"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🏆 টপ ৫ রেফারার", callback_data="adm_top_ref"),
        types.InlineKeyboardButton("🏆 টপ ৫ ওয়ার্কার", callback_data="adm_top_work"),
        types.InlineKeyboardButton("🔄 রিসেট টপ রেফারার", callback_data="adm_reset_top_ref"),
        types.InlineKeyboardButton("🔄 রিসেট টপ ওয়ার্কার", callback_data="adm_reset_top_work"),
        types.InlineKeyboardButton("📩 সেন্ড কাস্টম মেসেজ", callback_data="adm_send_custom_msg"),
        types.InlineKeyboardButton("💰 এড ব্যালেন্স", callback_data="adm_add_bonus"),
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="adm_stock"),
        types.InlineKeyboardButton("📥 স্টক ডাউনলোড", callback_data="adm_dl_stock"),
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="adm_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="adm_min_wd"),
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="adm_ref_bonus"),
        types.InlineKeyboardButton(f"🔘 বট {('OFF করুন' if bot_status=='ON' else 'ON করুন')}", callback_data="adm_toggle_bot"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="adm_edit_notice"),
        types.InlineKeyboardButton("👋 ওয়েলকাম মেসেজ", callback_data="adm_edit_welcome"),
        types.InlineKeyboardButton("🎁 রেফার মেসেজ", callback_data="adm_edit_ref_msg"),
        types.InlineKeyboardButton("🎧 হেল্পলাইন মেসেজ", callback_data="adm_edit_help_msg"),
        types.InlineKeyboardButton("🎥 ভিডিও লিংক এডিট", callback_data="adm_edit_video"),
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="adm_broadcast")
    )
    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_callback_router(call):
    if not is_admin(call.from_user.id): return
    action = call.data

    if action == "adm_top_ref":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, ref_count FROM weekly_stats WHERE ref_count > 0 ORDER BY ref_count DESC LIMIT 5")
        top_refs = cursor.fetchall()
        
        text = "🏆 **সেরা ৫ জন টপ রেফারার (চলতি সপ্তাহ):**\n\n"
        if not top_refs:
            text += "কোনো রেফারেল তথ্য পাওয়া যায়নি।"
        else:
            for idx, r in enumerate(top_refs, 1):
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (r[0],))
                u = cursor.fetchone()
                uname = f"@{u[0]}" if u and u[0] else "No Username"
                text += f"{idx}. ID: `{r[0]}` ({uname})\n   👥 রেফার: {r[1]} জন\n\n"
        conn.close()
        bot.send_message(call.from_user.id, text, parse_mode="Markdown")

    elif action == "adm_top_work":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, work_count FROM weekly_stats WHERE work_count > 0 ORDER BY work_count DESC LIMIT 5")
        top_works = cursor.fetchall()
        
        text = "🏆 **সেরা ৫ জন টপ ওয়ার্কার (চলতি সপ্তাহ):**\n\n"
        if not top_works:
            text += "কোনো সম্পন্ন কাজের তথ্য পাওয়া যায়নি।"
        else:
            for idx, w in enumerate(top_works, 1):
                cursor.execute("SELECT username FROM users WHERE user_id = ?", (w[0],))
                u = cursor.fetchone()
                uname = f"@{u[0]}" if u and u[0] else "No Username"
                text += f"{idx}. ID: `{w[0]}` ({uname})\n   ✅ কাজ করেছে: {w[1]} টি\n\n"
        conn.close()
        bot.send_message(call.from_user.id, text, parse_mode="Markdown")

    elif action == "adm_reset_top_ref":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE weekly_stats SET ref_count = 0")
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ টপ রেফারার ডাটা রিসেট সম্পন্ন!", show_alert=True)

    elif action == "adm_reset_top_work":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE weekly_stats SET work_count = 0")
        conn.commit()
        conn.close()
        bot.answer_callback_query(call.id, "✅ টপ ওয়ার্কার ডাটা রিসেট সম্পন্ন!", show_alert=True)

    elif action == "adm_send_custom_msg":
        msg = bot.send_message(call.from_user.id, "👤 **যে ইউজারকে কাস্টম মেসেজ পাঠাতে চান তার User ID টি লিখুন:**")
        bot.register_next_step_handler(msg, process_msg_uid)

    elif action == "adm_add_bonus":
        msg = bot.send_message(call.from_user.id, "👤 **যে ইউজারের ওয়ালেটে টাকা পাঠাতে চান তার User ID টি লিখুন:**")
        bot.register_next_step_handler(msg, process_bonus_uid)

    elif action == "adm_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
        pen = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
        app = cursor.fetchone()[0]
        conn.close()
        bot.send_message(call.from_user.id, f"📊 **স্টক অবস্থা:**\n\n⏳ পেন্ডিং: {pen} টি\n✅ রেডি স্টক: {app} টি")

    elif action == "adm_dl_stock":
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'APPROVED'")
        rows = cursor.fetchall()
        if not rows:
            bot.answer_callback_query(call.id, "স্টকে কোনো আইডি নেই!", show_alert=True)
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
        bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **স্টক এক্সেল ডাউনলোড সম্পন্ন!**")

    elif action == "adm_toggle_bot":
        curr = get_setting("bot_status", "ON")
        new_status = "OFF" if curr == "ON" else "ON"
        set_setting("bot_status", new_status)
        bot.answer_callback_query(call.id, f"বট এখন {new_status}!", show_alert=True)
        admin_dashboard(call.message)

    elif action == "adm_rate":
        msg = bot.send_message(call.from_user.id, "💰 **প্রতি কাজের নতুন রেট (টাকায়) লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "task_rate", "কাজের রেট আপডেট হয়েছে!"))

    elif action == "adm_min_wd":
        msg = bot.send_message(call.from_user.id, "💳 **নতুন সর্বনিম্ন উইথড্র পরিমাণ লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "min_withdraw", "মিনিমাম উইথড্র আপডেট হয়েছে!"))

    elif action == "adm_ref_bonus":
        msg = bot.send_message(call.from_user.id, "🎁 **নতুন রেফার বোনাস পরিমাণ (টাকায়) লিখুন:**")
        bot.register_next_step_handler(msg, process_ref_bonus_update)

    elif action == "adm_edit_notice":
        msg = bot.send_message(call.from_user.id, "📜 **নতুন কাজের নিয়মাবলী টেক্সটটি লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "notice_msg", "কাজের নিয়মাবলী আপডেট হয়েছে!"))

    elif action == "adm_edit_welcome":
        msg = bot.send_message(call.from_user.id, "👋 **নতুন ওয়েলকাম মেসেজ টেক্সটটি লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "welcome_msg", "ওয়েলকাম মেসেজ আপডেট হয়েছে!"))

    elif action == "adm_edit_ref_msg":
        msg = bot.send_message(call.from_user.id, "🎁 **নতুন রেফার মেসেজ টেক্সটটি লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "ref_msg", "রেফার মেসেজ আপডেট হয়েছে!"))

    elif action == "adm_edit_help_msg":
        msg = bot.send_message(call.from_user.id, "🎧 **নতুন হেল্পলাইন টেক্সটটি লিখুন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "helpline_msg", "হেল্পলাইন মেসেজ আপডেট হয়েছে!"))

    elif action == "adm_edit_video":
        msg = bot.send_message(call.from_user.id, "🎥 **নতুন ইউটিউব/টেলিগ্রাম ভিডিও লিংকটি দিন:**")
        bot.register_next_step_handler(msg, lambda m: set_and_reply(m, "video_link", "ভিডিও লিংক আপডেট হয়েছে!"))

    elif action == "adm_broadcast":
        msg = bot.send_message(call.from_user.id, "📢 **সকল ইউজারকে যে মেসেজ পাঠাতে চান তা লিখুন:**")
        bot.register_next_step_handler(msg, process_broadcast)

def process_ref_bonus_update(message):
    val = message.text.strip()
    try:
        float(val)
        set_setting("ref_bonus", val)
        bot.send_message(message.chat.id, f"✅ **রেফার বোনাস সফলভাবে ৳{val} টাকায় আপডেট করা হয়েছে!**", parse_mode="Markdown")
    except Exception:
        bot.send_message(message.chat.id, "❌ **ভুল নম্বর টাইপ করেছেন!**")

def process_msg_uid(message):
    try:
        target_uid = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📝 **User ID `{target_uid}`-এর জন্য আপনার কাস্টম নোটিফিকেশন/মেসেজটি লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: send_custom_msg_final(m, target_uid))
    except Exception:
        bot.send_message(message.chat.id, "❌ **ভুল User ID!**")

def send_custom_msg_final(message, target_uid):
    custom_text = message.text.strip()
    try:
        bot.send_message(target_uid, custom_text, parse_mode="Markdown")
        bot.send_message(message.chat.id, f"✅ **User ID `{target_uid}`-কে মেসেজটি সফলভাবে পাঠানো হয়েছে!**", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ **মেসেজ পাঠানো যায়নি!** ইউজার বট ব্লক করেছে অথবা আইডি ভুল।\nError: {e}")

# ==================== [FIXED] BONUS BALANCE ADD SYSTEM ====================
def process_bonus_uid(message):
    try:
        target_uid = int(message.text.strip())
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (target_uid,))
        user_exists = cursor.fetchone()
        conn.close()

        if not user_exists:
            bot.send_message(message.chat.id, f"❌ **User ID `{target_uid}` টি ডেটাবেজে পাওয়া যায়নি!**\nইউজারকে অবশ্যই একবার বটে `/start` দিতে বলুন।", parse_mode="Markdown")
            return

        msg = bot.send_message(message.chat.id, f"💵 **User ID `{target_uid}`-এর অ্যাকাউন্টে কত টাকা বোনাস যোগ করতে চান লিখুন:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: process_bonus_amount(m, target_uid))
    except Exception:
        bot.send_message(message.chat.id, "❌ **ভুল User ID!** শুধুমাত্র সংখ্যা টাইপ করুন।")

def process_bonus_amount(message, target_uid):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ **টাকার পরিমাণ ০-এর থেকে বেশি হতে হবে!**")
            return

        conn = get_db()
        cursor = conn.cursor()
        
        # ১. নিশ্চিতভাবে ইউজার ফেস করে ব্যালেন্স আপডেট করা
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_uid))
        conn.commit() # স্থায়ীভাবে ডেটাবেজে সেভ

        # ২. নতুন ব্যালেন্স কত হলো তা চেক করা
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (target_uid,))
        new_balance = cursor.fetchone()[0]
        conn.close()

        # ৩. এডমিনকে কনফার্ম করা
        bot.send_message(message.chat.id, f"✅ **User ID `{target_uid}`-এর অ্যাকাউন্টে ৳{amount:.2f} যোগ করা হয়েছে!**\nবর্তমান ব্যালেন্স: ৳{new_balance:.2f}", parse_mode="Markdown")
        
        # ৪. সফল হওয়ার পর ইউজারকে জানানো
        try:
            bot.send_message(target_uid, f"🎉 **এডমিন প্যানেল থেকে আপনার অ্যাকাউন্টে ৳{amount:.2f} বোনাস যোগ করা হয়েছে!**\n💰 আপনার বর্তমান ব্যালেন্স: **৳{new_balance:.2f}**", parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, "⚠️ **ইউজারের ব্যালেন্স এড হয়েছে, তবে ইউজার বট ব্লক রাখায় মেসেজ সেন্ড হয়নি।**")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ **ব্যালেন্স এড করা সম্ভব হয়নি!**\nError: {e}")

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
        except Exception:
            pass
    bot.send_message(message.chat.id, f"✅ **মোট {count} জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে!**")

if __name__ == "__main__":
    print("🤖 Fully Fixed Bot Active...")
    bot.infinity_polling(skip_pending=True)
