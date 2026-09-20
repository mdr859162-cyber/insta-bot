import os
import random
import string
import time
import threading
import pyotp
import requests
import pandas as pd
import telebot
from telebot import types

# ================= Configuration =================
API_TOKEN = '8820592126:AAGieNIHM9b8U9jJGki4EO0_afvSRw59RBs'
ADMIN_ID = 8422485324
ADMIN_USERNAME = "@Adiminsaport"
SUPPORT_CHANNEL_LINK = "https://t.me/instaXhubsaport"
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
    'refer_bonus': 10.0,  # Updated to 10 TK as per your request
    'welcome_msg': "👋 *আসালামু আলাইকুম!*\n✨ **Insta X Hub Management Bot**-এ আপনাকে স্বাগতম!",
    'rules_text': "⚠️ *কাজের নিয়ম:* \nসঠিকভাবে ইনস্টাগ্রাম একাউন্ট খুলে 2FA সেট করে জমা দিন।",
    'video_url': "https://t.me/instaXhubsaport", # Support group post/video link
    'refer_msg': "🎁 *রেফার করে আয় করুন!*",
    'helpline_msg': "🎧 *হেল্পলাইন ও সাপোর্ট:* \nযেকোনো সমস্যায় আমাদের চ্যানেলে জয়েন করুন বা এডমিনকে মেসেজ দিন।"
}

# ================= Helper Functions =================
def is_user_joined(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ['creator', 'administrator', 'member']
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
        return res.status_code == 200
    except Exception:
        return False

def get_user_data(user_id):
    if user_id not in users:
        users[user_id] = {
            'balance': 0.0,
            'pending_balance': 0.0,
            'total_tasks': 0,
            'pending_tasks': 0,
            'today_tasks': 0,
            'referrals': 0,
            'refer_income': 0.0,
            'referred_by': None,
            'is_first_task_done': False,
            'ip_sim_hash': None # Device tracking
        }
    return users[user_id]

# 1-Hour Auto Cancel Task Scheduler
def start_task_timer(user_id, chat_id):
    def timer_job():
        time.sleep(3600)  # 1 Hour
        if user_id in active_user_tasks:
            active_user_tasks.pop(user_id, None)
            try:
                bot.send_message(chat_id, "⏰ *সময় শেষ!* ১ ঘণ্টা পার হয়ে যাওয়ায় আপনার চলমান কাজটি অটোমেটিক বাতিল করা হয়েছে।", parse_mode="Markdown")
            except Exception:
                pass
    t = threading.Thread(target=timer_job)
    t.daemon = True
    t.start()

# ================= Keyboards =================
def build_welcome_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("📢 ১. চ্যানেলে জয়েন করুন", url=SUPPORT_CHANNEL_LINK)
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
    markup.add("🎬 কাজ শেখার ভিডিও")
    return markup

def build_task_action_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🔐 2FA Set", callback_data="set_2fa")
    btn2 = types.InlineKeyboardButton("❌ কাজ বাতিল করুন", callback_data="cancel_task")
    markup.add(btn1, btn2)
    return markup

def build_submit_keyboard():
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("🎉 কাজ জমা দিন", callback_data="submit_final_job")
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
        types.InlineKeyboardButton("📤 বায়ার রিপোর্ট আপলোড", callback_data="admin_upload_report_menu")
    )
    return markup

# ================= Handlers =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    u_data = get_user_data(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and u_data['referred_by'] is None:
            u_data['referred_by'] = ref_id
            
            # Send Notification to Referrer (Without instant bonus, first task pending)
            try:
                bot.send_message(
                    ref_id, 
                    f"🎉 *আপনার রেফার লিংক থেকে একজন ইউজার বটে যুক্ত হয়েছেন!*\n\n"
                    f"👉 তার প্রথম কাজটি সফলভাবে জমা হলে আপনি পাবেন `{settings['refer_bonus']:.0f}` টাকা বোনাস।",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

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
            bot.answer_callback_query(call.id, "✅ ভেরিফিকেশন সফল!")
            bot.send_message(call.message.chat.id, "🎉 *আমাদের সাথে যুক্ত হওয়ার জন্য ধন্যবাদ!*", parse_mode="Markdown", reply_markup=build_main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ দয়া করে আগে চ্যানেলে জয়েন করুন!", show_alert=True)

    elif call.data == "cancel_task":
        active_user_tasks.pop(user_id, None)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "❌ *আপনার কাজটি সফলভাবে বাতিল করা হয়েছে।*", parse_mode="Markdown")

    elif call.data == "set_2fa":
        if user_id not in active_user_tasks:
            bot.send_message(call.message.chat.id, "⚠️ আপনার কোনো চলমান কাজ পাওয়া যায়নি। আবার নতুন কাজ শুরু করুন।")
            return
        
        username = active_user_tasks[user_id]['username']
        bot.answer_callback_query(call.id, "🔍 চেক করা হচ্ছে...")
        status_msg = bot.send_message(call.message.chat.id, "⏳ *বট ইনস্টাগ্রাম একাউন্টটি চেক করছে...*", parse_mode="Markdown")
        time.sleep(1.5)
        
        if check_instagram_user_exists(username):
            try:
                bot.delete_message(call.message.chat.id, status_msg.message_id)
            except Exception:
                pass
            active_user_tasks[user_id]['attempts'] = 0
            msg = bot.send_message(call.message.chat.id, "✅ *একাউন্ট সঠিকভাবে তৈরি হয়েছে!*\n\n🔐 এবার আপনার **2FA Secret Key** টি ইনপুট হিসেবে পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_2fa_key)
        else:
            try:
                bot.delete_message(call.message.chat.id, status_msg.message_id)
            except Exception:
                pass
            bot.send_message(call.message.chat.id, "❌ *একাউন্টটি ইনস্টাগ্রামে পাওয়া যায়নি!*\nদয়া করে আগে সঠিকভাবে ইউজারনেম ও পাসওয়ার্ড দিয়ে একাউন্ট তৈরি করুন, তারপর চেষ্টা করুন।", parse_mode="Markdown")

    elif call.data == "submit_final_job":
        task_data = active_user_tasks.get(user_id)
        if not task_data or 'temp_2fa' not in task_data:
            bot.send_message(call.message.chat.id, "⚠️ আপনার কাজের সেশনটির মেয়াদ শেষ হয়ে গেছে।")
            return

        download_stock.append({
            'user_id': user_id,
            'username': task_data['username'],
            'password': task_data['password'],
            '2fa_key': task_data['temp_2fa']
        })
        
        u_data = get_user_data(user_id)
        u_data['pending_tasks'] += 1
        u_data['today_tasks'] += 1
        u_data['pending_balance'] += settings['task_rate']
        
        # Checking First Completed Task & Fake Referral Verification Logic
        if not u_data['is_first_task_done'] and u_data['referred_by'] is not None:
            ref_id = u_data['referred_by']
            ref_user = get_user_data(ref_id)
            
            # Simulated Device/IP Same Check
            is_same_device_or_ip = False
            if u_data.get('ip_sim_hash') and ref_user.get('ip_sim_hash'):
                if u_data['ip_sim_hash'] == ref_user['ip_sim_hash']:
                    is_same_device_or_ip = True
            
            if is_same_device_or_ip:
                try:
                    bot.send_message(
                        ref_id,
                        "❌ *রেফার বোনাস প্রদান ব্যর্থ হয়েছে!*\n\n"
                        "⚠️ আপনি একই আইডি/আইপি দিয়ে ফেক রেফার করার চেষ্টা করেছেন। বোনাস প্রদান বাতিল করা হলো। সঠিক রেফার করে আয় করুন।",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            else:
                # Valid Referral Bonus Awarded
                ref_user['referrals'] += 1
                ref_user['refer_income'] += settings['refer_bonus']
                ref_user['balance'] += settings['refer_bonus']
                try:
                    bot.send_message(
                        ref_id,
                        f"🎉 *অভিনন্দন! আপনার রেফারেল ইউজারের ১ম কাজ সফলভাবে জমা হয়েছে।*\n\n"
                        f"💰 আপনার অ্যাকাউন্টে **{settings['refer_bonus']:.0f} টাকা** রেফার বোনাস যোগ করা হয়েছে।",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            
            u_data['is_first_task_done'] = True

        if 'task_msg_id' in task_data:
            try:
                bot.delete_message(call.message.chat.id, task_data['task_msg_id'])
            except Exception:
                pass

        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
            
        active_user_tasks.pop(user_id, None)
        
        bot.send_message(
            call.message.chat.id,
            "🎉 *আপনার কাজটি সফলভাবে জমা নেওয়া হয়েছে!*\n"
            "⏰ ১২-২৪ ঘণ্টার মধ্যে রিভিউ সম্পন্ন করে টাকা ওয়ালেটে যোগ করে দেওয়া হবে। 💸",
            parse_mode="Markdown"
        )

    # Admin Control Callback Handlers
    elif call.data == "admin_toggle_bot":
        if user_id == ADMIN_ID:
            settings['bot_active'] = not settings['bot_active']
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=build_admin_panel())

    elif call.data == "admin_top_ref":
        if user_id == ADMIN_ID:
            sorted_ref = sorted(users.items(), key=lambda x: x[1]['referrals'], reverse=True)[:5]
            msg = "🏆 *টপ ৫ রেফারার এর তালিকা:*\n\n"
            for idx, (u_id, u_info) in enumerate(sorted_ref, 1):
                msg += f"{idx}. 🆔 `{u_id}` | 👥 রেফার: `{u_info['referrals']}` জন | 💰 ইনকাম: `{u_info['refer_income']:.2f}` টাকা\n"
            bot.send_message(call.message.chat.id, msg if sorted_ref else "⚠️ কোনো রেফারাল তথ্য পাওয়া যায়নি।", parse_mode="Markdown")

    elif call.data == "admin_top_worker":
        if user_id == ADMIN_ID:
            sorted_workers = sorted(users.items(), key=lambda x: x[1]['total_tasks'], reverse=True)[:5]
            msg = "🏆 *টপ ৫ ওয়ার্কার এর তালিকা:*\n\n"
            for idx, (u_id, u_info) in enumerate(sorted_workers, 1):
                msg += f"{idx}. 🆔 `{u_id}` | ⚙️ মোট কাজ: `{u_info['total_tasks']}` টি | 💰 ইনকাম: `{u_info['balance']:.2f}` টাকা\n"
            bot.send_message(call.message.chat.id, msg if sorted_workers else "⚠️ কোনো কাজের তথ্য পাওয়া যায়নি।", parse_mode="Markdown")

    elif call.data == "admin_reset_ref":
        if user_id == ADMIN_ID:
            for u in users.values():
                u['referrals'] = 0
                u['refer_income'] = 0.0
            bot.send_message(call.message.chat.id, "✅ *টপ রেফারার তালিকা সফলভাবে রিসেট করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_reset_worker":
        if user_id == ADMIN_ID:
            for u in users.values():
                u['total_tasks'] = 0
                u['today_tasks'] = 0
            bot.send_message(call.message.chat.id, "✅ *টপ ওয়ার্কার তালিকা সফলভাবে রিসেট করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_stock_info":
        if user_id == ADMIN_ID:
            bot.send_message(call.message.chat.id, f"📦 *ডাউনলোড স্টকে মোট রেডি আইডি:* `{len(download_stock)}` টি।", parse_mode="Markdown")

    elif call.data == "admin_stock_download":
        if user_id == ADMIN_ID:
            if not download_stock:
                bot.send_message(call.message.chat.id, "⚠️ ডাউনলোড স্টকে কোনো কাজ নেই!")
                return
            df = pd.DataFrame(download_stock)
            excel_path = "download_stock.xlsx"
            df[['username', 'password', '2fa_key']].to_excel(excel_path, index=False)
            with open(excel_path, 'rb') as doc:
                bot.send_document(call.message.chat.id, doc, caption="📥 *ডাউনলোড স্টক ফাইল (এক্সেল)*", parse_mode="Markdown")
            os.remove(excel_path)
            download_stock.clear()
            bot.send_message(call.message.chat.id, "🧹 *স্টক ডাউনলোড সম্পন্ন এবং ডাটা অটোমেটিক ক্লিন করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_custom_msg":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "✉️ যে ইউজারকে মেসেজ পাঠাতে চান তার **User ID** পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_target_user_for_msg)

    elif call.data == "admin_add_bal":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "💰 যে ইউজারের ব্যালেন্স এড করতে চান তার **User ID** পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_target_user_for_bal)

    elif call.data == "admin_set_rate":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "task_rate"
            bot.send_message(call.message.chat.id, f"💰 নতুন **টাস্ক রেট** (টাকা) লিখে পাঠান (বর্তমান: {settings['task_rate']}):", parse_mode="Markdown")

    elif call.data == "admin_set_withdraw":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "min_withdraw"
            bot.send_message(call.message.chat.id, f"💳 নতুন **মিনিমাম উইথড্র** এমাউন্ট লিখে পাঠান (বর্তমান: {settings['min_withdraw']}):", parse_mode="Markdown")

    elif call.data == "admin_set_ref_bonus":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "refer_bonus"
            bot.send_message(call.message.chat.id, f"🎁 নতুন **রেফার বোনাস** এমাউন্ট লিখে পাঠান (বর্তমান: {settings['refer_bonus']}):", parse_mode="Markdown")

    # FIXED: Broadcast to All Users Button
    elif call.data == "admin_broadcast":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📢 **সবাইকে যে মেসেজটি পাঠাতে চান তা লিখে পাঠান:**", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_broadcast_msg)

    elif call.data == "admin_upload_report_menu":
        if user_id == ADMIN_ID:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📊 Excel ফাইল আপলোড", callback_data="admin_upload_excel"),
                types.InlineKeyboardButton("📸 স্ক্রিনশট আপলোড", callback_data="admin_upload_ss")
            )
            bot.send_message(call.message.chat.id, "📤 **বায়ার রিপোর্ট আপলোড অপশন নির্বাচন করুন:**", parse_mode="Markdown", reply_markup=markup)

    elif call.data == "admin_upload_excel":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📊 বায়ার রিপোর্ট এক্সেল (.xlsx) ফাইলটি আপলোড করুন:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_excel_report)

    elif call.data == "admin_upload_ss":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📸 বায়ার রিপোর্টের স্ক্রিনশটটি পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_ss_report)

    # FIXED: Edit Buttons (Ref Message, Helpline Message, etc.)
    elif call.data == "admin_edit_ref_msg":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "ref_msg"
            bot.send_message(call.message.chat.id, "✍️ নতুন **রেফারাল মেসেজ** লিখে পাঠান:", parse_mode="Markdown")

    elif call.data == "admin_edit_help_msg":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "help_msg"
            bot.send_message(call.message.chat.id, "✍️ নতুন **হেল্পলাইন মেসেজ** লিখে পাঠান:", parse_mode="Markdown")

    elif call.data == "admin_edit_video":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "video_url"
            bot.send_message(call.message.chat.id, "✍️ সাপোর্ট গ্রুপের নতুন **ভিডিও পোস্ট লিংক** লিখে পাঠান:", parse_mode="Markdown")

    elif call.data.startswith("admin_edit_"):
        if user_id == ADMIN_ID:
            key = call.data.replace("admin_edit_", "")
            admin_states[user_id] = key
            bot.send_message(call.message.chat.id, f"✍️ **{key.upper()}** এর জন্য নতুন ইনপুট লিখে পাঠান:", parse_mode="Markdown")

# 2FA Validation Logic with 3-Attempt Limit
def process_2fa_key(message):
    user_id = message.from_user.id
    raw_key = message.text.strip().replace(" ", "")
    
    if user_id not in active_user_tasks:
        bot.send_message(message.chat.id, "⚠️ আপনার কাজটি ইতোমধ্যে বাতিল বা শেষ হয়ে গেছে।")
        return

    task_data = active_user_tasks[user_id]
    task_data['attempts'] = task_data.get('attempts', 0) + 1

    try:
        totp = pyotp.TOTP(raw_key)
        code = totp.now()
        
        if len(str(code)) == 6:
            task_data['temp_2fa'] = raw_key
            bot.send_message(
                message.chat.id,
                f"🔑 *2FA Key ভ্যালিড করা হয়েছে! (generated code: {code})*\n\n"
                "কাজটি নিশ্চিত করতে নিচে থাকা **কাজ জমা দিন** বাটনে ক্লিক করুন:",
                parse_mode="Markdown",
                reply_markup=build_submit_keyboard()
            )
            return
        else:
            raise ValueError("Invalid Key")
    except Exception:
        if task_data['attempts'] >= 3:
            active_user_tasks.pop(user_id, None)
            bot.send_message(message.chat.id, "❌ *পর পর ৩ বার ভুল 2FA Key দিয়েছেন!*\nআপনার বর্তমান কাজটি অটোমেটিক বাতিল করা হলো।", parse_mode="Markdown")
        else:
            msg = bot.send_message(
                message.chat.id, 
                f"❌ *অকার্যকর 2FA Key! (চেষ্টা: {task_data['attempts']}/৩)*\n"
                "দয়া করে সঠিক Secret Key টি আবার পাঠান:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_2fa_key)

# Admin Step Handlers
def process_broadcast_msg(message):
    success_count = 0
    fail_count = 0
    bot.send_message(message.chat.id, "⏳ ব্রডকাস্ট পাঠানো শুরু হয়েছে...")
    for u_id in list(users.keys()):
        try:
            bot.send_message(u_id, f"📢 *বিশেষ ঘোষণা:*\n\n{message.text}", parse_mode="Markdown")
            success_count += 1
            time.sleep(0.05)
        except Exception:
            fail_count += 1
    bot.send_message(message.chat.id, f"✅ *ব্রডকাস্ট সম্পন্ন!*\n\n🎯 সফল: `{success_count}` টি\n❌ ব্যর্থ: `{fail_count}` টি", parse_mode="Markdown")

def process_target_user_for_msg(message):
    try:
        target_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"📝 ID `{target_id}` এর জন্য বার্তাটি লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: send_custom_user_msg(m, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর ইউজার আইডি।")

def send_custom_user_msg(message, target_id):
    try:
        bot.send_message(target_id, f"📩 *এডমিন থেকে নতুন মেসেজ:*\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ মেসেজ সফলভাবে পাঠানো হয়েছে!")
    except Exception:
        bot.send_message(message.chat.id, "❌ মেসেজ পাঠানো সম্ভব হয়নি।")

def process_target_user_for_bal(message):
    try:
        target_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"💵 ID `{target_id}` এর ওয়ালেটে কত টাকা যোগ করতে চান?", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: add_user_bal(m, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর ইউজার আইডি।")

def add_user_bal(message, target_id):
    try:
        amount = float(message.text.strip())
        u_data = get_user_data(target_id)
        u_data['balance'] += amount
        bot.send_message(message.chat.id, f"✅ `{amount}` টাকা সফলভাবে যুক্ত করা হয়েছে!")
        try:
            bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে এডমিন কর্তৃক `{amount}` টাকা যোগ করা হয়েছে!", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর টাকার পরিমাণ।")

def process_excel_report(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ ফাইল পাওয়া যায়নি। এক্সেল (.xlsx) ফাইল পাঠান।")
        return
    bot.send_message(message.chat.id, "⏳ রিপোর্ট প্রসেসিং করা হচ্ছে...")

def process_ss_report(message):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ স্ক্রিনশট পাওয়া যায়নি।")
        return
    bot.send_message(message.chat.id, "✅ স্ক্রিনশট রিপোর্ট সফলভাবে গ্রহণ করা হয়েছে।")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

    # Admin Settings State Handler
    if user_id == ADMIN_ID and user_id in admin_states:
        state = admin_states.pop(user_id)
        try:
            if state == "task_rate": settings['task_rate'] = float(text)
            elif state == "min_withdraw": settings['min_withdraw'] = float(text)
            elif state == "refer_bonus": settings['refer_bonus'] = float(text)
            elif state == "welcome": settings['welcome_msg'] = text
            elif state == "rules": settings['rules_text'] = text
            elif state == "video_url": settings['video_url'] = text
            elif state == "ref_msg": settings['refer_msg'] = text
            elif state == "help_msg": settings['helpline_msg'] = text
            elif state == "channel": global SUPPORT_CHANNEL_LINK; SUPPORT_CHANNEL_LINK = text
            
            bot.send_message(message.chat.id, f"✅ *সাফল্যের সাথে `{state.upper()}` আপডেট করা হয়েছে!*", parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, "❌ অকার্যকর ইনপুট।")
        return

    if text == "🚀 কাজ শুরু করুন":
        if not settings['bot_active']:
            bot.send_message(message.chat.id, "🔴 বট বর্তমানে অফলাইনে আছে। পরবর্তীতে চেষ্টা করুন।")
            return
            
        username, password = generate_credentials()
        
        task_text = (
            "✨ *আপনার কাজের বিস্তারিত তথ্য নিচে দেওয়া হলো:* ✨\n\n"
            f"💰 **বর্তমান কাজের রেট:** `{settings['task_rate']:.2f}` টাকা\n"
            f"👤 **Username:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            "👉 ওপরের তথ্য দিয়ে একাউন্ট তৈরি করে **2FA Set** বাটনে চাপ দিন।"
        )
        msg_sent = bot.send_message(message.chat.id, task_text, parse_mode="Markdown", reply_markup=build_task_action_keyboard())
        
        active_user_tasks[user_id] = {
            'username': username, 
            'password': password,
            'task_msg_id': msg_sent.message_id,
            'attempts': 0
        }
        
        # 1-Hour Expiry Timer
        start_task_timer(user_id, message.chat.id)

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

    # NEW: Work Video Button with Direct Group Link
    elif text == "🎬 কাজ শেখার ভিডিও":
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("▶️ ভিডিও দেখতে এখানে ক্লিক করুন", url=settings['video_url'])
        markup.add(btn)
        
        bot.send_message(
            message.chat.id,
            "🎬 *কাজ শেখার জন্য নিচের বাটনে ক্লিক করুন এবং ভিডিও দেখুন:*",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif text == "🎁 রেফার করুন":
        u_data = get_user_data(user_id)
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        ref_text = (
            f"🎁 *রেফারেল সিস্টেম* 🎁\n\n"
            f"{settings['refer_msg']}\n\n"
            f"🔗 *আপনার রেফারেল লিংক:* \n`{ref_link}`\n\n"
            f"📊 *আপনার রেফারেল তথ্য:*\n"
            f"👥 **মোট রেফার করেছেন:** `{u_data['referrals']}` জন\n"
            f"💰 **রেফার থেকে মোট ইনকাম:** `{u_data['refer_income']:.2f}` টাকা\n\n"
            f"💡 প্রতি সফল রেফারে পাবেন `{settings['refer_bonus']:.2f}` টাকা (ইউজারের প্রথম কাজ জমা হওয়ার পর)!"
        )
        bot.send_message(message.chat.id, ref_text, parse_mode="Markdown")

    elif text == "🆘 হেল্পলাইন 📞":
        markup = types.InlineKeyboardMarkup()
        admin_link = f"https://t.me/{ADMIN_USERNAME.replace('@', '')}"
        markup.add(
            types.InlineKeyboardButton("👨‍💻 এডমিন সাপোর্ট", url=admin_link),
            types.InlineKeyboardButton("👥 সাপোর্ট গ্রুপ", url=SUPPORT_CHANNEL_LINK)
        )
        bot.send_message(message.chat.id, settings['helpline_msg'], parse_mode="Markdown", reply_markup=markup)

if __name__ == '__main__':
    print("🤖 Insta X Hub Bot Running...")
    bot.infinity_polling()
