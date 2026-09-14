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
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('task_rate', '3')")
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

# ==================== BACKGROUND 6-HOUR CHECKER ====================
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
            
            for task in pending_tasks:
                t_id, u_id = task
                cursor.execute("UPDATE tasks SET status = 'APPROVED' WHERE id = ?", (t_id,))
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (task_rate, u_id))
                
                cursor.execute("SELECT referred_by, first_task_approved FROM users WHERE user_id = ?", (u_id,))
                u_info = cursor.fetchone()
                if u_info and u_info[1] == 0:
                    cursor.execute("UPDATE users SET first_task_approved = 1 WHERE user_id = ?", (u_id,))
                    ref_by = u_info[0]
                    if ref_by and ref_by != u_id:
                        cursor.execute("UPDATE users SET balance = balance + 10 WHERE user_id = ?", (ref_by,))
                        try:
                            bot.send_message(ref_by, "🎉 **আপনার রেফারটি সফলভাবে সম্পন্ন হয়েছে!** আপনি পেয়ে গেছেন **৳১০ বোনাস**! 💸", parse_mode="Markdown")
                        except Exception:
                            pass
                
                try:
                    bot.send_message(u_id, f"🎉 **অভিনন্দন!** আপনার একটি কাজের ৬ ঘণ্টার ভ্যালিডেশন সফল হয়েছে এবং আপনার ব্যালেন্সে **৳{task_rate:.2f}** যুক্ত করা হয়েছে।", parse_mode="Markdown")
                except Exception:
                    pass
                    
            conn.commit()
            conn.close()
        except Exception as e:
            print("Checker Error:", e)

Thread(target=background_task_checker, daemon=True).start()

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

💼 আমাদের বটে ইনস্টাগ্রাম একাউন্ট ক্রিয়েট করে আপনি খুব সহজেই প্রতিদিন চমৎকার ইনকাম করতে পারবেন।

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
        bot.send_message(user_id, "🎉 **ধন্যবাদ আমাদের সঙ্গে যুক্ত হওয়ার জন্য!** 👇", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ দয়া করে আগে আমাদের সাপোর্ট গ্রুপে জয়েন হন", show_alert=True)

# ==================== WORK FLOW & 3-ATTEMPTS 2FA FIX ====================
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
        "start_time": time.time(),
        "attempts": 0  # 2FA ভুল হওয়ার কাউন্টার
    }

    text = f"""🤖 **ইউনিক কাজের ডিটেইলস জেনারেট করা হয়েছে:**

👤 **Username:** `{ig_user}`
🔑 **Password:** `{ig_pass}`

📌 **নির্দেশিকা:**
১. তথ্যগুলো দিয়ে আইডি খুলে 2FA চালু করুন।
২. 2FA Secret Key সংগ্রহ করে নিচের বাটনে চাপ দিন।"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔑 2FA Set", callback_data="get_2fa"))
    markup.add(types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task"))
    bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "cancel_task")
def cancel_task_action(call):
    user_id = call.from_user.id
    if user_id in user_active_task:
        del user_active_task[user_id]
        try:
            bot.edit_message_text("❌ **আপনার কাজ বাতিল করা হয়েছে।**", call.message.chat.id, call.message.message_id)
        except Exception:
            bot.send_message(user_id, "❌ **আপনার কাজ বাতিল করা হয়েছে।**", parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "কোনো সক্রিয় কাজ নেই!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "get_2fa")
def ask_2fa_key(call):
    user_id = call.from_user.id
    if user_id not in user_active_task:
        bot.answer_callback_query(call.id, "সেশন আউট হয়ে গেছে!", show_alert=True)
        return
        
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    msg = bot.send_message(user_id, "🔑 **আপনার 2FA Key টি দিন:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_2fa_input)

def process_2fa_input(message):
    user_id = message.from_user.id
    if user_id not in user_active_task:
        bot.send_message(user_id, "❌ সেশন আউট হয়ে গেছে! নতুন কাজ নিতে '💼 কাজ শুরু করুন 🚀' চাপুন।")
        return

    secret_key = message.text.strip().replace(" ", "").upper()

    try:
        if len(secret_key) < 16:
            raise ValueError("Invalid Key Length")

        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        
        # সফল হলে অ্যাটেম্পট কাউন্টার রিসেট করে কি সেভ হবে
        user_active_task[user_id]["secret_key"] = secret_key

        text = f"""অ্যাকাউন্ট খোলা শেষ হলে নিচের বাটনে চাপ দিন:

নিচের বাটনে চাপ দিয়ে কোডটি কপি করুন:"""
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f"📋 {totp_code}", callback_data=f"copy_{totp_code}"))
        markup.add(types.InlineKeyboardButton("✅ একাউন্ট খোলা শেষ", callback_data="finish_account"))

        bot.send_message(user_id, text, reply_markup=markup)

    except Exception:
        # ৩ বার ভুল কি দেওয়ার লজিক
        user_active_task[user_id]["attempts"] += 1
        current_attempts = user_active_task[user_id]["attempts"]
        
        if current_attempts >= 3:
            # ৩ বার ভুল দিলে কাজ বাতিল করে দেওয়া হবে
            del user_active_task[user_id]
            bot.send_message(user_id, "❌ **আপনি পরপর ৩ বার ভুল 2FA Secret Key প্রদান করেছেন।**\n\nআপনার এই কাজটি বাতিল করা হয়েছে। নতুন করে কাজ শুরু করতে '💼 কাজ শুরু করুন 🚀' চাপুন।", parse_mode="Markdown")
        else:
            remaining = 3 - current_attempts
            msg = bot.send_message(user_id, f"❌ **সঠিক 2FA Secret Key প্রদান করুন!**\n⚠️ আপনার ভুল প্রচেষ্টা: {current_attempts}/৩ বার। (আর মাত্র {remaining} বার সুযোগ আছে)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_input)

@bot.callback_query_handler(func=lambda call: call.data.startswith("copy_"))
def handle_copy_code(call):
    code = call.data.split("_")[1]
    bot.answer_callback_query(call.id, f"কোডটি কপি করা হয়েছে: {code}", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "finish_account")
def finish_account_submission(call):
    user_id = call.from_user.id
    if user_id not in user_active_task or "secret_key" not in user_active_task[user_id]:
        bot.answer_callback_query(call.id, "সেশন শেষ হয়ে গেছে!", show_alert=True)
        return

    task_data = user_active_task.pop(user_id)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at)
                      VALUES (?, ?, ?, ?, 'PENDING', ?)""",
                   (user_id, task_data["username"], task_data["password"], task_data["secret_key"], int(time.time())))
    conn.commit()
    conn.close()

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    success_msg = """✅ **Rcv (কাজ জমা নেওয়া হয়েছে)**

এটার টাকা পরবর্তী **৬ ঘণ্টার মধ্যে** চেক হয়ে আপনার অ্যাকাউন্টে যোগ হবে ইনশাআল্লাহ।

আরও কাজ করতে চাইলে এখনই আবার কাজ শুরু করতে পারেন। 🚀"""
    bot.send_message(user_id, success_msg, parse_mode="Markdown")

# ==================== ADVANCED WITHDRAW SYSTEM & FIX ====================
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
    min_wd = float(get_setting("min_withdraw", "100"))
    
    text = f"📊 **আপনার অ্যাকাউন্ট তথ্য:**\n\n💰 **বর্তমান ব্যালেন্স:** ৳{b_val:.2f}\n⏳ **পেন্ডিং কাজ:** {pending_cnt} টি"
    
    if b_val < min_wd:
        bot.send_message(user_id, f"{text}\n\n❌ **আপনার পর্যাপ্ত ব্যালেন্স নেই!** উইথড্র করতে কমপক্ষে **৳{min_wd:.0f}** প্রয়োজন।", parse_mode="Markdown")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("বিকাশ", callback_data="wd_bkash"),
               types.InlineKeyboardButton("নগদ", callback_data="wd_nagad"))
    bot.send_message(user_id, f"{text}\n\n💳 **উইথড্র করতে মেথড পছন্দ করুন (সর্বনিম্ন ৳{min_wd:.0f}):**", reply_markup=markup, parse_mode="Markdown")

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

    msg = bot.send_message(user_id, f"📱 **আপনার সঠিক {method} নম্বরটি লিখে পাঠান:**", parse_mode="Markdown")
    bot.register_next_step_handler(msg, get_withdraw_number)

def get_withdraw_number(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data:
        bot.send_message(user_id, "❌ উইথড্র সেশন শেষ হয়ে গেছে!")
        return
    
    phone_number = message.text.strip()
    user_withdraw_data[user_id]["number"] = phone_number
    
    min_wd = user_withdraw_data[user_id]["min_wd"]
    balance = user_withdraw_data[user_id]["balance"]
    
    msg = bot.send_message(user_id, f"💵 **কত টাকা উইথড্র করতে চান?**\n\n💰 আপনার ব্যালেন্স: ৳{balance:.2f}\n🔻 সর্বনিম্ন উইথড্র: ৳{min_wd:.0f}", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    user_id = message.from_user.id
    if user_id not in user_withdraw_data:
        bot.send_message(user_id, "❌ উইথড্র সেশন শেষ হয়ে গেছে!")
        return
        
    try:
        amount = float(message.text.strip())
        wd_info = user_withdraw_data.pop(user_id)
        
        min_wd = wd_info["min_wd"]
        balance = wd_info["balance"]
        
        if amount < min_wd or amount > balance:
            bot.send_message(user_id, f"❌ **সঠিক টাকার পরিমাণ টাইপ করুন!** (সর্বনিম্ন ৳{min_wd:.0f} এবং সর্বোচ্চ আপনার ব্যালেন্সের সমান হতে হবে)")
            return

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = 'APPROVED'", (user_id,))
        app_cnt = cursor.fetchone()[0]
        conn.close()

        # ইউজারের কাছে সুন্দর রেসপন্স নোটিশ
        bot.send_message(user_id, f"✅ **আপনার উইথড্র রিকোয়েস্টটি সফলভাবে জমা হয়েছে!**\n\n💳 **মেথড:** {wd_info['method']}\n📱 **নম্বর:** `{wd_info['number']}`\n💵 **পরিমাণ:** ৳{amount:.2f}\n\n⏳ **স্ট্যাটাস:** আপনার উইথড্রটি প্রসেসিং-এ আছে। এডমিন চেক করে শীঘ্রই পেমেন্ট সম্পন্ন করবেন ইনশাআল্লাহ।", parse_mode="Markdown")

        # এডমিন প্যানেলে সঠিক নোটিফিকেশন পাঠানোর ব্যবস্থা
        admin_msg = f"""📩 **নতুন উইথড্র রিকোয়েস্ট এসেছে!**

👤 **ইউজার নাম:** {message.from_user.first_name} (`{user_id}`)
📊 **মোট সফল কাজ:** {app_cnt} টি
💰 **উইথড্রর আগের ব্যালেন্স:** ৳{balance:.2f}
💵 **উইথড্র করার পরিমাণ:** ৳{amount:.2f}
💳 **পেমেন্ট মেথড:** {wd_info['method']}
📱 **নম্বর:** `{wd_info['number']}`"""

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"wdapp_{user_id}_{amount}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"wdrej_{user_id}_{amount}")
        )

        for admin_id in ADMIN_IDS:
            try:
                bot.send_message(admin_id, admin_msg, reply_markup=markup, parse_mode="Markdown")
            except Exception:
                pass

    except ValueError:
        bot.send_message(user_id, "❌ **দয়া করে সঠিক সংখ্যায় টাকার পরিমাণ লিখুন!**")

@bot.callback_query_handler(func=lambda call: call.data.startswith("wdapp_") or call.data.startswith("wdrej_"))
def handle_withdraw_approval(call):
    if not is_admin(call.from_user.id): return
    
    action, u_id, amt = call.data.split("_")
    u_id = int(u_id)
    amt = float(amt)
    
    if action == "wdapp":
        try:
            bot.send_message(u_id, f"🎉 **আপনার ৳{amt:.2f} টাকার উইথড্র রিকোয়েস্টটি সফলভাবে এপ্রুভ করা হয়েছে এবং পেমেন্ট পাঠিয়ে দেওয়া হয়েছে!**", parse_mode="Markdown")
        except Exception:
            pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ✅ **APPROVED**", call.message.chat.id, call.message.message_id)
    else:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, u_id))
        conn.commit()
        conn.close()
        try:
            bot.send_message(u_id, f"❌ **আপনার ৳{amt:.2f} টাকার উইথড্র রিকোয়েস্টটি বাতিল করা হয়েছে এবং টাকা আপনার মূল ব্যালেন্সে ফেরত দেওয়া হয়েছে।**", parse_mode="Markdown")
        except Exception:
            pass
        bot.edit_message_text(call.message.text + "\n\nSTATUS: ❌ **REJECTED & REFUNDED**", call.message.chat.id, call.message.message_id)

# ==================== OTHER BOT BUTTONS ====================
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
    text = f"🎁 **রেফার করে ইনকাম করুন!**\n\n🔗 **আপনার রেফার লিংক:**\n`{ref_link}`\n\nসফল রেফারে পাবেন **৳১০ বোনাস**!"
    bot.send_message(message.from_user.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🆘 হেল্পলাইন 📞")
def handle_helpline(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=f"https://t.me/{ADMIN_USERNAME.replace('@','')}"))
    bot.send_message(message.from_user.id, "🎧 **যোগাযোগ করতে নিচের বাটনে চাপ দিন:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "🎬 আমি নতুন (কাজের ভিডিও) 🎬")
def handle_video_guide(message):
    v_link = get_setting("video_link", "NO_LINK")
    markup = types.InlineKeyboardMarkup()
    if v_link != "NO_LINK":
        markup.add(types.InlineKeyboardButton("🎥 নতুনদের কাজের ভিডিও টিউটোরিয়াল", url=v_link))
    else:
        markup.add(types.InlineKeyboardButton("🎥 খুব শীঘ্রই কাজের ভিডিও আসতেছে...", callback_data="no_video"))
    bot.send_message(message.from_user.id, "🎬 **ভিডিও গাইড দেখুন:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "no_video")
def callback_no_video(call):
    bot.answer_callback_query(call.id, "🎥 কাজের ভিডিও টিউটোরিয়াল শীঘ্রই আপলোড করা হবে!", show_alert=True)

# ==================== ADMIN PANEL ====================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id): return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 Stock Info", callback_data="admin_stock_info"),
        types.InlineKeyboardButton("📥 Download Stock", callback_data="admin_download_stock"),
        types.InlineKeyboardButton("💰 Per Task Rate", callback_data="admin_set_task_rate"),
        types.InlineKeyboardButton("🎥 Video Link", callback_data="admin_add_video"),
        types.InlineKeyboardButton("📜 Update Notice", callback_data="admin_set_notice"),
        types.InlineKeyboardButton("💳 Min Withdraw", callback_data="admin_set_min_wd")
    )
    bot.send_message(message.from_user.id, "🛠 **ADMIN PANEL CONTROL CENTER**", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stock_info")
def admin_stock_info_cb(call):
    if not is_admin(call.from_user.id): return
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'PENDING'")
    pending_cnt = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'APPROVED'")
    approved_cnt = cursor.fetchone()[0]
    conn.close()
    
    text = f"📊 **স্টক সংক্রান্ত তথ্য:**\n\n⏳ **পেন্ডিং আইডি (৬ ঘণ্টার কম):** {pending_cnt} টি\n✅ **স্টকে জমা আইডি (ডাউনলোডের জন্য প্রস্তুত):** {approved_cnt} টি"
    bot.send_message(call.from_user.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_task_rate")
def admin_set_task_rate_cb(call):
    if not is_admin(call.from_user.id): return
    curr_rate = get_setting("task_rate", "3")
    msg = bot.send_message(call.from_user.id, f"💰 **বর্তমান কাজের রেট ৳{curr_rate}। নতুন কাজের রেট কত দিতে চান? (যেমন: 5, 7, 10):**")
    bot.register_next_step_handler(msg, save_task_rate)

def save_task_rate(message):
    rate = message.text.strip()
    set_setting("task_rate", rate)
    bot.send_message(message.chat.id, f"✅ **প্রতি কাজের রেট ৳{rate} সফলভাবে সেভ করা হয়েছে!**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_download_stock")
def admin_download_stock(call):
    if not is_admin(call.from_user.id): return
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, ig_username, ig_password, secret_key FROM tasks WHERE status = 'APPROVED'")
    rows = cursor.fetchall()

    if not rows:
        bot.answer_callback_query(call.id, "❌ ডাউনলোড করার মতো কোনো Approved কাজ স্টকে নেই!", show_alert=True)
        conn.close()
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Username", "Password", "Secret Key"])
    
    task_ids = []
    for r in rows:
        t_id, ig_un, ig_pw, sec_key = r
        task_ids.append(t_id)
        ws.append([ig_un, ig_pw, sec_key])

    cursor.execute(f"DELETE FROM tasks WHERE id IN ({','.join(['?']*len(task_ids))})", task_ids)
    conn.commit()
    conn.close()

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    bot.send_document(call.from_user.id, bio, visible_file_name="Instagram_Stock.xlsx", caption="✅ **স্টক এক্সেল ফাইল ডাউনলোড সফল হয়েছে!**")

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_video")
def admin_add_video_cb(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.from_user.id, "🎥 **নতুন কাজের ভিডিও লিংকটি পাঠাও:**")
    bot.register_next_step_handler(msg, lambda m: set_setting("video_link", m.text.strip()))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_notice")
def admin_set_notice_cb(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.from_user.id, "📜 **নতুন নোটিশটি লিখে পাঠাও:**")
    bot.register_next_step_handler(msg, lambda m: set_setting("notice", m.text.strip()))

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_min_wd")
def admin_set_min_wd_cb(call):
    if not is_admin(call.from_user.id): return
    msg = bot.send_message(call.from_user.id, "💰 **সর্বনিম্ন উইথড্র পরিমাণ কত রাখতে চান?:**")
    bot.register_next_step_handler(msg, lambda m: set_setting("min_withdraw", m.text.strip()))

if __name__ == "__main__":
    print("🤖 Bot is active and running...")
    bot.infinity_polling(skip_pending=True)
