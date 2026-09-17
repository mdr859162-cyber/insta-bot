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
    
    defaults = {
        'task_rate': '3',
        'ref_bonus': '10',
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

def generate_credentials():
    username = "ig_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=7))
    password = "Pass#" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
    return username, password

# ==================== REAL-TIME AUTO VALIDATION ====================
def is_valid_2fa_secret(secret_key):
    """ ২এফএ কি-টি সঠিক কি না এবং লাইভ OTP কোড তৈরি করা যায় কি না চেক করবে """
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
    """ ব্যাকএন্ডে সরাসরি ইনস্টাগ্রাম প্রোফাইলের অস্তিত্ব ভ্যালিড করবে """
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
    """ ৬ ঘণ্টা পর অটোমেটিক ইউজারকে পেমেন্ট দেবে (কোনো ম্যানুয়াল রিভিউ ছাড়া) """
    while True:
        try:
            conn = get_db()
            cursor = conn.cursor()
            now = int(time.time())
            
            cursor.execute("SELECT id, user_id, ig_username, secret_key FROM tasks WHERE status = 'PENDING' AND auto_approve_at <= ?", (now,))
            pending_tasks = cursor.fetchall()

            for task in pending_tasks:
                t_id, u_id, ig_user, secret_key = task
                
                # ৬ ঘণ্টা পর ফাইনাল চেক
                if verify_instagram_account_exists(ig_user) and is_valid_2fa_secret(secret_key):
                    task_rate = float(get_setting("task_rate", "3"))

                    cursor.execute("UPDATE tasks SET status = 'APPROVED' WHERE id = ?", (t_id,))
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (task_rate, u_id))
                    conn.commit()

                    try:
                        bot.send_message(u_id, f"🎉 **আপনার কাজ অটোমেটিক এপ্রুভ হয়েছে!**\n💰 ওয়ালেটে যোগ হয়েছে: **৳{task_rate:.2f}**", parse_mode="Markdown")
                    except Exception: pass
                else:
                    cursor.execute("UPDATE tasks SET status = 'REJECTED' WHERE id = ?", (t_id,))
                    conn.commit()
                    try:
                        bot.send_message(u_id, "❌ **আপনার অ্যাকাউন্টটি ইনস্টাগ্রামে খুঁজে না পাওয়ায় কাজটি অটো-রিজেক্ট করা হয়েছে।**\n\nপ্রয়োজনে সঠিক নিয়ম জেনে আবার চেষ্টা করুন।", parse_mode="Markdown")
                    except Exception: pass

            conn.close()
        except Exception:
            pass
        
        time.sleep(30)

threading.Thread(target=background_auto_approver, daemon=True).start()

# ==================== WORK SUBMISSION (FULLY AUTOMATED) ====================
user_active_task = {}

@bot.callback_query_handler(func=lambda call: call.data == "finish_account")
def finish_account_submission(call):
    user_id = call.from_user.id
    if user_id not in user_active_task or "secret_key" not in user_active_task[user_id]:
        bot.answer_callback_query(call.id, "❌ এই কাজটি বাতিল করা হয়েছে!", show_alert=True)
        return

    task_data = user_active_task[user_id]
    ig_user = task_data["username"]
    secret_key = task_data["secret_key"]

    bot.answer_callback_query(call.id, "🔍 অটো-চেকিং চলছে...", show_alert=False)

    # ১. অটো 2FA ভ্যালিডেশন
    if not is_valid_2fa_secret(secret_key):
        bot.send_message(user_id, "❌ **ভুল/অকার্যকর 2FA Key!** সঠিক সিক্রেট কি দিয়ে আবার চেষ্টা করুন।", parse_mode="Markdown")
        return

    # ২. অটো প্রোফাইল প্রুফ ভ্যালিডেশন
    if not verify_instagram_account_exists(ig_user):
        bot.send_message(user_id, f"❌ **কাজ রিজেক্ট হয়েছে!**\n\n`{ig_user}` ইউজারনেমে কোনো অ্যাকাউন্ট তৈরি হয়নি। দয়া করে সঠিক নিয়ম মেনে আইডি তৈরি করুন।", parse_mode="Markdown")
        return

    # ৩. সম্পূর্ণ ভ্যালিড হলে অটো-পেন্ডিং এ যুক্ত
    del user_active_task[user_id]
    now = int(time.time())
    auto_approve_time = now + (6 * 3600) # ৬ ঘণ্টা পর অটো পেমেন্ট

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (user_id, ig_username, ig_password, secret_key, status, created_at, auto_approve_at) VALUES (?, ?, ?, ?, 'PENDING', ?, ?)",
                   (user_id, task_data["username"], task_data["password"], secret_key, now, auto_approve_time))
    conn.commit()
    conn.close()

    try: bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    except Exception: pass

    bot.send_message(user_id, "✅ **কাজ অটোমেটিক জমা নেওয়া হয়েছে!**\n\n৬ ঘণ্টার মধ্যে ব্যাকএন্ড অটো-সিস্টেম চূড়ান্ত ভেরিফাই করে আপনার ওয়ালেটে পেমেন্ট পাঠিয়ে দেবে।", parse_mode="Markdown")
