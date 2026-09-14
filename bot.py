
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
ADMIN_IDS = [8422485324]  # ⚙️ আপনার প্রদত্ত Admin Numeric ID সফলভাবে বসানো হয়েছে

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
    
    # Dynamic Settings Table (Admin Panel Data)
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
        btn_channel = types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন 🌟", url=CHANNEL_LINK)
        btn_check = types.InlineKeyboardButton("✅ জয়েন সম্পন্ন হয়েছে 🚀", callback_data="check_join")
        markup.add(btn_channel)
        markup.add(btn_check)
        bot.send_message(user_id, "👋 **স্বাগতম!**\nকাজ শুরু করার আগ
