import telebot
from telebot import types
import sqlite3
import random
import string
import time
import pyotp
import io
import openpyxl

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
SUPPORT_GROUP = "https://t.me/instaXhubsaport" # সাপোর্ট গ্রুপ লিংক
ADMIN_USERNAME = "@Adiminsaport"               # এডমিন ইউজারনেম
ADMIN_IDS = [8422485324]

GROUP_CHAT_ID = "@instaXhubsaport"             # বাধ্যতামূলক জয়েন চ্যানেল/গ্রুপ

# ==================== BOT INITIALIZATION ====================
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
        ip_address TEXT DEFAULT '',
        first_task_approved INTEGER DEFAULT 0
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
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('video_link', 'NO_LINK')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '100')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notice', '📜 **কাজের নিয়মাবলী:**\n১. বট থেকে দেওয়া ইউনিক আইডি ও পাসওয়ার্ড দিয়ে একাউন্ট খুলুন।\n২. সঠিক 2FA Secret Key দিয়ে জমা দিন।\n\n⚠️ ভুল বা ফেক কাজ জমা দিলে পেমেন্ট বন্ধ করে দেওয়া হবে।')")
    
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

# ==================== MAIN MENU ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("💼 কাজ শুরু করুন 🚀")
    btn2 = types.KeyboardButton("💰 ব্যালেন্স & উইথড্র 💳")
    btn3 = types.KeyboardButton("📊 কাজের রিপোর্ট 📈")
    btn4 = types.KeyboardButton("📜 কাজের নিয়ম ⚠️")
    btn5 = types.KeyboardButton("👥 রেফার করুন 🎁")
    btn6 = types.KeyboardButton("🎬 আমি নতুন (কাজের ভিডিও) 🎬")
    btn7 = types.KeyboardButton("🆘 হেল্পলাইন 📞")
    
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5, btn6)
    markup.add(btn7)
    return markup

# ==================== START COMMAND & JOIN FLOW ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
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
        conn.commit()
    conn.close()

    welcome_text = """✨ **আসসালামু আলাইকুম! INSTAXHUB বটে আপনাকে স্বাগতম** 🌟

💼 আমাদের বটে ইনস্টাগ্রাম একাউন্ট ক্রিয়েট করে আপনি খুব সহজেই প্রতিদিন চমৎকার ইনকাম করতে পারবেন। এটি একটি ১০০% অটোমেটেড ও বিশ্বস্ত প্ল্যাটফর্ম।

👉 **কাজ শুরু করতে নিচের '▶️ Start 🚀' বাটনে ক্লিক করুন!**"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Start 🚀", callback_data="click_start"))
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "click_start")
def process_start_click(call):
    user_id = call.from_user.id
    
    text = "⚠️ **বটটি ব্যবহার করার আগে বাধ্যতামূলক আমাদের অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হতে হবে!** 📣"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 আমাদের চ্যানেলে জয়েন হন 🚀", url=SUPPORT_GROUP),
        types.InlineKeyboardButton("✅ জয়েন সম্পন্ন করেছি ⚡", callback_data="check_join")
    )
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    user_id = call.from_user.id
    if check_mandatory_join(user_id):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(user_id, "🎉 **ধন্যবাদ আমাদের সঙ্গে যুক্ত হওয়ার জন্য এবং এখন আপনি স্বাভাবিকভাবে কাজ করতে পারবেন।** 👇", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ দয়া করে আগে আমাদের সাপোর্ট গ্রুপে জয়েন হন তারপরে কাজ শুরু করুন", show_alert=True)

# ==================== WORK FLOW ====================
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ শুরু করুন 🚀")
def handle_work(message):
    user_id = message.from_user.id
    
    if not check_mandatory_join(user_id):
        bot.send_message(user_id, "❌ **কাজ করতে হলে আগে সাপোর্ট গ্রুপে জয়েন করুন!** /start চাপুন।")
        return

    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {
        "username": ig_user, 
        "password": ig_pass,
        "start_time": time.time()
    }

    text = f"""🤖 **ইউনিক কাজের ডিটেইলস জেনারেট করা হয়েছে:**

👤 **Username:** `{ig_user}`
🔑 **Password:** `{ig_pass}`

⏱ **সময়সীমা:** ১ ঘণ্টা (এর মধ্যে কাজ শেষ করতে হবে)

📌 **নির্দেশিকা:**
১. তথ্যগুলো দিয়ে আইডি খুলে 2FA চালু করুন।
২. 2FA Secret Key সংগ্রহ করে নিচের বাটনে চাপ দিন।"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 Get 2FA Code", callback_data="get_2fa"))
    markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_action(call):
    user_id = call.from_user.id
    if user_id in user_active_task:
        del user_active_task[user_id]
        try:
            bot.edit_message_text("❌ **আপনার কাজ বাতিল করা হয়েছে।** বটের ডাটা ক্লিয়ার করা হলো।", call.message.chat.id, call.message.message_id)
        except Exception:
            bot.send_message(user_id, "❌ **আপনার কাজ বাতিল করা হয়েছে।** বটের ডাটা ক্লিয়ার করা হলো।", parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "কোনো সক্রিয় কাজ নেই বা সেশন আগেই শেষ হয়ে গেছে!", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.answer_callback_query(call.id, "সেশন আউট হয়ে গেছে!", show_alert=True)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(user_id, "❌ সেশন আউট হয়ে গেছে! নতুন কাজ নিতে '💼 কাজ শুরু করুন 🚀' বাটনে চাপ দিন।")
        return
        
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(user_id, "📥 **আপনার 2FA Secret Key-টি পাঠান:**\n*(উদাহরণ: `JBSWY3DPEHPK3PXP`)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ সেশন আউট হয়ে গেছে অথবা আপনার কাজ বাতিল করা হয়েছে। নতুন কাজ নিতে '💼 কাজ শুরু করুন 🚀' চাপুন।")
        return

    # ১ ঘণ্টা = ৩৬০০ সেকেন্ড
    if time.time() - user_active_task[user_id]["start_time"] > 3600:
        del user_active_task[user_id]
        bot.send_message(user_id, "⏳ **সেশন আউট!** ১ ঘণ্টা সময় পার হয়ে যাওয়ায় আপনার কাজটি স্বয়ংক্রয়ভাবে বাতিল করা হয়েছে। নতুন কাজ নিতে আবার চেষ্টা করুন।")
        return

    secret_key = message.text.strip().replace(" ", "").upper()

    try:
        if len(secret_key) < 16:
            raise ValueError("Invalid Key Length")

        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        
        task_data = user_active_task.pop(user_id)
        
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at)
                          VALUES (?, ?, ?, ?, 'PENDING', ?)""",
                       (user_id, task_data["username"], task_data["password"], secret_key, int(time.time())))
        conn.commit()
        conn.close()

        text = f"""✅ **প্রাথমিক চেকিং সফল হয়েছে!**
🔢 **আপনার ইনস্টাগ্রাম কোড:** `{totp_code}`

⏳ **আপনার কাজটি পেন্ডিং এ আছে!** 
দয়া করে ১২ থেকে ২৪ ঘণ্টা অপেক্ষা করুন। এই সময়ের মধ্যে স্বয়ংক্রিয় যাচাই শেষে অ্যাকাউন্টে পেমেন্ট যুক্ত হবে।"""
        bot.send_message(user_id, text, parse_mode="Markdown")

    except Exception:
        bot.send_message(user_id, "❌ **সঠিক 2FA Secret Key প্রদান করুন!**\nদয়া করে ইনস্টাগ্রাম থেকে পাওয়া সঠিক সিক্রেট কি-টি কপি করে দিন। ভুয়া বা মনগড়া লেখা গ্রহণযোগ্য নয়।", parse_mode="Markdown")

# ==================== OTHER BUTTON HANDLERS & WITHDRAW ====================
user_withdraw_data = {}

@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স & উইথড্র 💳")
def handle_balance(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    bal = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    pending_cnt = cursor.fetchone()[0]
    conn.close()

    b_val = bal[0] if bal else 0.0
    text = f"📊 **আপনার অ্যাকাউন্ট তথ্য:**\n\n💰 **বর্তমান ব্যালেন্স:** ৳{b_val:.2f}\n⏳ **পেন্ডিং কাজ:** {pending_cnt} টি"
    
    min_wd = get_setting("min_withdraw", "100")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"),
               types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(user_id, f"{text}\n\n💳 **উইথড্র করতে মেথড পছন্দ করুন (সর্বনিম্ন ৳{min_wd}):**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["wd_bkash", "wd_nagad"])
def process_withdraw_method(call):
    user_id = call.from_user.id
    method = "বিকাশ" if call.data == "wd_bkash" else "নগদ"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    balance = res[0] if res else 0.0
    min_wd = float(get_setting("min_withdraw", "100"))

    if balance < min_wd:
        bot.answer_callback_query(call.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই! সর্বনিম্ন উইথড্র ৳{min_wd:.0f}", show_alert=True)
        return

    user_withdraw_data[user_id] = {"method": method, "balance": balance, "min_wd": min_wd}
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.send_message(user_id, f"📱 **আপনার {method} নম্বরটি লিখে পাঠান:**", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, get_withdraw_number)

def get_withdraw_number(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data:
        bot.send_message(user_id, "❌ উইথড্র সেশন শেষ হয়ে গেছে! আবার চেষ্টা করুন।")
        return
    
    phone_number = message.text.strip()
    user_withdraw_data[user_id]["number"] = phone_number
    
    min_wd = user_withdraw_data[user_id]["min_wd"]
    balance = user_withdraw_data[user_id]["balance"]
    
    bot.send_message(user_id, f"💵 **কত টাকা উইথড্র করতে চান?**\n\n💰 আপনার ব্যালেন্স: ৳{balance:.2f}\n🔻 সর্বনিম্ন উইথড্র: ৳{min_wd:.0f}", parse_mode="Markdown")
    bot.register_next_step_handler(message, process_withdraw_amount)

def process_withdraw_amount(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data:
        bot.send_message(user_id, "❌ উইথড্র সেশন শেষ হয়ে গেছে! আবার চেষ্টা করুন।")
        return
        
    try:
        amount = float(message.text.strip())
        wd_info = user_withdraw_data.pop(user_id)
        
        if amount < wd_info["min_wd"]:
            bot.send_message(user_id, f"❌ **সর্বনিম্ন উইথড্র পরিমাণ ৳{wd_info['min_wd']:.0f} টাকা!**")
            return
            
        if amount > wd_info["balance"]:
            bot.send_message(user_id, "❌ **আপনার অ্যাকাউন্টে এত ব্যালেন্স নেই!**")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

        bot.send_message(user_id, f"✅ **আপনার উইথড্র রিকোয়েস্ট সফলভাবে জমা নেওয়া হয়েছে!**\n\n💳 **মেথড:** {wd_info['method']}\n📱 **নম্বর:** `{wd_info['number']}`\n💵 **পরিমাণ:** ৳{amount:.2f}\n\n⏳ খুব শীঘ্রই এডমিন আপনার পেমেন্টটি প্রসেস করবে।", parse_mode="Markdown")

        # Admin Notification
        admin_msg = f"📩 **নতুন উইথড্র রিকোয়েস্ট!**\n\n👤 **ইউজার ID:** `{user_id}`\n💳 **মেথড:** {wd_info['method']}\n📱 **নম্বর:** `{wd_info['number']}`\n💵 **পরিমাণ:** ৳{amount:.2f}"
        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, admin_msg, parse_mode="Markdown")
            except Exception:
                pass

    except ValueError:
        bot.send_message(user_id, "❌ **দয়া করে সঠিক অংকে টাকার পরিমাণ লিখুন!** (যেমন: 100)")

@bot.message_handler(func=lambda msg: msg.text == "📊 কাজের রিপোর্ট 📈")
def handle_report(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
    app_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'PENDING'", (user_id,))
    pen_cnt = cursor.fetchone()[0]
    conn.close()

    bot.send_message(user_id, f"📈 **আপনার কাজের রিপোর্ট:**\n\n✅ **সফল কাজ:** {app_cnt} টি\n⏳ **পেন্ডিং কাজ:** {pen_cnt} টি", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ⚠️")
def handle_notice(message):
    bot.send_message(message.from_user.id, get_setting("notice"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "👥 রেফার করুন 🎁")
def handle_ref(message):
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    
    text = f"""🎁 **রেফার করে আনলিমিটেড আয় করুন!**

🔗 **আপনার রেফারেল লিংক:**
`{ref_link}`

📌 **রেফার বোনাস নীতি:**
১. আপনার দেওয়া লিংকে কেউ যুক্ত হয়ে **প্রথম কাজ সফলভাবে সম্পন্ন ও এপ্রুভ** করা মাত্রই আপনি পাবেন **৳১০ বোনাস**! 💸
২. ⚠️ **সতর্কতা:** কোনো প্রকার ফেক রেফার, একই ডিভাইসে মাল্টিপল অ্যাকাউন্ট বা দুর্নীতি করলে আপনার রেফার বোনাস আটকে যাবে এবং অটোমেটিক রিজেক্ট মেসেজ যাবে।

সঠিক ইউজার ইনভাইট করুন এবং বোনাস উপভোগ করুন! 🚀"""
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
    
    text = """🎧 **আমাদের সাপোর্ট টিম আপনার সেবায় নিয়োজিত!**

বট ব্যবহারে যেকোনো সমস্যা, পেমেন্ট সংক্রান্ত তথ্য বা প্রশ্নের জন্য সরাসরি আমাদের এডমিনের সঙ্গে যোগাযোগ করতে পারবেন।

👇 **যোগাযোগ করতে নিচের বাটনে চাপ দিন:**"""
    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎬 আমি নতুন (কাজের ভিডিও) 🎬")
def handle_video_guide(message):
    v_link = get_setting("video_link", "NO_LINK")
    markup = types.InlineKeyboardMarkup()
    
    if v_link != "NO_LINK":
        markup.add(types.InlineKeyboardButton("🎥 নতুনদের কাজের ভিডিও টিউটোরিয়াল", url=v_link))
    else:
        markup.add(types.InlineKeyboardButton("🎥 খুব শীঘ্রই কাজের ভিডিও আসতেছে...", callback_data="no_video"))

    bot.send_message(message.from_user.id, "🎬 **সহজে কাজ শিখতে নিচের ভিডিও গাইডটি দেখে নিন:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "no_video")
def callback_no_video(call):
    bot.answer_callback_query(call.id, "🎥 কাজের ভিডিও টিউটোরিয়াল খুব শীঘ্রই আপলোড করা হবে!", show_alert=True)

# ==================== ADMIN PANEL ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📥 Download Stock", callback_data="admin_download_stock"),
        types.InlineKeyboardButton("🎥 Video Link", callback_data="admin_add_video"),
        types.InlineKeyboardButton("📜 Update Notice", callback_data="admin_set_notice"),
        types.InlineKeyboardButton("💰 Min Withdraw", callback_data="admin_set_min_wd")
    )
    bot.send_message(message.from_user.id, "🛠 **ADMIN PANEL CONTROL CENTER**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_video")
def admin_add_video_cb(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "🎥 **নতুন কাজের ভিডিও লিংকটি পাঠাও:**")
    bot.register_next_step_handler(call.message, save_video_link)

def save_video_link(message):
    set_setting("video_link", message.text.strip())
    bot.send_message(message.chat.id, "✅ **ভিডিও লিংক সফলভাবে আপডেট করা হয়েছে!**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_notice")
def admin_set_notice_cb(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "📜 **নতুন কাজের নিয়ম বা নোটিশটি লিখে পাঠাও:**")
    bot.register_next_step_handler(call.message, save_notice)

def save_notice(message):
    set_setting("notice", message.text.strip())
    bot.send_message(message.chat.id, "✅ **নোটিশ সফলভাবে পরিবর্তন করা হয়েছে!**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_min_wd")
def admin_set_min_wd_cb(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "💰 **সর্বনিম্ন উইথড্র পরিমাণ কত টাকা রাখতে চাও? (যেমন: 100):**")
    bot.register_next_step_handler(call.message, save_min_wd)

def save_min_wd(message):
    set_setting("min_withdraw", message.text.strip())
    bot.send_message(message.chat.id, "✅ **সর্বনিম্ন উইথড্র মান সফলভাবে সেভ করা হয়েছে!**")

# ==================== DOWNLOAD STOCK & PROCESS REFERRAL ====================
@bot.callback_query_handler(func=lambda call: call.data == "admin_download_stock")
def admin_download_stock(call):
    if not is_admin(call.from_user.id): return
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'PENDING'")
    rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "❌ বর্তমানে স্টকে কোনো পেন্ডিং কাজ নেই!", show_alert=True)
        conn.close()
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Username", "Password", "Secret Key"])
    
    task_ids_to_delete = []
    
    for r in rows:
        t_id, u_id, ig_un, ig_pw, sec_key = r
        task_ids_to_delete.append(t_id)
        ws.append([ig_un, ig_pw, sec_key])

        cursor.execute("SELECT referred_by, first_task_approved FROM users WHERE user_id = ?", (u_id,))
        u_info = cursor.fetchone()
        
        if u_info:
            ref_by, first_app = u_info
            
            if first_app == 0:
                cursor.execute("UPDATE users SET first_task_approved = 1 WHERE user_id = ?", (u_id,))
                
                if ref_by:
                    is_fake = False
                    if ref_by == u_id:
                        is_fake = True
                    
                    if is_fake:
                        try:
                            fake_msg = "⚠️ **আপনার রেফারটি ফেক হিসেবে চিহ্নিত হয়েছে!**\nযার কারণে আপনি রেফারের বোনাস ৳১০ পাননি। দয়া করে সঠিক রেফার করুন এবং বোনাস জিতে নিন।"
                            bot.send_message(ref_by, fake_msg, parse_mode="Markdown")
                        except Exception:
                            pass
                    else:
                        cursor.execute("UPDATE users SET balance = balance + 10 WHERE user_id = ?", (ref_by,))
                        try:
                            success_msg = "🎉 **আপনার রেফারটি সফলভাবে কাউন্ট করা হয়েছে!**\nআপনার রেফারে যুক্ত ইউজারের প্রথম কাজটি এপ্রুভ হওয়ার জন্য আপনি পেয়ে গেছেন **৳১০ বোনাস**! 💸"
                            bot.send_message(ref_by, success_msg, parse_mode="Markdown")
                        except Exception:
                            pass

    cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(task_ids_to_delete))})", task_ids_to_delete)
    conn.commit()
    conn.close()

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **স্টক এক্সেল ডাউনলোড সফল হয়েছে এবং ডাটাবেজ থেকে ডাটা ক্লিয়ার করা হয়েছে!**")

if __name__ == "__main__":
    print("🤖 Bot is active...")
    bot.infinity_polling(skip_pending=True)
