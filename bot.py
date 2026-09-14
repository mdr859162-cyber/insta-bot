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
SUPPORT_GROUP = "https://t.me/instaXhubsaport"
ADMIN_USERNAME = "@Adiminsaport"
ADMIN_IDS = [8422485324]  # Admin Numeric ID

CHANNEL_USERNAME = "@instaXhubsaport"  # চ্যানেল ইউজারনেম
CHANNEL_LINK = "https://t.me/instaXhubsaport"

bot = telebot.TeleBot(TOKEN)

# ==================== DATABASE SETUP ====================
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0.0,
        pending_balance REAL DEFAULT 0.0,
        referred_by INTEGER,
        referral_count INTEGER DEFAULT 0,
        ip_device TEXT,
        joined_date INTEGER
    )''')
    
    # Tasks Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        ig_username TEXT,
        ig_password TEXT,
        secret_key TEXT,
        status TEXT DEFAULT 'PENDING',
        created_at INTEGER,
        attempts INTEGER DEFAULT 0
    )''')
    
    # Dynamic Settings Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    
    # Default Dynamic Settings Insert
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('video_link', 'NO_LINK')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('min_withdraw', '100')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('notice', '📜 **কাজের নিয়মাবলী:**\n১. বট থেকে দেওয়া ইউনিক ইউজারনেম ও পাসওয়ার্ড দিয়ে ইনস্টাগ্রাম আইডি খুলুন।\n২. সঠিক 2FA Secret Key দিয়ে কোড জেনারেট করে কাজ জমা দিন।\n\n⚠️ **নোটিশ:** ভুল বা ফেক কাজ জমা দিলে পেমেন্ট বন্ধ করে দেওয়া হবে।')")
    
    conn.commit()
    conn.close()

init_db()

# ==================== HELPER FUNCTIONS ====================
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
        return True

# ==================== MAIN MENUS ====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_work = types.KeyboardButton("💼 কাজ")
    btn_balance = types.KeyboardButton("💰 ব্যালেন্স")
    btn_withdraw = types.KeyboardButton("💳 উইথড্র")
    btn_ref = types.KeyboardButton("👥 রেফারেল")
    btn_notice = types.KeyboardButton("📜 কাজের নিয়ম ও নোটিশ")
    btn_support = types.KeyboardButton("🎧 সাপোর্ট ও হেল্পলাইন")
    markup.add(btn_work, btn_balance, btn_withdraw, btn_ref, btn_notice, btn_support)
    return markup

# ==================== START & USER FLOW ====================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    
    args = message.text.split()
    referrer_id = int(args[1]) if len(args) > 1 and args[1].isdigit() and int(args[1]) != user_id else None

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (user_id, username, referred_by, joined_date) VALUES (?, ?, ?, ?)",
                       (user_id, username, referrer_id, int(time.time())))
        conn.commit()
    conn.close()

    if not check_mandatory_join(user_id):
        markup = types.InlineKeyboardMarkup()
        btn_channel = types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_LINK)
        btn_check = types.InlineKeyboardButton("✅ জয়েন সম্পন্ন হয়েছে", callback_data="check_join")
        markup.add(btn_channel)
        markup.add(btn_check)
        bot.send_message(user_id, "👋 **স্বাগতম!**\nকাজ শুরু করার আগে আমাদের অফিশিয়াল চ্যানেলে জয়েন করুন।", reply_markup=markup, parse_mode="Markdown")
        return

    bot.send_message(user_id, "✅ **ধন্যবাদ আমাদের সাথে যুক্ত হওয়ার জন্য!**\nএবার আপনি নিচে দেওয়া মেনু থেকে কাজ শুরু করতে পারেন।", reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    if check_mandatory_join(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.from_user.id, "✅ **ধন্যবাদ আমাদের সাথে যুক্ত হওয়ার জন্য!**\nএবার আপনি নিচে দেওয়া মেনু থেকে কাজ শুরু করতে পারেন।", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি! আগে জয়েন করুন।", show_alert=True)

# ==================== WORK SUBMISSION FLOW ====================
user_active_task = {}

@bot.message_handler(func=lambda msg: msg.text == "💼 কাজ")
def handle_work(message):
    user_id = message.from_user.id
    ig_user, ig_pass = generate_credentials()
    user_active_task[user_id] = {"username": ig_user, "password": ig_pass}

    text = f"""🤖 **আপনার কাজের জন্য ইউনিক ডিটেইলস জেনারেট করা হয়েছে:**

👤 **Username:** `{ig_user}` *(ট্যাপ করলে অটো-কপি)*
🔑 **Password:** `{ig_pass}` *(ট্যাপ করলে অটো-কপি)*

📌 **নির্দেশিকা:**
১. উপরের ইউজারনেম ও পাসওয়ার্ড দিয়ে ইনস্টাগ্রাম আইডি খুলুন।
২. 2FA চালু করুন এবং ২FA Secret Key সংগ্রহ করুন।
৩. নিচে থাকা **🔑 Get 2FA Code** বাটনে চাপ দিন।"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 Get 2FA Code", callback_data="get_2fa"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    bot.send_message(call.from_user.id, "📥 **আপনার ইনস্টাগ্রাম অ্যাকাউন্টের 2FA Secret Key-টি এখানে লিখে পাঠান:**\n*(উদাহরণ: `JBSWY3DPEHPK3PXP`)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    secret_key = message.text.strip().replace(" ", "")

    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ সেশন আউট হয়ে গেছে। আবার '💼 কাজ' বাটনে চাপ দিন।")
        return

    try:
        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        user_active_task[user_id]["secret_key"] = secret_key

        text = f"""✅ **আপনার Secret Key গ্রহণ করা হয়েছে!**

🔢 **আপনার ৬ ডিজিটের ইনস্টাগ্রাম কোড:** `{totp_code}`
*(ইনস্টাগ্রামে অ্যাকাউন্ট ভ্যালিডেশনের জন্য এটি ব্যবহার করুন)*

অ্যাকাউন্ট তৈরি সফলভাবে শেষ হলে নিচের **📤 কাজ জমা দিন** বাটনে চাপ দিন:"""

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 কাজ জমা দিন", callback_data="submit_final_work"))
        bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

    except Exception:
        bot.send_message(user_id, "❌ **ভুল 2FA Secret Key!**\nদয়া করে সঠিক Secret Key পাঠান। আবার '💼 কাজ' বাটনে ক্লিক করুন।")

@bot.callback_query_handler(func=lambda call: call.data == "submit_final_work")
def submit_final_work(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ সেশন শেষ হয়ে গেছে। আবার '💼 কাজ' বাটনে চাপ দিন।")
        return

    task_data = user_active_task.pop(user_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at)
                      VALUES (?, ?, ?, ?, 'PENDING', ?)""",
                   (user_id, task_data["username"], task_data["password"], task_data["secret_key"], int(time.time())))
    conn.commit()
    conn.close()

    bot.send_message(user_id, "🎉 **আপনার কাজটি প্রাথমিক বিচারে সঠিক হয়েছে!**\n১২ থেকে ২৪ ঘণ্টার মধ্যে অটোমেটিক ভ্যালিডেশন শেষে অ্যাকাউন্টে ব্যালেন্স যোগ করে দেওয়া হবে।", parse_mode="Markdown")

# ==================== BALANCE & WITHDRAW ====================
@bot.message_handler(func=lambda msg: msg.text == "💰 ব্যালেন্স")
def handle_balance(message):
    user_id = message.from_user.id
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, pending_balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()

    bal = res[0] if res else 0.0
    pending = res[1] if res else 0.0

    text = f"""📊 **আপনার অ্যাকাউন্ট তথ্য:**

🔹 **মোট আয়:** ৳{bal + pending:.2f}
🔹 **বর্তমান ব্যালেন্স:** ৳{bal:.2f}
🔹 **পেন্ডিং ব্যালেন্স:** ৳{pending:.2f}"""
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "💳 উইথড্র")
def handle_withdraw(message):
    min_wd = get_setting("min_withdraw", "100")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"),
               types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(message.from_user.id, f"💳 **পেমেন্ট নেওয়ার জন্য মাধ্যম নির্বাচন করুন:**\n*(সর্বনিম্ন উইথড্র ৳{min_wd})*", reply_markup=markup, parse_mode="Markdown")

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
        bot.send_message(user_id, f"❌ **আপনার ব্যালেন্স ৳{min_wd}-এর কম থাকায় উইথড্র করতে পারছেন না।**")
        return

    bot.send_message(user_id, f"📱 আপনার **{method}** নাম্বার এবং টাকার পরিমাণ লিখে পাঠান:\n*(উদাহরণ: `01712345678 150`)*", parse_mode="Markdown")
    bot.register_next_step_handler(call.message, lambda msg: process_withdraw_request(msg, method))

def process_withdraw_request(message, method):
    user_id = message.from_user.id
    min_wd = float(get_setting("min_withdraw", "100"))
    try:
        parts = message.text.split()
        num = parts[0]
        amount = float(parts[1])

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = cursor.fetchone()[0]

        if amount < min_wd or amount > bal:
            bot.send_message(user_id, f"❌ **অবৈধ পরিমাণ!** সর্বনিম্ন ৳{min_wd} অথবা আপনার বর্তমান ব্যালেন্স অনুযায়ী চেষ্টা করুন।")
            conn.close()
            return

        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

        bot.send_message(user_id, "⏳ **আপনার উইথড্র রিকোয়েস্ট এডমিনের কাছে পাঠানো হয়েছে।** খুব শীঘ্রই পেমেন্ট সম্পন্ন করা হবে।")

        for admin_id in ADMIN_IDS:
            admin_markup = types.InlineKeyboardMarkup()
            admin_markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"app_wd_{user_id}_{amount}"),
                             types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_wd_{user_id}_{amount}"))
            bot.send_message(admin_id, f"🔔 **নতুন উইথড্র রিকোয়েস্ট!**\n\n👤 **User:** @{message.from_user.username} (`{user_id}`)\n📱 **Method:** {method}\n📞 **Number:** `{num}`\n💰 **Amount:** ৳{amount}", reply_markup=admin_markup, parse_mode="Markdown")
    except Exception:
        bot.send_message(user_id, "❌ **ফরম্যাট সঠিক নয়!** উদাহরণ অনুযায়ী নাম্বার ও অ্যামাউন্ট দিন (যেমন: `01712345678 150`)")

# ==================== REFERRAL & RULES ====================
@bot.message_handler(func=lambda msg: msg.text == "👥 রেফারেল")
def handle_referral(message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    text = f"""🔗 **আপনার রেফারেল লিংক:**
`{ref_link}` *(ট্যাপ করলে অটো-কপি)*

💰 **বোনাস:** প্রতি সফল রেফারে ৳১০।

⚠️ **সতর্কবার্তা:** ফেক রেফার করার চেষ্টা করলে বা স্প্যামিং করলে আপনার রেফার বোনাস বন্ধ হয়ে যেতে পারে।"""
    bot.send_message(user_id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 কাজের নিয়ম ও নোটিশ")
def handle_notice(message):
    notice_text = get_setting("notice")
    bot.send_message(message.from_user.id, notice_text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎧 সাপোর্ট ও হেল্পলাইন")
def handle_support(message):
    v_link = get_setting("video_link", "NO_LINK")

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"),
               types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপ", url=SUPPORT_GROUP))
    
    if v_link != "NO_LINK":
        markup.add(types.InlineKeyboardButton("🎥 নতুনদের জন্য ভিডিও গাইড", url=v_link))
    else:
        markup.add(types.InlineKeyboardButton("🎥 খুব শীঘ্রই ভিডিও আসতেছে...", callback_data="no_video"))

    bot.send_message(message.from_user.id, "🎧 **আমাদের সাপোর্ট সার্ভিসেস:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "no_video")
def callback_no_video(call):
    bot.answer_callback_query(call.id, "🎥 কাজ শেখার টিউটোরিয়াল ভিডিও খুব শীঘ্রই আপলোড করা হবে!", show_alert=True)

# ==================== ADMIN PANEL ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
    pending_tasks = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
    ready_stock = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📥 Download Stock", callback_data="admin_download_stock"),
        types.InlineKeyboardButton("🎥 Video Link", callback_data="admin_add_video"),
        types.InlineKeyboardButton("📜 Update Notice", callback_data="admin_set_notice"),
        types.InlineKeyboardButton("💰 Min Withdraw", callback_data="admin_set_min_wd"),
        types.InlineKeyboardButton("📢 Broadcast Msg", callback_data="admin_broadcast")
    )
    
    text = f"""🛠 **ADVANCED ADMIN DASHBOARD**

👥 **Total Users:** {total_users}
📊 **Pending Tasks:** {pending_tasks}
📦 **Ready Stock:** {ready_stock}
🎥 **Current Video:** {get_setting('video_link')}
💳 **Min Withdraw:** ৳{get_setting('min_withdraw')}"""

    bot.send_message(message.from_user.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_video")
def admin_add_video(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "🎥 **নতুন ভিডিও লিংক লিখে পাঠান:**")
    bot.register_next_step_handler(call.message, lambda m: set_setting("video_link", m.text.strip()) or bot.send_message(m.chat.id, "✅ **ভিডিও লিংক আপডেট সফল!**"))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_notice")
def admin_set_notice(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "📜 **নতুন কাজের নিয়ম ও নোটিশ লিখুন (Markdown Support):**")
    bot.register_next_step_handler(call.message, lambda m: set_setting("notice", m.text.strip()) or bot.send_message(m.chat.id, "✅ **নোটিশ সফলভাবে আপডেট হয়েছে!**"))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_min_wd")
def admin_set_min_wd(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "💳 **সর্বনিম্ন উইথড্র কত টাকা করতে চান? সংখ্যাটি লিখুন:**")
    bot.register_next_step_handler(call.message, lambda m: set_setting("min_withdraw", m.text.strip()) or bot.send_message(m.chat.id, "✅ **সর্বনিম্ন উইথড্র সেট হয়েছে!**"))

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast(call):
    if not is_admin(call.from_user.id): return
    bot.send_message(call.from_user.id, "📢 **সব ইউজারকে যে ব্রডকাস্ট মেসেজ পাঠাতে চান তা লিখে পাঠান:**")
    bot.register_next_step_handler(call.message, process_broadcast)

def process_broadcast(message):
    broadcast_msg = message.text.strip()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    count = 0
    bot.send_message(message.chat.id, "🚀 **মেসেজ পাঠানো শুরু হচ্ছে...**")
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **অফিশিয়াল নোটিশ:**\n\n{broadcast_msg}", parse_mode="Markdown")
            count += 1
            time.sleep(0.05)
        except Exception:
            pass

    bot.send_message(message.chat.id, f"🎉 **মেসেজ সফলভাবে পাঠানো সম্পন্ন! মোট {count} জন ইউজার মেসেজ পেয়েছেন।**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_download_stock")
def admin_download_stock(call):
    if not is_admin(call.from_user.id): return

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'APPROVED'")
    rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "❌ ডাউনলোডের জন্য কোনো স্টক নেই!", show_alert=True)
        conn.close()
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock Data"
    ws.append(["Username", "Password", "2FA Secret Key"])

    task_ids = []
    for r in rows:
        task_ids.append(r[0])
        ws.append([r[1], r[2], r[3]])

    cursor.execute(f"UPDATE tasks SET status = 'DOWNLOADED' WHERE id IN ({','.join(['?']*len(task_ids))})", task_ids)
    conn.commit()
    conn.close()

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    
    bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **স্টক ডাউনলোড সম্পূর্ণ এবং ডাটাবেজ থেকে ক্লিয়ার করা হয়েছে!**")

# Handle Withdraw Approval
@bot.callback_query_handler(func=lambda call: call.data.startswith("app_wd_") or call.data.startswith("rej_wd_"))
def handle_wd_action(call):
    if not is_admin(call.from_user.id): return

    parts = call.data.split("_")
    action = parts[0]
    target_user_id = int(parts[2])
    amount = float(parts[3])

    if action == "app":
        bot.send_message(target_user_id, f"🎉 **অভিনন্দন!** আপনার ৳{amount:.2f} পেমেন্ট সফলভাবে পাঠানো হয়েছে।")
        bot.edit_message_text(f"✅ **Approved Payment of ৳{amount} for user {target_user_id}**", call.message.chat.id, call.message.message_id)
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user_id))
        conn.commit()
        conn.close()
        bot.send_message(target_user_id, f"❌ **আপনার ৳{amount:.2f} পেমেন্ট রিকোয়েস্টটি বাতিল করা হয়েছে** এবং ব্যালেন্স ফেরত দেওয়া হয়েছে।")
        bot.edit_message_text(f"❌ **Rejected Payment of ৳{amount} for user {target_user_id}**", call.message.chat.id, call.message.message_id)

# ==================== BOT RUNNING ====================
if __name__ == "__main__":
    print("🤖 Bot is starting...")
    bot.infinity_polling(skip_pending=True)
