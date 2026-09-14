# ==================== START COMMAND & JOIN FLOW ====================
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

💼 আমাদের বটে ইনস্টাগ্রাম একাউন্ট ক্রিয়েট করে আপনি খুব সহজেই প্রতিদিন চমৎকার ইনকাম করতে পারবেন। এটি একটি ১০০% অটোমেটেড ও বিশ্বস্ত প্ল্যাটফর্ম।

👉 **কাজ শুরু করতে নিচের '▶️ Start 🚀' বাটনে ক্লিক করুন!**"""

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("▶️ Start 🚀", callback_data="click_start"))
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "click_start")
def process_start_click(call):
    user_id = call.from_user.id
    
    if check_mandatory_join(user_id):
        bot.send_message(user_id, "🎉 **ধন্যবাদ আমাদের সঙ্গে যুক্ত হওয়ার জন্য এবং এখন আপনি স্বাভাবিকভাবে কাজ করতে পারবেন।** 👇", reply_markup=main_menu(), parse_mode="Markdown")
    else:
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
        bot.send_message(user_id, "🎉 **ধন্যবাদ আমাদের সঙ্গে যুক্ত হওয়ার জন্য এবং এখন আপনি স্বাভাবিকভাবে কাজ করতে পারবেন।** 👇", reply_markup=main_menu(), parse_mode="Markdown")
    else:
        bot.answer_callback_query(call.id, "⚠️ দয়া করে আগে আমাদের সাপোর্ট গ্রুপে জয়েন হন তারপরে কাজ শুরু করুন", show_alert=True)
