import telebot
from telebot import types
import sqlite3
import random
import string
import time

# ==================== CONFIGURATION ====================
TOKEN = "8820592126:AAF8UF5emIHX4fsh2eUZ9wrMUWI0djqsnVs"
ADMIN_IDS = [8422485324]

# আপনার সাপোর্ট গ্রুপের সঠিক ইউজারনেম ও লিংক
SUPPORT_GROUP_USERNAME = "@instaXhubsaport" 
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
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
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

# ==================== MUST JOIN CHECK ====================
def check_must_join(user_id):
    if is_admin(user_id):
        return True
    try:
        member = bot.get_chat_member(SUPPORT_GROUP_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        # গ্রুপে বটকে অ্যাডমিন না বানালে বা ইউজারনেম ভুল হলে চেক ফেল করবে
        print(f"Join Check Error: {e}")
        return False

def send_must_join_msg(chat_id):
    # ১. প্রথমে নিচের মেনু বাটনগুলো সম্পূর্ণ মুছে ফেলার কমান্ড
    remove_menu = types.ReplyKeyboardRemove()
    
    # ২. জয়েন করার বাটন তৈরি
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 অফিশিয়াল সাপোর্ট গ্রুপে জয়েন করুন", url=SUPPORT_GROUP_LINK),
        types.InlineKeyboardButton("✅ জয়েন করেছি", callback_data="check_joined")
    )
    
    # মেসেজ পাঠানো এবং নিচের কিবোর্ড লুকিয়ে ইনলাইন বাটন দেখানো
    bot.send_message(
        chat_id, 
        "⚠️ **আমাদের বটে কাজ করার জন্য অবশ্যই অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হন।**", 
        reply_markup=remove_menu, 
        parse_mode="Markdown"
    )
    bot.send_message(
        chat_id, 
        "👉 জয়েন হয়ে নিচের বাটনে চাপ দিয়ে ভেরিফাই করুন:", 
        reply_markup=markup, 
        parse_mode="Markdown"
    )

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

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "নাই"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                       (user_id, username, int(time.time())))
    conn.commit()
    conn.close()

    # গ্রুপে যুক্ত আছে কিনা ভেরিফিকেশন
    if check_must_join(user_id):
        # যুক্ত থাকলে নিচের কাজ শুরু করার মূল মেনু দেখাবে
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **নিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশনটি বেছে নিন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        # যুক্ত না থাকলে মেনু বাটন লুকিয়ে শুধু জয়েন বাটন দেখাবে
        send_must_join_msg(user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_joined")
def check_joined_callback(call):
    user_id = call.from_user.id
    if check_must_join(user_id):
        bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=False)
        text = get_setting("welcome_msg")
        success_msg = f"{text}\n\n🎉 **আপনার জয়েনিং সফল হয়েছে! নিচের মেনু থেকে কাজ শুরু করুন।** 👇"
        bot.send_message(user_id, success_msg, reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(
            call.id, 
            "⚠️ দয়া করে আগে আমাদের অফিশিয়াল সাপোর্ট গ্রুপে যুক্ত হন, তারপরে কাজ শুরু করুন!", 
            show_alert=True
        )

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    if not check_must_join(user_id):
        send_must_join_msg(user_id)
        return

bot.infinity_polling()
