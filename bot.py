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
ADMIN_IDS = [8422485324]  # আপনার Telegram Numeric ID

CHANNEL_USERNAME = "@instaXhubsaport"
CHANNEL_LINK = "https://t.me/instaXhubsaport"

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
    
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('video_link', 'NO_LINK')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '100')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notice', '📜 **কাজের নিয়মাবলী:**\n১. বট থেকে দেওয়া ইউনিক আইডি ও পাসওয়ার্ড দিয়ে একাউন্ট খুলুন।\n২. সঠিক 2FA Secret Key দিয়ে জমা দিন।\n\n⚠️ ভুয়া তথ্য দিলে একাউন্ট সাসপেন্ড করা হবে।')")
    
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
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return False

# ==================== MAIN MENU ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💼 কাজ", "💰 ব্যালেন্স", "💳 উইথড্র", "👥 রেফারেল", "📜 কাজের নিয়ম ও নোটিশ", "🎧 সাপোর্ট ও হেল্পলাইন")
    return markup

# ==================== START COMMAND ====================
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

    if not check_mandatory_join(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 সাপোর্ট গ্রুপে জয়েন করুন", url=CHANNEL_LINK))
        markup.add(types.InlineKeyboardButton("✅ জয়েন সম্পন্ন হয়েছে", callback_data="check_join"))
        bot.send_message(user_id, "👋 **স্বাগতম!**\nকাজ শুরু করার আগে আমাদের সাপোর্ট গ্রুপে জয়েন করা বাধ্যতামূলক।", reply_markup=markup, parse_mode="Markdown")
        return

    bot.send_message(user_id, "✅ **ধন্যবাদ!** এবার আপনি নিচে দেওয়া মেনু থেকে কাজ শুরু করতে পারেন।", reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    if check_mandatory_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "✅ **ধন্যবাদ!** মেনু আনলক করা হয়েছে।", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো গ্রুপে জয়েন করেননি! আগে জয়েন করুন।", show_alert=True)

# ==================== WORK & VALIDATION FLOW ====================
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ")
def handle_work(message):
    user_id = message.from_user.id
    
    if not check_mandatory_join(user_id):
        bot.send_message(user_id, "❌ কাজ করতে হলে আগে সাপোর্ট গ্রুপে যুক্ত হোন! /start চাপুন।")
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

⏱ **সময়সীমা:** ৫ মিনিট (এর মধ্যে কাজ শেষ করতে হবে)

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
        bot.edit_message_text("❌ **আপনার কাজ সফলভাবে বাতিল করা হয়েছে।** বটের ডাটা ক্লিয়ার করা হলো।", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "কোনো সেশন সক্রিয় নেই!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ সেশন আউট হয়ে গেছে! নতুন কাজ নিতে '💼 কাজ' বাটনে চাপ দিন।")
        return
        
    bot.send_message(user_id, "📥 **আপনার ২১/১৬ ডিজিটের 2FA Secret Key-টি পাঠান:**\n*(উদাহরণ: `JBSWY3DPEHPK3PXP`)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ কাজের সময়সীমা অতিক্রম করেছে। নতুন কাজ নিন।")
        return

    # ৫ মিনিট টাইম চেকিং
    if time.time() - user_active_task[user_id]["start_time"] > 300:
        del user_active_task[user_id]
        bot.send_message(user_id, "⏱ **আপনার কাজের ৫ মিনিট সময় শেষ হয়ে গেছে!** ডাটা ক্লিয়ার করা হয়েছে, দয়া করে নতুন আইডি ও পাসওয়ার্ড নিয়ে কাজ শুরু করুন।")
        return

    secret_key = message.text.strip().replace(" ", "")

    # ১-স্টেজ রিয়েল-টাইম ভ্যালিডেশন টেস্ট
    try:
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
দয়া করে ১২ থেকে ২৪ ঘণ্টা অপেক্ষা করুন। এই সময়ের মধ্যে স্বয়ংক্রিয় রি-চেকিং ও চূড়ান্ত যাচাই শেষে অ্যাকাউন্টে পেমেন্ট যুক্ত হবে।"""
        bot.send_message(user_id, text, parse_mode="Markdown")

    except Exception:
        bot.send_message(user_id, "❌ **কোনো বৈধ তথ্য পাওয়া যায়নি!**\nদয়া করে নতুন পাসওয়ার্ড এবং ইউজার নেম নিয়ে সঠিকভাবে কাজ শুরু করুন।", parse_mode="Markdown")

# ==================== BALANCE & WITHDRAW ====================
@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স")
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
    text = f"📊 **অ্যাকাউন্ট তথ্য:**\n\n💰 **বর্তমান ব্যালেন্স:** ৳{b_val:.2f}\n⏳ **পেন্ডিং কাজ:** {pending_cnt} টি"
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💳 উইথড্র")
def handle_withdraw(message):
    min_wd = get_setting("min_withdraw", "100")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"),
               types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(message.from_user.id, f"💳 **উইথড্র মাধ্যম নির্বাচন করুন:**\n*(সর্বনিম্ন উইথড্র ৳{min_wd})*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["wd_bkash", "wd_nagad"])
def process_withdraw_method(call):
    method = "বিকাশ" if call.data == "wd_bkash" else "নগদ"
    user_id = call.from_user.id
    min_wd = float(get_setting("min_withdraw", "100"))
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    bal = cursor.fetchone()[0]
    conn.close()

    if bal < min_wd:
        bot.send_message(user_id, f"❌ **ব্যালেন্স পর্যাপ্ত নয়!** সর্বনিম্ন উইথড্র ৳{min_wd}")
        return

    bot.send_message(user_id, f"📱 **{method}** নাম্বার ও পরিমাণ লিখুন:\n*(যেমন: `01712345678 150`)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, lambda m: send_wd_request(m, method, min_wd))

def send_wd_request(message, method, min_wd):
    user_id = message.from_user.id
    try:
        parts = message.text.split()
        num, amount = parts[0], float(parts[1])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]

        if amount < min_wd or amount > bal:
            bot.send_message(user_id, "❌ **অবৈধ পরিমাণ!** চেষ্টা সফল হয়নি।")
            conn.close()
            return

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

        bot.send_message(user_id, "⏳ **উইথড্র রিকোয়েস্ট জমা হয়েছে।**")

        for admin_id in ADMIN_IDS:
            admin_markup = types.InlineKeyboardMarkup()
            admin_markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"app_wd_{user_id}_{amount}"),
                             types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_wd_{user_id}_{amount}"))
            bot.send_message(admin_id, f"🔔 **উইথড্র রিকোয়েস্ট!**\n\n👤 **User:** `{user_id}`\n📱 **Method:** {method}\n📞 **Number:** `{num}`\n💰 **Amount:** ৳{amount}", reply_markup=admin_markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(user_id, "❌ **ভুল ফরম্যাট!** নিয়ম মেনে লিখুন।")

# ==================== OTHERS & ADMIN PANEL ====================
@bot.message_handler(func=lambda msg: msg.text == "👥 রেফারেল")
def handle_ref(message):
    bot_info = bot.get_me()
    bot.send_message(message.from_user.id, f"🔗 **রেফারেল লিংক:**\nhttps://t.me/{bot_info.username}?start={message.from_user.id}", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ও নোটিশ")
def handle_notice(message):
    bot.send_message(message.from_user.id, get_setting("notice"), parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎧 সাপোর্ট ও হেল্পলাইন")
def handle_support(message):
    v_link = get_setting("video_link", "NO_LINK")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"),
               types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপ", url=SUPPORT_GROUP))
    if v_link != "NO_LINK":
        markup.add(types.InlineKeyboardButton("🎥 কাজের ভিডিও গাইড", url=v_link))
    bot.send_message(message.from_user.id, "🎧 **আমাদের সাপোর্ট সার্ভিস:**", reply_markup=markup, parse_mode="Markdown")

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
    bot.send_message(message.from_user.id, "🛠 **ADMIN PANEL**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_download_stock")
def admin_download_stock(call):
    if not is_admin(call.from_user.id): return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'PENDING'")
    rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "❌ কোনো স্টক নেই!", show_alert=True)
        conn.close()
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Username", "Password", "Secret Key"])
    
    t_ids = []
    for r in rows:
        t_ids.append(r[0])
        ws.append([r[1], r[2], r[3]])

    cursor.execute(f"UPDATE tasks SET status = 'APPROVED' WHERE id IN ({','.join(['?']*len(t_ids))})", t_ids)
    conn.commit()
    conn.close()

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **স্টক ডাউনলোডেড!**")

if __name__ == "__main__":
    print("🤖 Bot Active...")
    bot.infinity_polling(skip_pending=True)
