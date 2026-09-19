import os
import re
import random
import string
import time
import pyotp
import requests
import pandas as pd
import telebot
from telebot import types

# ================= Configuration =================
API_TOKEN = '8820592126:AAGieNIHM9b8U9jJGki4EO0_afvSRw59RBs'
ADMIN_ID = 8422485324
ADMIN_USERNAME = "@Adiminsaport"
SUPPORT_GROUP_LINK = "https://t.me/gmailhubsaport"
CHANNEL_LINK = "https://t.me/instaXhubsaport"
CHANNEL_USERNAME = "@instaXhubsaport"

bot = telebot.TeleBot(API_TOKEN)

# ================= In-Memory Database =================
users = {}
download_stock = [] 
active_user_tasks = {} 
admin_states = {}

settings = {
    'bot_active': True,
    'task_rate': 10.0,
    'min_withdraw': 100.0,
    'refer_bonus': 2.0,
    'welcome_msg': "👋 *আসালামু আলাইকুম!*\n✨ **Insta X Hub Management Bot**-এ আপনাকে স্বাগতম!\nআমাদের বটের মাধ্যমে সহজেই ইনস্টাগ্রাম একাউন্ট তৈরি করে দৈনিক ভালো টাকা আয় করুন। 💸",
    'rules_text': "⚠️ *কাজের নিয়ম:* \nযেকোনো সমস্যা বা সহায়তার জন্য সরাসরি অ্যাডমিনের সাথে যোগাযোগ করুন।",
    'video_text': "🎬 *টিউটোরিয়াল ভিডিও:* \nখুব শীঘ্রই কাজের টিউটোরিয়াল ভিডিও আসছে! সাথে থাকুন। 🚀",
    'refer_msg': "🎁 *রেফার করে আয় করুন:* \nআপনার বন্ধুদের রেফার করে প্রতি রেফারে আকর্ষণীয় বোনাস পান!",
    'helpline_msg': "🎧 *হেল্পলাইন ও সাপোর্ট:* \nযেকোনো সমস্যায় আমাদের সাপোর্ট গ্রুপ বা এডমিনের সাথে যোগাযোগ করুন।"
}

# ================= Helper Functions =================
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception:
        return True

def generate_credentials():
    num_part = ''.join(random.choices(string.digits, k=5))
    username = f"insta_x_hub_{num_part}"
    pass_nums = ''.join(random.choices(string.digits, k=4))
    password = f"InstaXHub@{pass_nums}#"
    return username, password

def check_instagram_user_exists(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return True
        return False
    except Exception:
        return True

def get_user_data(user_id):
    if user_id not in users:
        users[user_id] = {
            'balance': 0.0,
            'pending_balance': 0.0,
            'total_tasks': 0,
            'pending_tasks': 0,
            'today_tasks': 0
        }
    return users[user_id]

# ================= Keyboards =================
def build_welcome_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📢 ১. চ্যানেলে জয়েন করুন", url=CHANNEL_LINK)
    btn2 = types.InlineKeyboardButton("✅ ২. জয়েন করেছি", callback_data="verify_join")
    markup.add(btn1)
    markup.add(btn2)
    return markup

def build_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add("🚀 কাজ শুরু করুন")
    markup.add("💰 ব্যালেন্স & উইথড্র 💳")
    markup.add("📊 কাজের রিপোর্ট", "📜 কাজের নিয়ম ⚠️")
    markup.add("🎁 রেফার করুন", "🆘 হেল্পলাইন 📞")
    return markup

def build_task_action_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔐 2FA Set", callback_data="set_2fa")
    btn2 = types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    markup.add(btn1, btn2)
    return markup

def build_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    status_icon = "🟢 ON" if settings['bot_active'] else "🔴 OFF"
    
    markup.add(types.InlineKeyboardButton(f"🤖 বট স্ট্যাটাস: {status_icon}", callback_data="admin_toggle_bot"))
    markup.add(
        types.InlineKeyboardButton("🏆 টপ ৫ রেফারার", callback_data="admin_top_ref"),
        types.InlineKeyboardButton("🏆 টপ ৫ ওয়ার্কার", callback_data="admin_top_worker")
    )
    markup.add(
        types.InlineKeyboardButton("🔄 রিসেট টপ রেফারার", callback_data="admin_reset_ref"),
        types.InlineKeyboardButton("🔄 রিসেট টপ ওয়ার্কার", callback_data="admin_reset_worker")
    )
    markup.add(
        types.InlineKeyboardButton("✉️ সেন্ড কাস্টম মেসেজ", callback_data="admin_custom_msg"),
        types.InlineKeyboardButton("💰 এড ব্যালেন্স", callback_data="admin_add_bal")
    )
    markup.add(
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="admin_stock_info"),
        types.InlineKeyboardButton("📲 স্টক ডাউনলোড", callback_data="admin_stock_download")
    )
    markup.add(
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="admin_set_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="admin_set_withdraw")
    )
    markup.add(
        types.InlineKeyboardButton("🎁 রেফার বোনাস", callback_data="admin_set_ref_bonus"),
        types.InlineKeyboardButton("🔴 বট OFF করুন" if settings['bot_active'] else "🟢 বট ON করুন", callback_data="admin_toggle_bot")
    )
    markup.add(
        types.InlineKeyboardButton("📢 জয়েন চ্যানেল এডিট", callback_data="admin_edit_channel"),
        types.InlineKeyboardButton("📜 কাজের নিয়ম এডিট", callback_data="admin_edit_rules")
    )
    markup.add(
        types.InlineKeyboardButton("👋 ওয়েলকাম মেসেজ", callback_data="admin_edit_welcome"),
        types.InlineKeyboardButton("🎁 রেফার মেসেজ", callback_data="admin_edit_ref_msg")
    )
    markup.add(
        types.InlineKeyboardButton("🎧 হেল্পলাইন মেসেজ", callback_data="admin_edit_help_msg"),
        types.InlineKeyboardButton("🎬 ভিডিও লিংক এডিট", callback_data="admin_edit_video")
    )
    markup.add(
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📤 বায়ার রিপোর্ট আপলোড", callback_data="admin_upload_report")
    )
    return markup

# ================= Handlers =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    get_user_data(user_id)
    bot.send_message(message.chat.id, settings['welcome_msg'], parse_mode="Markdown", reply_markup=build_welcome_keyboard())

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "⚙️ *এডমিন কন্ট্রোল প্যানেল:*", parse_mode="Markdown", reply_markup=build_admin_panel())

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "verify_join":
        if is_user_joined(user_id):
            bot.answer_callback_query(call.id, "✅ চ্যানেল ভেরিফিকেশন সফল!")
            bot.send_message(call.message.chat.id, "🎉 *আমাদের সাথে যুক্ত হওয়ার জন্য ধন্যবাদ!*", parse_mode="Markdown", reply_markup=build_main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ দয়া করে আগে চ্যানেলে জয়েন করুন!", show_alert=True)

    elif call.data == "cancel_task":
        active_user_tasks.pop(user_id, None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "❌ *আপনার কাজটি বাতিল করা হয়েছে।*", parse_mode="Markdown")

    elif call.data == "set_2fa":
        if user_id not in active_user_tasks:
            bot.send_message(call.message.chat.id, "⚠️ সক্রিয় কোনো কাজ পাওয়া যায়নি। আবার শুরু করুন।")
            return
        
        username = active_user_tasks[user_id]['username']
        bot.answer_callback_query(call.id, "🔍 চেক করা হচ্ছে...")
        bot.send_message(call.message.chat.id, "⏳ *বট ইনস্টাগ্রাম একাউন্টটি ভ্যালিডেট করছে...*", parse_mode="Markdown")
        time.sleep(2)
        
        if check_instagram_user_exists(username):
            # মেসেজটি পপআপ ডিলিট করে নেওয়া হচ্ছে
            active_user_tasks[user_id]['action_msg_id'] = call.message.message_id
            msg = bot.send_message(call.message.chat.id, "✅ *একাউন্ট সঠিকভাবে তৈরি হয়েছে!*\n\n🔐 এবার আপনার **2FA Secret Key** টি ইনপুট পাঠাও:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_key)
        else:
            bot.send_message(call.message.chat.id, "❌ *একাউন্টটি পাওয়া যায়নি!*\nদয়া করে আগে দেওয়া তথ্য দিয়ে Instagram একাউন্ট খুলুন।", parse_mode="Markdown")

    elif call.data == "admin_toggle_bot":
        if user_id == ADMIN_ID:
            settings['bot_active'] = not settings['bot_active']
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=build_admin_panel())

    elif call.data == "admin_stock_info":
        if user_id == ADMIN_ID:
            bot.send_message(call.message.chat.id, f"📦 *ডাউনলোড স্টকে রেডি আইডি:* `{len(download_stock)}` টি।", parse_mode="Markdown")

    elif call.data == "admin_stock_download":
        if user_id == ADMIN_ID:
            if not download_stock:
                bot.send_message(call.message.chat.id, "⚠️ কোনো ডাউনলোড স্টক নেই!")
                return
            df = pd.DataFrame(download_stock)
            excel_path = "download_stock.xlsx"
            df[['username', 'password', '2fa_key']].to_excel(excel_path, index=False)
            with open(excel_path, 'rb') as doc:
                bot.send_document(call.message.chat.id, doc, caption="📥 *ডাউনলোড স্টক এক্সেল ফাইল।*", parse_mode="Markdown")
            os.remove(excel_path)

    elif call.data.startswith("admin_edit_"):
        if user_id == ADMIN_ID:
            key = call.data.replace("admin_edit_", "")
            admin_states[user_id] = key
            bot.send_message(call.message.chat.id, f"✍️ নতুন টেক্সট বা ইনপুট পাঠান `{key}` এর জন্য:", parse_mode="Markdown")

def process_2fa_key(message):
    user_id = message.from_user.id
    raw_key = message.text.strip().replace(" ", "")
    
    try:
        totp = pyotp.TOTP(raw_key)
        current_code = totp.now() # ভ্যালিড 2FA Key চেক
        
        task_data = active_user_tasks.get(user_id)
        if task_data:
            # ডাউনলোড স্টকে জমা
            download_stock.append({
                'user_id': user_id,
                'username': task_data['username'],
                'password': task_data['password'],
                '2fa_key': raw_key
            })
            
            u_data = get_user_data(user_id)
            u_data['pending_tasks'] += 1
            u_data['today_tasks'] += 1
            u_data['pending_balance'] += settings['task_rate']
            
            # আগের বাটন ডায়ালগ মেসেজ মোছা
            if 'action_msg_id' in task_data:
                try:
                    bot.delete_message(message.chat.id, task_data['action_msg_id'])
                except Exception:
                    pass
            
            active_user_tasks.pop(user_id, None)
            
            bot.send_message(
                message.chat.id,
                f"🔑 *2FA Key ভ্যালিড করা হয়েছে! (Code: {current_code})*\n\n"
                "🎉 *আপনার কাজটি সফলভাবে জমা নেওয়া হয়েছে!*\n⏰ ১২-২৪ ঘণ্টার মধ্যে রিভিউ সম্পন্ন করে টাকা ওয়ালেটে যোগ করে দেওয়া হবে। 💸",
                parse_mode="Markdown"
            )
    except Exception:
        msg = bot.send_message(message.chat.id, "❌ *অকার্যকর 2FA Key!* \nকাজ জমা নেওয়া হয়নি। দয়া করে সঠিক 2FA Key টি দিন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_2fa_key)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    if user_id == ADMIN_ID and user_id in admin_states:
        state = admin_states.pop(user_id)
        if state == "welcome": settings['welcome_msg'] = text
        elif state == "rules": settings['rules_text'] = text
        elif state == "video": settings['video_text'] = text
        elif state == "ref_msg": settings['refer_msg'] = text
        elif state == "help_msg": settings['helpline_msg'] = text
        bot.send_message(message.chat.id, "✅ *সফলভাবে আপডেট করা হয়েছে!*", parse_mode="Markdown")
        return

    if text == "🚀 কাজ শুরু করুন":
        username, password = generate_credentials()
        active_user_tasks[user_id] = {'username': username, 'password': password}
        task_text = (
            "✨ *আপনার কাজের বিস্তারিত তথ্য নিচে দেওয়া হলো:* ✨\n\n"
            f"👤 **Username:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            "👉 ওপরের তথ্য দিয়ে একাউন্ট তৈরি করে **2FA Set** বাটনে চাপ দিন।"
        )
        bot.send_message(message.chat.id, task_text, parse_mode="Markdown", reply_markup=build_task_action_keyboard())

    elif text == "💰 ব্যালেন্স & উইথড্র 💳":
        u_data = get_user_data(user_id)
        balance_msg = (
            "💼 *আপনার ওয়ালেট রিপোর্ট:* 💼\n\n"
            f"💵 **বর্তমান ব্যালেন্স:** `{u_data['balance']:.2f}` টাকা\n"
            f"⏳ **পেন্ডিং ব্যালেন্স:** `{u_data['pending_balance']:.2f}` টাকা\n"
            f"🏆 **মোট আয়:** `{u_data['balance'] + u_data['pending_balance']:.2f}` টাকা\n\n"
            f"📌 **সর্বনিম্ন উইথড্র:** {settings['min_withdraw']:.0f} টাকা।"
        )
        bot.send_message(message.chat.id, balance_msg, parse_mode="Markdown")

    elif text == "📊 কাজের রিপোর্ট":
        u_data = get_user_data(user_id)
        report_msg = (
            "📊 *আপনার ব্যক্তিগত কাজের রিপোর্ট:* 📊\n\n"
            f"📅 **আজকের জমা দেওয়া কাজ:** `{u_data['today_tasks']}` টি\n"
            f"⏳ **পেন্ডিং কাজ:** `{u_data['pending_tasks']}` টি\n"
            f"✅ **মোট সফলভাবে জমা দেওয়া কাজ:** `{u_data['total_tasks']}` টি"
        )
        bot.send_message(message.chat.id, report_msg, parse_mode="Markdown")

    elif text == "📜 কাজের নিয়ম ⚠️":
        bot.send_message(message.chat.id, settings['rules_text'], parse_mode="Markdown")

    elif text == "🎁 রেফার করুন":
        bot.send_message(message.chat.id, settings['refer_msg'], parse_mode="Markdown")

    elif text == "🆘 হেল্পলাইন 📞":
        markup = types.InlineKeyboardMarkup()
        admin_link = f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"
        markup.add(
            types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=admin_link),
            types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপ", url=SUPPORT_GROUP_LINK)
        )
        bot.send_message(message.chat.id, settings['helpline_msg'], parse_mode="Markdown", reply_markup=markup)

if __name__ == '__main__':
    print("🤖 Insta X Hub Bot Running...")
    bot.infinity_polling()
