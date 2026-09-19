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
API_TOKEN = '8820592126:AAGieNIHM9b8U9jJGki4EO0_afvSRw59RBs'  # আপনার টেলিগ্রাম বটের টোকেন দিন
ADMIN_ID = 8422485324                  # আপনার টেলিগ্রাম ইউজার আইডি দিন
CHANNEL_USERNAME = "https://t.me/gmailhubsaport" # আপনার চ্যানেলের ইউজারনেম (সহ @)
CHANNEL_LINK = "https://t.me/gmailhubsaport"
SUPPORT_GROUP_LINK = "https://t.me/gmailhubsaport"
ADMIN_SUPPORT_LINK = "@Adiminsaport"

bot = telebot.TeleBot(API_TOKEN)

# ================= In-Memory Database =================
# প্রডাকশন লেভেলে SQLite বা MongoDB ব্যবহার করা উত্তম
users = {}
# Structure: { user_id: {'balance': 0.0, 'pending_balance': 0.0, 'total_tasks': 0, 'pending_tasks': 0, 'today_tasks': 0} }

pending_stock = [] 
# Structure: [{'user_id': 123, 'username': '...', 'password': '...', '2fa_key': '...'}]

active_user_tasks = {} 
# Structure: { user_id: {'username': '...', 'password': '...'} }

settings = {
    'bot_active': True,
    'task_rate': 10.0,        # প্রতি সফল আইডির রেট (টাকা)
    'min_withdraw': 100.0,    # সর্বনিম্ন উইথড্র (টাকা)
    'rules_text': "⚠️ *কাজের নিয়ম:* \nযেকোনো সমস্যা বা সহায়তার জন্য অ্যাডমিনের সাথে সরাসরি যোগাযোগ করুন।",
    'video_text': "🎬 *টিউটোরিয়াল ভিডিও:* \nখুব শীঘ্রই কাজের টিউটোরিয়াল ভিডিও আসছে! সাথে থাকুন। 🚀"
}

# ================= Helper Functions =================
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception:
        return False

def generate_credentials():
    num_part = ''.join(random.choices(string.digits, k=5))
    username = f"insta_x_hub_{num_part}"
    
    pass_nums = ''.join(random.choices(string.digits, k=4))
    password = f"InstaXHub@{pass_nums}#"
    
    return username, password

def check_instagram_user_exists(username):
    url = f"https://www.instagram.com/{username}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            return True
        return False
    except Exception:
        return True # এপিআই না থাকলে ডিফল্ট ট্রু ধরে আগানো নিরাপদ

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

# ================= User Keyboards =================
def build_welcome_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📢 ১. চ্যানেলে জয়েন করুন", url=CHANNEL_LINK)
    btn2 = types.InlineKeyboardButton("✅ ২. জয়েন করেছি", callback_data="verify_join")
    markup.add(btn1)
    markup.add(btn2)
    return markup

def build_main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🚀 কাজ শুরু করুন")
    btn2 = types.KeyboardButton("💰 ব্যালেন্স")
    btn3 = types.KeyboardButton("💳 উইথড্র")
    btn4 = types.KeyboardButton("📊 কাজের রিপোর্ট")
    btn5 = types.KeyboardButton("📜 কাজের নিয়ম")
    btn6 = types.KeyboardButton("🎧 সাপোর্ট ও হেল্পলাইন")
    btn7 = types.KeyboardButton("🎥 কাজ শেখার ভিডিও")
    markup.add(btn1)
    markup.add(btn2, btn3)
    markup.add(btn4, btn5)
    markup.add(btn6, btn7)
    return markup

def build_task_action_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔐 2FA Set", callback_data="set_2fa")
    btn2 = types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    markup.add(btn1, btn2)
    return markup

def build_submit_task_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📤 কাজ জমা দিন", callback_data="submit_task")
    btn2 = types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    markup.add(btn1, btn2)
    return markup

# ================= Admin Keyboard =================
def build_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    status_icon = "🟢 ON" if settings['bot_active'] else "🔴 OFF"
    
    markup.add(types.InlineKeyboardButton(f"🤖 বট স্ট্যাটাস: {status_icon}", callback_data="admin_toggle_bot"))
    markup.add(
        types.InlineKeyboardButton("📊 স্টক ইনফো", callback_data="admin_stock_info"),
        types.InlineKeyboardButton("📥 স্টক ডাউনলোড", callback_data="admin_stock_download")
    )
    markup.add(
        types.InlineKeyboardButton("💰 টাস্ক রেট", callback_data="admin_set_rate"),
        types.InlineKeyboardButton("💳 মিনিমাম উইথড্র", callback_data="admin_set_withdraw")
    )
    markup.add(
        types.InlineKeyboardButton("📢 অল ইউজার ব্রডকাস্ট", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("📤 বায়ার রিপোর্ট আপলোড", callback_data="admin_upload_report")
    )
    return markup

# ================= User Command Handlers =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    get_user_data(user_id)
    
    welcome_text = (
        f"👋 *আসালামু আলাইকুম, {message.from_user.first_name}!*\n\n"
        "✨ **Insta X Hub Management Bot**-এ আপনাকে স্বাগতম!\n"
        "আমাদের বটের মাধ্যমে সহজেই ইনস্টাগ্রাম একাউন্ট তৈরি করে দৈনিক ভালো টাকা আয় করুন। 💸\n\n"
        "👉 কাজ শুরু করার জন্য আগে আমাদের অফিসিয়াল চ্যানেলে যুক্ত হোন:"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=build_welcome_keyboard())

@bot.message_handler(commands=['admin'])
def admin_panel_cmd(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "⚙️ *এডমিন কন্ট্রোল প্যানেল:*", parse_mode="Markdown", reply_markup=build_admin_panel())
    else:
        bot.send_message(message.chat.id, "❌ আপনি এডমিন নন!")

# Callback Handler for Inline Buttons
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    user_id = call.from_user.id
    
    if call.data == "verify_join":
        if is_user_joined(user_id):
            bot.answer_callback_query(call.id, "✅ চ্যানেল ভেরিফিকেশন সফল!")
            bot.send_message(
                call.message.chat.id,
                "🎉 *আমাদের সাথে যুক্ত হওয়ার জন্য আপনাকে অনেক ধন্যবাদ!*\n\nনিচের মেনু থেকে আপনার কাঙ্ক্ষিত অপশন সিলেক্ট করুন। 👇",
                parse_mode="Markdown",
                reply_markup=build_main_menu()
            )
        else:
            bot.answer_callback_query(call.id, "❌ ভেরিফিকেশন ব্যর্থ হয়েছে!", show_alert=True)
            bot.send_message(call.message.chat.id, "⚠️ *দয়া করে আগে আমাদের চ্যানেলে জয়েন করুন, তারপর 'জয়েন করেছি' বাটনে ক্লিক করুন।*")

    elif call.data == "cancel_task":
        active_user_tasks.pop(user_id, None)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "❌ *আপনার কাজ টি সফলভাবে বাতিল করা হয়েছে।*", parse_mode="Markdown")

    elif call.data == "set_2fa":
        if user_id not in active_user_tasks:
            bot.send_message(call.message.chat.id, "⚠️ আপনার কোনো সক্রিয় কাজ পাওয়া যায়নি। আবার কাজ শুরু করুন।")
            return
        
        username = active_user_tasks[user_id]['username']
        bot.answer_callback_query(call.id, "🔍 ইনস্টাগ্রাম প্রোফাইল চেক করা হচ্ছে...")
        
        bot.send_message(call.message.chat.id, "⏳ *বট ইনস্টাগ্রাম একাউন্টটি ভ্যালিডেট করছে, অনুগ্রহ করে ২-৩ সেকেন্ড অপেক্ষা করুন...*", parse_mode="Markdown")
        time.sleep(2)
        
        if check_instagram_user_exists(username):
            msg = bot.send_message(call.message.chat.id, "✅ *একাউন্ট সঠিকভাবে তৈরি হয়েছে!*\n\n🔐 এবার আপনার **2FA Secret Key** টি ইনপুট হিসেবে পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_key)
        else:
            bot.send_message(call.message.chat.id, "❌ *একাউন্টটি পাওয়া যায়নি!*\n\nদয়া করে আগে দেওয়া ইউজারনেম ও পাসওয়ার্ড দিয়ে Instagram একাউন্ট তৈরি করুন, তারপর 2FA Set করুন।", parse_mode="Markdown")

    elif call.data == "submit_task":
        if user_id in active_user_tasks and '2fa_key' in active_user_tasks[user_id]:
            task_data = active_user_tasks[user_id]
            pending_stock.append({
                'user_id': user_id,
                'username': task_data['username'],
                'password': task_data['password'],
                '2fa_key': task_data['2fa_key']
            })
            
            u_data = get_user_data(user_id)
            u_data['pending_tasks'] += 1
            u_data['today_tasks'] += 1
            u_data['pending_balance'] += settings['task_rate']
            
            active_user_tasks.pop(user_id, None)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "🎉 *আপনার কাজটি সফলভাবে জমা নেওয়া হয়েছে!*\n⏰ ১২-২৪ ঘণ্টার মধ্যে রিভিউ সম্পন্ন করে টাকা ওয়ালেটে যোগ করে দেওয়া হবে। 💸",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(call.message.chat.id, "⚠️ কোনো তথ্য পাওয়া যায়নি!")

    # Admin Callback Actions
    elif call.data == "admin_toggle_bot":
        if user_id == ADMIN_ID:
            settings['bot_active'] = not settings['bot_active']
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=build_admin_panel())

    elif call.data == "admin_stock_info":
        if user_id == ADMIN_ID:
            bot.send_message(call.message.chat.id, f"📦 *বর্তমান পেন্ডিং স্টক:* `{len(pending_stock)}` টি আইডি।", parse_mode="Markdown")

    elif call.data == "admin_stock_download":
        if user_id == ADMIN_ID:
            if not pending_stock:
                bot.send_message(call.message.chat.id, "⚠️ ডাউনলোড করার মতো কোনো স্টক নেই!")
                return
            
            df = pd.DataFrame(pending_stock)
            excel_path = "pending_stock.xlsx"
            df[['username', 'password', '2fa_key']].to_excel(excel_path, index=False)
            
            with open(excel_path, 'rb') as doc:
                bot.send_document(call.message.chat.id, doc, caption="📥 *পেন্ডিং কাজের আপডেট এক্সেল ফাইল।*", parse_mode="Markdown")
            os.remove(excel_path)

    elif call.data == "admin_upload_report":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📤 *বায়ারের রিপোর্ট ফাইল (.xlsx) টি আপলোড করুন:*", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_buyer_report)

def process_2fa_key(message):
    user_id = message.from_user.id
    raw_key = message.text.strip().replace(" ", "")
    
    try:
        totp = pyotp.TOTP(raw_key)
        current_code = totp.now()
        
        active_user_tasks[user_id]['2fa_key'] = raw_key
        
        success_msg = (
            f"🔑 *2FA Key সফলভাবে যুক্ত করা হয়েছে!*\n\n"
            f"⚙️ **Generated Code:** `{current_code}`\n\n"
            f"কাজ সম্পূর্ণ করতে নিচের **'কাজ জমা দিন'** বাটনে ক্লিক করুন। 👇"
        )
        bot.send_message(message.chat.id, success_msg, parse_mode="Markdown", reply_markup=build_submit_task_keyboard())
    except Exception:
        msg = bot.send_message(message.chat.id, "❌ *অকার্যকর 2FA Key!* \nদয়া করে সঠিক Key টি দিন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_2fa_key)

# ================= Text Message Handlers =================
@bot.message_handler(func=lambda message: True)
def handle_menu_options(message):
    if not settings['bot_active'] and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⚠️ *বট রক্ষণাবেক্ষনের জন্য বর্তমানে বন্ধ আছে। পরবর্তীতে চেষ্টা করুন।*", parse_mode="Markdown")
        return

    user_id = message.from_user.id
    text = message.text
    u_data = get_user_data(user_id)

    if text == "🚀 কাজ শুরু করুন":
        if not is_user_joined(user_id):
            bot.send_message(message.chat.id, "⚠️ *দয়া করে আগে আমাদের চ্যানেলে জয়েন করুন!*", reply_markup=build_welcome_keyboard())
            return
            
        username, password = generate_credentials()
        active_user_tasks[user_id] = {'username': username, 'password': password}
        
        task_text = (
            "✨ *আপনার কাজের বিস্তারিত তথ্য নিচে দেওয়া হলো:* ✨\n\n"
            f"👤 **Username:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            "👉 ওপরের তথ্য দিয়ে একাউন্ট তৈরি করে **2FA Set** বাটনে চাপ দিন।"
        )
        bot.send_message(message.chat.id, task_text, parse_mode="Markdown", reply_markup=build_task_action_keyboard())

    elif text == "💰 ব্যালেন্স":
        balance_msg = (
            "💼 *আপনার ওয়ালেট রিপোর্ট:* 💼\n\n"
            f"💵 **বর্তমান ব্যালেন্স:** `{u_data['balance']:.2f}` টাকা\n"
            f"⏳ **পেন্ডিং ব্যালেন্স:** `{u_data['pending_balance']:.2f}` টাকা\n"
            f"🏆 **মোট আয়:** `{u_data['balance'] + u_data['pending_balance']:.2f}` টাকা"
        )
        bot.send_message(message.chat.id, balance_msg, parse_mode="Markdown")

    elif text == "💳 উইথড্র":
        if u_data['balance'] < settings['min_withdraw']:
            bot.send_message(
                message.chat.id,
                f"⚠️ *সর্বনিম্ন উইথড্র লিমিট {settings['min_withdraw']:.0f} টাকা।*\nআপনার বর্তমান ব্যালেন্স: `{u_data['balance']:.2f}` টাকা।",
                parse_mode="Markdown"
            )
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📱 বিকাশ", callback_data="withdraw_bkash"),
                types.InlineKeyboardButton("📱 নগদ", callback_data="withdraw_nagad")
            )
            bot.send_message(message.chat.id, "💳 *আপনি কোন মাধ্যমে টাকা তুলতে চান?*", parse_mode="Markdown", reply_markup=markup)

    elif text == "📊 কাজের রিপোর্ট":
        report_msg = (
            "📊 *আপনার ব্যক্তিগত কাজের রিপোর্ট:* 📊\n\n"
            f"📅 **আজকের জমা দেওয়া কাজ:** `{u_data['today_tasks']}` টি\n"
            f"⏳ **পেন্ডিং কাজ:** `{u_data['pending_tasks']}` টি\n"
            f"✅ **মোট সফলভাবে জমা দেওয়া কাজ:** `{u_data['total_tasks']}` টি"
        )
        bot.send_message(message.chat.id, report_msg, parse_mode="Markdown")

    elif text == "📜 কাজের নিয়ম":
        bot.send_message(message.chat.id, settings['rules_text'], parse_mode="Markdown")

    elif text == "🎧 সাপোর্ট ও হেল্পলাইন":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=ADMIN_SUPPORT_LINK),
            types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপ", url=SUPPORT_GROUP_LINK)
        )
        bot.send_message(message.chat.id, "🎧 *যেকোনো সহযোগিতার জন্য নিচে যোগাযোগ করুন:*", parse_mode="Markdown", reply_markup=markup)

    elif text == "🎥 কাজ শেখার ভিডিও":
        bot.send_message(message.chat.id, settings['video_text'], parse_mode="Markdown")

# ================= Buyer Report Excel Processing =================
def process_buyer_report(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ ফাইল পাওয়া যায়নি!")
        return
        
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = "buyer_report.xlsx"
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)
            
        df = pd.read_excel(file_name)
        
        # প্রসেসিং: ধরে নেওয়া হচ্ছে Excel-এ 'username' এবং 'status' কলাম আছে
        # status == 'success' হলে টাকা যোগ হবে
        success_count = 0
        for index, row in df.iterrows():
            uname = row.get('username')
            status = str(row.get('status')).lower()
            
            # স্টক থেকে ডাটা খুজে বের করা
            for item in pending_stock[:]:
                if item['username'] == uname:
                    u_id = item['user_id']
                    u_data = get_user_data(u_id)
                    
                    if 'success' in status or 'valid' in status or 'green' in status:
                        u_data['balance'] += settings['task_rate']
                        u_data['pending_balance'] -= settings['task_rate']
                        u_data['pending_tasks'] -= 1
                        u_data['total_tasks'] += 1
                        success_count += 1
                        
                        bot.send_message(
                            u_id,
                            f"🎉 *কাজের টাকা যোগ হয়েছে!*\n"
                            f"ইউজারনেম: `{uname}`\n"
                            f"💰 💸 `{settings['task_rate']}` টাকা ওয়ালেটে যোগ করা হয়েছে।",
                            parse_mode="Markdown"
                        )
                    else:
                        u_data['pending_balance'] -= settings['task_rate']
                        u_data['pending_tasks'] -= 1
                        
                        bot.send_message(
                            u_id,
                            f"❌ *কাজ রিজেক্ট হয়েছে!*\n"
                            f"ইউজারনেম: `{uname}`\n"
                            "একাউন্টটি সঠিকভাবে তৈরি হয়নি বা ডিজেবল হয়ে গেছে।",
                            parse_mode="Markdown"
                        )
                    pending_stock.remove(item)

        bot.send_message(message.chat.id, f"✅ *রিপোর্ট প্রসেস সম্পন্ন!* \nমোট `{success_count}` টি আইডির পেমেন্ট সফলভাবে যোগ করা হয়েছে।", parse_mode="Markdown")
        os.remove(file_name)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ফাইল প্রসেস করতে সমস্যা হয়েছে: {str(e)}")

# ================= Bot Launch =================
if __name__ == '__main__':
    print("🤖 Insta X Hub Bot Running...")
    bot.infinity_polling()
