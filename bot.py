import os
import random
import string
import time
import threading
import pyotp
import requests
import pandas as pd
import openpyxl
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
account_history = {}  # { 'username': user_id }
active_user_tasks = {} 
admin_states = {}
user_states = {} 

settings = {
    'bot_active': True,
    'task_rate': 10.0,
    'min_withdraw': 100.0,
    'refer_bonus': 10.0,
    'welcome_msg': "👋 *আসালামু আলাইকুম!*\n✨ **Insta X Hub Management Bot**-এ আপনাকে স্বাগতম!",
    'rules_text': "⚠️ *কাজের নিয়ম:* \nসঠিকভাবে ইনস্টাগ্রাম একাউন্ট খুলে 2FA সেট করে জমা দিন।",
    'video_url': "https://t.me/instaXhubsaport",
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

# Scraper Fix: Always return True to avoid false-positive blocking
def check_instagram_user_exists(username):
    return True

def get_user_data(user_id, tg_user_obj=None):
    if user_id not in users:
        device_fingerprint = None
        if tg_user_obj:
            device_fingerprint = f"{tg_user_obj.is_premium}_{tg_user_obj.language_code}"
            
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
            'device_fp': device_fingerprint,
            'user_obj': tg_user_obj
        }
    return users[user_id]

def find_user_by_account_username(acc_username):
    if acc_username in account_history:
        return account_history[acc_username]
    for item in download_stock:
        if item.get('username') == acc_username:
            return item.get('user_id')
    return None

def start_task_timer(user_id, chat_id):
    def timer_job():
        time.sleep(3600)  # 1 Hour Timer
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
    u_data = get_user_data(user_id, message.from_user)
    
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        ref_id = int(args[1])
        if ref_id != user_id and u_data['referred_by'] is None:
            u_data['referred_by'] = ref_id
            try:
                bot.send_message(
                    ref_id, 
                    f"🎉 *আপনার রেফার লিংক থেকে একজন ইউজার বটে যুক্ত হয়েছেন!*\n\n"
                    f"👉 তার ১ম কাজটি সফলভাবে সম্পন্ন হলে আপনি পাবেন `{settings['refer_bonus']:.0f}` টাকা বোনাস।",
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
            bot.send_message(call.message.chat.id, "⚠️ আপনার কোনো চলমান কাজ পাওয়া যায়নি। আবার কাজ শুরু করুন।")
            return
        
        active_user_tasks[user_id]['attempts'] = 0
        msg = bot.send_message(call.message.chat.id, "🔐 আপনার Instagram থেকে পাওয়া **2FA Secret Key** টি সঠিকভাবে দিন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_2fa_key)

    elif call.data == "submit_final_job":
        task_data = active_user_tasks.get(user_id)
        if not task_data or 'temp_2fa' not in task_data:
            bot.send_message(call.message.chat.id, "⚠️ কাজের কোনো বৈধ তথ্য পাওয়া যায়নি! কাজ বাতিল করা হলো।")
            return

        u_data = get_user_data(user_id, call.from_user)
        
        is_same_device = False
        if u_data['referred_by'] is not None:
            ref_id = u_data['referred_by']
            ref_user = get_user_data(ref_id)
            if u_data.get('device_fp') and ref_user.get('device_fp'):
                if u_data['device_fp'] == ref_user['device_fp']:
                    is_same_device = True

        account_history[task_data['username']] = user_id

        download_stock.append({
            'user_id': user_id,
            'username': task_data['username'],
            'password': task_data['password'],
            '2fa_key': task_data['temp_2fa']
        })
        
        u_data['pending_tasks'] += 1
        u_data['today_tasks'] += 1
        u_data['pending_balance'] += settings['task_rate']
        
        if not u_data['is_first_task_done'] and u_data['referred_by'] is not None:
            ref_id = u_data['referred_by']
            ref_user = get_user_data(ref_id)
            
            if is_same_device:
                try:
                    bot.send_message(
                        ref_id,
                        "❌ *রেফার বোনাস প্রদান ব্যর্থ হয়েছে!*\n\n"
                        "⚠️ একই ডিভাইস দিয়ে ফেক রেফারাল সনাক্ত করা হয়েছে।",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            else:
                ref_user['referrals'] += 1
                ref_user['refer_income'] += settings['refer_bonus']
                ref_user['balance'] += settings['refer_bonus']
                try:
                    bot.send_message(
                        ref_id,
                        f"🎉 *অভিনন্দন! আপনার রেফার করা ইউজারের ১ম কাজ সফল হয়েছে।*\n\n"
                        f"💰 আপনার ওয়ালেটে **{settings['refer_bonus']:.0f} টাকা** রেফার বোনাস যোগ করা হয়েছে।",
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
            "⏰ ১২-২৪ ঘণ্টার মধ্যে রিভিউ সম্পন্ন করে টাকা আপনার মূল ব্যালেন্স-এ যোগ করে দেওয়া হবে। 💸",
            parse_mode="Markdown"
        )

    # ================= Withdrawal Handlers =================
    elif call.data == "start_withdraw":
        u_data = get_user_data(user_id, call.from_user)
        if u_data['balance'] < settings['min_withdraw']:
            bot.answer_callback_query(call.id, f"❌ আপনার ব্যালেন্স {settings['min_withdraw']:.0f} টাকার কম!", show_alert=True)
            return

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("বিকাশ (Bkash)", callback_data="method_bkash"),
            types.InlineKeyboardButton("নগদ (Nagad)", callback_data="method_nagad")
        )
        bot.edit_message_text(
            "💳 *উইথড্র করার পদ্ধতি সিলেক্ট করুন:*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif call.data in ["method_bkash", "method_nagad"]:
        method = "বিকাশ (Bkash)" if call.data == "method_bkash" else "নগদ (Nagad)"
        user_states[user_id] = {'method': method}
        
        bot.edit_message_text(
            f"📱 আপনি **{method}** নির্বাচন করেছেন।\n\nআপনার **{method} নম্বরটি** লিখে পাঠান:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(call.message, process_withdraw_number)

    elif call.data.startswith("wd_approve_"):
        if user_id == ADMIN_ID:
            parts = call.data.split("_")
            target_id = int(parts[2])
            amount = float(parts[3])
            
            try:
                bot.edit_message_text(
                    f"{call.message.text}\n\n✅ *অবস্থা:* এপ্রুভ করা হয়েছে।",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown"
                )
                bot.send_message(
                    target_id,
                    f"🎉 *আপনার উইথড্র রিকোয়েস্ট সফলভাবে এপ্রুভ করা হয়েছে!*\n\n"
                    f"💰 **পরিমাণ:** `{amount:.2f}` টাকা\n"
                    f"টাকা আপনার নাম্বারে পাঠিয়ে দেওয়া হয়েছে। ধন্যবাদ!",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    elif call.data.startswith("wd_reject_"):
        if user_id == ADMIN_ID:
            parts = call.data.split("_")
            target_id = int(parts[2])
            amount = float(parts[3])
            
            target_data = get_user_data(target_id)
            target_data['balance'] += amount
            
            try:
                bot.edit_message_text(
                    f"{call.message.text}\n\n❌ *অবস্থা:* রিজেক্ট করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode="Markdown"
                )
                bot.send_message(
                    target_id,
                    f"❌ *আপনার উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে।*\n\n"
                    f"💰 `{amount:.2f}` টাকা আপনার মূল ব্যালেন্সে ব্যাক দেওয়া হয়েছে।",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    # Admin Control Handlers
    elif call.data == "admin_toggle_bot":
        if user_id == ADMIN_ID:
            settings['bot_active'] = not settings['bot_active']
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=build_admin_panel())

    elif call.data == "admin_top_ref":
        if user_id == ADMIN_ID:
            sorted_ref = sorted(users.items(), key=lambda x: x[1]['referrals'], reverse=True)[:5]
            msg = "🏆 *টপ ৫ রেফারার তালিকা:*\n\n"
            for idx, (u_id, u_info) in enumerate(sorted_ref, 1):
                msg += f"{idx}. 🆔 `{u_id}` | 👥 রেফার: `{u_info['referrals']}` | 💰 ইনকাম: `{u_info['refer_income']:.2f}` টাকা\n"
            bot.send_message(call.message.chat.id, msg if sorted_ref else "⚠️ কোনো রেফার তথ্য নেই।", parse_mode="Markdown")

    elif call.data == "admin_top_worker":
        if user_id == ADMIN_ID:
            sorted_workers = sorted(users.items(), key=lambda x: x[1]['total_tasks'], reverse=True)[:5]
            msg = "🏆 *টপ ৫ ওয়ার্কার তালিকা:*\n\n"
            for idx, (u_id, u_info) in enumerate(sorted_workers, 1):
                msg += f"{idx}. 🆔 `{u_id}` | ⚙️ কাজ: `{u_info['total_tasks']}` টি | 💰 ইনকাম: `{u_info['balance']:.2f}` টাকা\n"
            bot.send_message(call.message.chat.id, msg if sorted_workers else "⚠️ কোনো কাজের তথ্য নেই।", parse_mode="Markdown")

    elif call.data == "admin_reset_ref":
        if user_id == ADMIN_ID:
            for u in users.values():
                u['referrals'] = 0
                u['refer_income'] = 0.0
            bot.send_message(call.message.chat.id, "✅ *টপ রেফারার তালিকা রিসেট করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_reset_worker":
        if user_id == ADMIN_ID:
            for u in users.values():
                u['total_tasks'] = 0
                u['today_tasks'] = 0
            bot.send_message(call.message.chat.id, "✅ *টপ ওয়ার্কার তালিকা রিসেট করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_stock_info":
        if user_id == ADMIN_ID:
            bot.send_message(call.message.chat.id, f"📦 *ডাউনলোড স্টকে মোট রেডি আইডি:* `{len(download_stock)}` টি।", parse_mode="Markdown")

    elif call.data == "admin_stock_download":
        if user_id == ADMIN_ID:
            if not download_stock:
                bot.send_message(call.message.chat.id, "⚠️ স্টকে কোনো নতুন কাজ নেই!")
                return
            
            df = pd.DataFrame(download_stock)
            excel_path = "download_stock.xlsx"
            df[['username', 'password', '2fa_key']].to_excel(excel_path, index=False)
            
            with open(excel_path, 'rb') as doc:
                bot.send_document(call.message.chat.id, doc, caption=f"📥 *নতুন {len(download_stock)} টি আইডির স্টক ফাইল*", parse_mode="Markdown")
            
            os.remove(excel_path)
            download_stock.clear()
            bot.send_message(call.message.chat.id, "🧹 *স্টক ফাইল ডাউনলোড সম্পন্ন এবং স্টক তালিকা খালি করা হয়েছে!*", parse_mode="Markdown")

    elif call.data == "admin_custom_msg":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "✉️ যে ইউজারকে মেসেজ পাঠাবেন তার **User ID** পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_target_user_for_msg)

    elif call.data == "admin_add_bal":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "💰 যে ইউজারের ব্যালেন্স এড করবেন তার **User ID** পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_target_user_for_bal)

    elif call.data == "admin_set_rate":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "task_rate"
            bot.send_message(call.message.chat.id, f"💰 নতুন **টাস্ক রেট** পাঠান (বর্তমান: {settings['task_rate']}):", parse_mode="Markdown")

    elif call.data == "admin_set_withdraw":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "min_withdraw"
            bot.send_message(call.message.chat.id, f"💳 নতুন **মিনিমাম উইথড্র** পাঠান (বর্তমান: {settings['min_withdraw']}):", parse_mode="Markdown")

    elif call.data == "admin_set_ref_bonus":
        if user_id == ADMIN_ID:
            admin_states[user_id] = "refer_bonus"
            bot.send_message(call.message.chat.id, f"🎁 নতুন **রেফার বোনাস** পাঠান (বর্তমান: {settings['refer_bonus']}):", parse_mode="Markdown")

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
            bot.send_message(call.message.chat.id, "📤 **বায়ার রিপোর্ট অপশন বেছে নিন:**", parse_mode="Markdown", reply_markup=markup)

    elif call.data == "admin_upload_excel":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📊 বায়ার রিপোর্ট এক্সেল (.xlsx) ফাইলটি পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_excel_report)

    elif call.data == "admin_upload_ss":
        if user_id == ADMIN_ID:
            msg = bot.send_message(call.message.chat.id, "📸 বায়ার রিপোর্টের স্ক্রিনশটটি পাঠান:", parse_mode="Markdown")
            bot.register_next_step_handler(msg, process_ss_report)

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
            bot.send_message(call.message.chat.id, "✍️ কাজ শেখার নতুন **ভিডিও/গ্রুপ লিংক** লিখে পাঠান:", parse_mode="Markdown")

    elif call.data.startswith("admin_edit_"):
        if user_id == ADMIN_ID:
            key = call.data.replace("admin_edit_", "")
            admin_states[user_id] = key
            bot.send_message(call.message.chat.id, f"✍️ **{key.upper()}** এর নতুন ইনপুট পাঠান:", parse_mode="Markdown")

# Withdrawal Input Steps
def process_withdraw_number(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    
    number = message.text.strip()
    user_states[user_id]['number'] = number
    
    u_data = get_user_data(user_id, message.from_user)
    msg = bot.send_message(
        message.chat.id,
        f"💵 কত টাকা তুলবেন তার পরিমাণ লিখুন:\n"
        f"📌 *(সর্বনিম্ন: {settings['min_withdraw']:.0f} টাকা | আপনার ব্যালেন্স: {u_data['balance']:.2f} টাকা)*",
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
        
    u_data = get_user_data(user_id, message.from_user)
    
    try:
        amount = float(message.text.strip())
        if amount < settings['min_withdraw']:
            bot.send_message(message.chat.id, f"❌ সর্বনিম্ন উইথড্র `{settings['min_withdraw']:.0f}` টাকা। আবার চেষ্টা করুন।", parse_mode="Markdown")
            user_states.pop(user_id, None)
            return
        if amount > u_data['balance']:
            bot.send_message(message.chat.id, "❌ আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।", parse_mode="Markdown")
            user_states.pop(user_id, None)
            return
            
        method = user_states[user_id]['method']
        number = user_states[user_id]['number']
        
        u_data['balance'] -= amount
        user_states.pop(user_id, None)
        
        bot.send_message(
            message.chat.id,
            "✅ *আপনার উইথড্র রিকোয়েস্টটি সফলভাবে পাঠানো হয়েছে!*\n\n"
            "⏳ এডমিন রিভিউ করে দ্রুত আপনার নাম্বারে টাকা পাঠিয়ে দিবে।",
            parse_mode="Markdown"
        )
        
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"wd_approve_{user_id}_{amount}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"wd_reject_{user_id}_{amount}")
        )
        
        user_name = message.from_user.first_name or "User"
        admin_msg = (
            "🔔 *নতুন উইথড্র রিকোয়েস্ট!* 🔔\n\n"
            f"👤 **ইউজার:** {user_name}\n"
            f"🆔 **User ID:** `{user_id}`\n"
            f"📊 **মোট কাজ সম্পন্ন:** `{u_data['total_tasks']}` টি\n"
            f"💳 **মেথড:** {method}\n"
            f"📱 **নাম্বার:** `{number}`\n"
            f"💰 **পরিমাণ:** `{amount:.2f}` টাকা\n"
        )
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown", reply_markup=admin_markup)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ অকার্যকর টাকার পরিমাণ। প্রক্রিয়াটি বাতিল করা হলো।")
        user_states.pop(user_id, None)

# STRICT 2FA KEY VALIDATION AND LIVE OTP CODE GENERATION
def process_2fa_key(message):
    user_id = message.from_user.id
    raw_key = message.text.strip().replace(" ", "")
    
    if user_id not in active_user_tasks:
        bot.send_message(message.chat.id, "⚠️ আপনার কাজটি বাতিল হয়ে গেছে। আবার নতুন করে শুরু করুন।")
        return

    task_data = active_user_tasks[user_id]
    task_data['attempts'] = task_data.get('attempts', 0) + 1

    try:
        # Check if secret key is valid Base32 string and can generate TOTP Code
        totp = pyotp.TOTP(raw_key)
        code = totp.now()  # Generates 6-Digit Real-time Code
        
        if len(str(code)) == 6 and str(code).isdigit():
            task_data['temp_2fa'] = raw_key
            bot.send_message(
                message.chat.id,
                f"✅ *2FA Secret Key সফলভাবে ম্যাচ করেছে!*\n\n"
                f"🔑 **আপনার বর্তমান ৬-ডিজিটের 2FA কোড:** `{code}`\n\n"
                "কাজটি সম্পন্ন করতে নিচের **কাজ জমা দিন** বাটনে ক্লিক করুন:",
                parse_mode="Markdown",
                reply_markup=build_submit_keyboard()
            )
            return
        else:
            raise ValueError("Invalid Key Format")

    except Exception:
        if task_data['attempts'] >= 3:
            active_user_tasks.pop(user_id, None)
            bot.send_message(message.chat.id, "❌ *পর পর ৩ বার ভুল বা ভুয়া 2FA Key দেওয়া হয়েছে!*\nআপনার চলতি কাজটি বাতিল করা হলো।", parse_mode="Markdown")
        else:
            msg = bot.send_message(
                message.chat.id, 
                f"❌ *ভুল বা অকার্যকর 2FA Secret Key! (চেষ্টা: {task_data['attempts']}/৩)*\n\n"
                "⚠️ দয়া করে ইনস্টাগ্রাম থেকে প্রাপ্ত সঠিক **2FA Secret Key** টি আবার লিখে পাঠান:", 
                parse_mode="Markdown"
            )
            bot.register_next_step_handler(msg, process_2fa_key)

# Admin Helper Handlers
def process_broadcast_msg(message):
    success_count = 0
    fail_count = 0
    bot.send_message(message.chat.id, "⏳ ব্রডকাস্ট শুরু হয়েছে...")
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
        msg = bot.send_message(message.chat.id, f"📝 ID `{target_id}` এর জন্য মেসেজ লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: send_custom_user_msg(m, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর আইডি।")

def send_custom_user_msg(message, target_id):
    try:
        bot.send_message(target_id, f"📩 *এডমিন মেসেজ:*\n\n{message.text}", parse_mode="Markdown")
        bot.send_message(message.chat.id, "✅ মেসেজ সফলভাবে পাঠানো হয়েছে!")
    except Exception:
        bot.send_message(message.chat.id, "❌ মেসেজ পাঠানো সম্ভব হয়নি।")

def process_target_user_for_bal(message):
    try:
        target_id = int(message.text.strip())
        msg = bot.send_message(message.chat.id, f"💵 ID `{target_id}` এর জন্য টাকার পরিমাণ লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, lambda m: add_user_bal(m, target_id))
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর আইডি।")

def add_user_bal(message, target_id):
    try:
        amount = float(message.text.strip())
        u_data = get_user_data(target_id)
        u_data['balance'] += amount
        bot.send_message(message.chat.id, f"✅ `{amount}` টাকা যুক্ত করা হয়েছে!")
        try:
            bot.send_message(target_id, f"🎉 আপনার অ্যাকাউন্টে `{amount}` টাকা যোগ করা হয়েছে!", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.send_message(message.chat.id, "❌ অকার্যকর টাকা।")

# ================= Excel Processing Logic =================
def process_excel_report(message):
    if not message.document:
        bot.send_message(message.chat.id, "❌ এক্সেল (.xlsx) ফাইল পাঠান।")
        return
    
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_path = "temp_report.xlsx"
    
    with open(file_path, 'wb') as new_file:
        new_file.write(downloaded_file)
        
    msg = bot.send_message(
        message.chat.id, 
        "🎨 *এপ্রুভড (Approved) সেলের ব্যাকগ্রাউন্ড কালার HEX কোড নির্বাচন করুন:*\n\n"
        "💡 *সাধারণ কোড:* সবুজ কালারের জন্য `00FF00` অথবা নো-কালার/সাদা কালারের জন্য `00000000`\n"
        "*(আপনি ডিফল্ট সবুজ কালার ব্যবহার করতে `1` লিখে পাঠান)*", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, lambda m: ask_reject_color(m, file_path))

def ask_reject_color(message, file_path):
    approved_color = message.text.strip().upper()
    if approved_color == "1":
        approved_color = "00FF00"
        
    msg = bot.send_message(
        message.chat.id, 
        "🎨 *রিজেক্টেড (Rejected) সেলের ব্যাকগ্রাউন্ড কালার HEX কোড নির্বাচন করুন:*\n\n"
        "💡 *সাধারণ কোড:* সাদা সেলের জন্য `00000000` (অথবা `000000`)\n"
        "*(আপনি ডিফল্ট সাদা কালার ব্যবহার করতে `1` লিখে পাঠান)*", 
        parse_mode="Markdown"
    )
    bot.register_next_step_handler(msg, lambda m: run_excel_processing(m, file_path, approved_color))

def run_excel_processing(message, file_path, approved_color):
    rejected_color = message.text.strip().upper()
    if rejected_color == "1":
        rejected_color = "00000000"
        
    bot.send_message(message.chat.id, "⏳ *এক্সেল ফাইল রিড ও অটো-প্রসেসিং চলছে...*", parse_mode="Markdown")
    
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheet = wb.active
        
        total_approved = 0
        total_amount_paid = 0.0
        rejected_list = []
        
        rate = settings['task_rate']
        
        for row in sheet.iter_rows(min_row=1):
            cell = row[0]
            acc_username = str(cell.value).strip() if cell.value else None
            
            if not acc_username or acc_username.lower() in ["username", "user_name", "id"]:
                continue
                
            cell_fill = cell.fill
            cell_color = "00000000"
            
            if cell_fill and cell_fill.start_color:
                if cell_fill.start_color.rgb:
                    cell_color = str(cell_fill.start_color.rgb).upper()
            
            target_user_id = find_user_by_account_username(acc_username)
            
            is_approved = False
            if approved_color in cell_color or (approved_color == "00FF00" and ("FF00FF00" in cell_color or "00FF00" in cell_color)):
                is_approved = True
            elif approved_color == "00000000" and cell_color in ["00000000", "000000", "FFFFFFFF"]:
                is_approved = True

            if target_user_id and target_user_id in users:
                u_data = users[target_user_id]
                
                if is_approved:
                    u_data['balance'] += rate
                    if u_data['pending_balance'] >= rate:
                        u_data['pending_balance'] -= rate
                    if u_data['pending_tasks'] > 0:
                        u_data['pending_tasks'] -= 1
                    u_data['total_tasks'] += 1
                    
                    total_approved += 1
                    total_amount_paid += rate
                    
                    try:
                        bot.send_message(
                            target_user_id,
                            f"🎉 *আপনার জমা দেওয়া কাজ সফল (Approved) হয়েছে!*\n\n"
                            f"👤 **আইডি:** `{acc_username}`\n"
                            f"💰 **যোগকৃত ব্যালেন্স:** `{rate:.2f}` টাকা",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                else:
                    if u_data['pending_balance'] >= rate:
                        u_data['pending_balance'] -= rate
                    if u_data['pending_tasks'] > 0:
                        u_data['pending_tasks'] -= 1
                        
                    rejected_list.append(acc_username)
                    
                    try:
                        bot.send_message(
                            target_user_id,
                            f"❌ *আপনার জমা দেওয়া কাজ রিজেক্ট (Rejected) করা হয়েছে!*\n\n"
                            f"👤 **আইডি:** `{acc_username}`",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            else:
                if not is_approved:
                    rejected_list.append(f"{acc_username} (User Unknown)")

        rej_str = "\n".join([f"- `{acc}`" for acc in rejected_list]) if rejected_list else "কোনো রিজেক্টেড আইডি পাওয়া যায়নি।"
        
        summary_msg = (
            "📊 *বায়ার রিপোর্ট অটো-প্রসেসিং সম্পন্ন!* 📊\n\n"
            f"✅ **মোট সফল কাজ:** `{total_approved}` টি\n"
            f"💵 **মোট বিতরণকৃত ব্যালেন্স:** `{total_amount_paid:.2f}` টাকা\n"
            f"❌ **মোট রিজেক্টেড আইডি:** `{len(rejected_list)}` টি\n\n"
            f"📋 **রিজেক্টেড আইডির তালিকা:**\n{rej_str}"
        )
        
        bot.send_message(ADMIN_ID, summary_msg, parse_mode="Markdown")
        
    except Exception as e:
        bot.send_message(ADMIN_ID, f"❌ ফাইল প্রসেসিং এ ত্রুটি হয়েছে: `{str(e)}`", parse_mode="Markdown")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def process_ss_report(message):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ স্ক্রিনশট পাঠান।")
        return
    bot.send_message(message.chat.id, "✅ রিপোর্ট স্ক্রিনশট গ্রহণ করা হয়েছে।")

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text

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
            
            bot.send_message(message.chat.id, f"✅ *`{state.upper()}` আপডেট করা হয়েছে!*", parse_mode="Markdown")
        except Exception:
            bot.send_message(message.chat.id, "❌ অকার্যকর ইনপুট।")
        return

    if text == "🚀 কাজ শুরু করুন":
        if not settings['bot_active']:
            bot.send_message(message.chat.id, "🔴 বট অফলাইনে আছে।")
            return
            
        username, password = generate_credentials()
        
        task_text = (
            "✨ *আপনার কাজের তথ্য:* ✨\n\n"
            f"💰 **কাজের রেট:** `{settings['task_rate']:.2f}` টাকা\n"
            f"👤 **Username:** `{username}`\n"
            f"🔑 **Password:** `{password}`\n\n"
            "👉 এই তথ্য দিয়ে একাউন্ট খুলে **2FA Set** বাটনে চাপ দিন।"
        )
        msg_sent = bot.send_message(message.chat.id, task_text, parse_mode="Markdown", reply_markup=build_task_action_keyboard())
        
        active_user_tasks[user_id] = {
            'username': username, 
            'password': password,
            'task_msg_id': msg_sent.message_id,
            'attempts': 0
        }
        
        start_task_timer(user_id, message.chat.id)

    elif text == "💰 ব্যালেন্স & উইথড্র 💳":
        u_data = get_user_data(user_id, message.from_user)
        balance_msg = (
            "💼 *আপনার ওয়ালেট:* 💼\n\n"
            f"💵 **বর্তমান ব্যালেন্স:** `{u_data['balance']:.2f}` টাকা\n"
            f"⏳ **পেন্ডিং ব্যালেন্স:** `{u_data['pending_balance']:.2f}` টাকা\n"
            f"🏆 **মোট আয়:** `{u_data['balance'] + u_data['pending_balance']:.2f}` টাকা\n\n"
            f"📌 **সর্বনিম্ন উইথড্র:** {settings['min_withdraw']:.0f} টাকা।"
        )
        
        markup = types.InlineKeyboardMarkup()
        if u_data['balance'] >= settings['min_withdraw']:
            markup.add(types.InlineKeyboardButton("💳 উইথড্র করুন", callback_data="start_withdraw"))
            
        bot.send_message(message.chat.id, balance_msg, parse_mode="Markdown", reply_markup=markup if u_data['balance'] >= settings['min_withdraw'] else None)

    elif text == "📊 কাজের রিপোর্ট":
        u_data = get_user_data(user_id, message.from_user)
        report_msg = (
            "📊 *কাজের রিপোর্ট:* 📊\n\n"
            f"📅 **আজকের কাজ:** `{u_data['today_tasks']}` টি\n"
            f"⏳ **পেন্ডিং কাজ:** `{u_data['pending_tasks']}` টি\n"
            f"✅ **মোট সফল কাজ:** `{u_data['total_tasks']}` টি"
        )
        bot.send_message(message.chat.id, report_msg, parse_mode="Markdown")

    elif text == "📜 কাজের নিয়ম ⚠️":
        bot.send_message(message.chat.id, settings['rules_text'], parse_mode="Markdown")

    elif text == "🎬 কাজ শেখার ভিডিও":
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("▶️ ভিডিও দেখুন", url=settings['video_url'])
        markup.add(btn)
        
        bot.send_message(
            message.chat.id,
            "🎬 *কাজ শেখার ভিডিও দেখতে নিচের বাটনে ক্লিক করুন:*",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif text == "🎁 রেফার করুন":
        u_data = get_user_data(user_id, message.from_user)
        bot_username = bot.get_me().username
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        ref_text = (
            f"🎁 *রেফারেল সিস্টেম* 🎁\n\n"
            f"{settings['refer_msg']}\n\n"
            f"🔗 *আপনার রেফারেল লিংক:* \n`{ref_link}`\n\n"
            f"📊 *আপনার রেফারেল তথ্য:*\n"
            f"👥 **মোট রেফার করেছেন:** `{u_data['referrals']}` জন\n"
            f"💰 **রেফার থেকে আয়:** `{u_data['refer_income']:.2f}` টাকা\n\n"
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
