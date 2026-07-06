import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"
FB_GROUP_URL = "https://www.facebook.com/share/g/1FChgcyZrp/"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ সেটআপ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def get_stock_text():
    cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
    res = cursor.fetchall()
    if not res: return "📦 বর্তমানে স্টক খালি!"
    return "📦 বর্তমান স্টক:\n" + "\n".join([f"🔹 {r[0]}: {r[1]} টি" for r in res])

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID: markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("👥 ফেসবুক গ্রুপে জয়েন করুন", url=FB_GROUP_URL))
        markup.add(types.InlineKeyboardButton("🔑 ভেরিফাই", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেল ও গ্রুপে জয়েন করুন!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id): return
    text = message.text.strip()

    if text == '🛒 জিমেইল কিনুন':
        stock_info = get_stock_text()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, f"{stock_info}\n\n📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        price = 35 if cat == 'Old' else 32
        cursor.execute("SELECT COUNT(*) FROM emails WHERE category=? AND status='available'", (cat,))
        count = cursor.fetchone()[0]
        if count == 0: bot.send_message(message.chat.id, "❌ দুঃখিত, এই ক্যাটাগরিতে স্টক নেই।")
        else:
            bot.send_message(message.chat.id, f"✅ স্টকে {count} টি আছে। কয়টি নিতে চান?")
            bot.register_next_step_handler(message, ask_payment_info, cat, price)

    elif text == '💰 জিমেইল বেচুন':
        # চ্যানেল প্রমোশন মেসেজ
        bot.send_message(message.chat.id, "📢 আপনারা একটু কষ্ট করে আমাদের চ্যানেল ঘুরে দেখতে পারেন: https://t.me/gmailbuyer1122 ✨")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "💰 কোন ক্যাটাগরির জিমেইল বেচতে চান? রেট দেওয়া আছে:", reply_markup=markup)

    elif text in ['পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)']:
        cat = 'Old' if '২৫' in text else 'New'
        price = 25 if cat == 'Old' else 22
        bot.send_message(message.chat.id, f"আপনি {cat} জিমেইল বেচতে চাচ্ছেন (প্রতিটি {price} টাকা)। কয়টি জিমেইল বেচতে চান?")
        bot.register_next_step_handler(message, ask_gmail_credentials, cat)

    elif text == '📢 চ্যানেল':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 আমাদের চ্যানেলে জয়েন করুন", url=CHANNEL_URL))
        bot.send_message(message.chat.id, "নিচের বাটনে ক্লিক করে আমাদের চ্যানেলে যুক্ত হোন:", reply_markup=markup)
    elif text == '📞 যোগাযোগ':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📩 আমার সাথে যোগাযোগ করুন", url="https://t.me/AK_A_SH_002"))
        bot.send_message(message.chat.id, "যেকোনো প্রয়োজনে সরাসরি যোগাযোগ করুন:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ জিমেইল যোগ", callback_data='admin_add'),
                   types.InlineKeyboardButton("➖ জিমেইল রিমুভ", callback_data='admin_remove'))
        markup.add(types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'),
                   types.InlineKeyboardButton("👥 ইউজার সংখ্যা", callback_data='admin_users'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)

def ask_payment_info(message, cat, price):
    try:
        qty = int(message.text)
        total = qty * price
        bot.send_message(message.chat.id, f"মোট: {total} টাকা।\nবিকাশ: 01762921053\n⚠️ পেমেন্ট করার পর আপনার বিকাশ নাম্বার ও TrxID লিখে পাঠান, নাহলে এপ্রুভ হবে না।")
        bot.register_next_step_handler(message, lambda m: finalize_buy_order(m, cat, qty, total))
    except: bot.send_message(message.chat.id, "❌ শুধু সংখ্যা লিখুন!")

def finalize_buy_order(message, cat, qty, total):
    if len(message.text) < 5:
        bot.send_message(message.chat.id, "❌ ভুল তথ্য! অনুগ্রহ করে সঠিক TrxID ও বিকাশ নাম্বার দিন।")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"approve_{message.chat.id}_{qty}_{cat}_{total}"))
    bot.send_message(ADMIN_ID, f"🔔 নতুন পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nডিটেইলস: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ আপনার পেমেন্ট রিকোয়েস্টটি যাচাইয়ের জন্য পাঠানো হয়েছে।")

def ask_gmail_credentials(message, cat):
    qty = message.text
    bot.send_message(message.chat.id, "জিমেইল এবং পাসওয়ার্ড পাঠান:")
    bot.register_next_step_handler(message, lambda m: ask_payment_method(m, cat, qty, m.text))

def ask_payment_method(message, cat, qty, creds):
    bot.send_message(message.chat.id, "আপনার পেমেন্ট নাম্বার দিন:")
    bot.register_next_step_handler(message, lambda m: finish_sell_order(m, cat, qty, creds, m.text))

def finish_sell_order(message, cat, qty, creds, p_num):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"sell_approve_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} {cat}\nতথ্য: {creds}\nপেমেন্ট: {p_num}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else: bot.answer_callback_query(call.id, "❌ চ্যানেল জয়েন করেননি!", show_alert=True)
    elif call.data.startswith('approve_'):
        data = call.data.split('_')
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (data[3], int(data[2])))
        rows = cursor.fetchall()
        if len(rows) < int(data[2]): bot.send_message(ADMIN_ID, "❌ স্টক শেষ!")
        else:
            msg = "✅ ডেলিভারি:\n" + "\n".join([f"📧 {r[1]} | 🔑 {r[2]}" for r in rows])
            for r in rows: cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (r[0],))
            conn.commit()
            bot.send_message(data[1], msg)
            bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
    elif call.data.startswith('sell_approve_'):
        bot.send_message(call.data.split('_')[2], "🎉 পেমেন্ট সফল, ধন্যবাদ!")
        bot.edit_message_text("✅ এপ্রুভড!", ADMIN_ID, call.message.message_id)
    elif call.data == 'admin_stock': bot.send_message(call.message.chat.id, get_stock_text())
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email Pass Category Price")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", m.text.split()), conn.commit(), bot.reply_to(m, "✅ যুক্ত হয়েছে!")])
    elif call.data == 'admin_remove':
        bot.send_message(call.message.chat.id, "রিমুভ করতে জিমেইলটি লিখুন:")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("DELETE FROM emails WHERE email=?", (m.text.strip(),)), conn.commit(), bot.reply_to(m, "✅ রিমুভড!")])
    elif call.data == 'admin_users':
        cursor.execute("SELECT COUNT(*) FROM users")
        bot.send_message(call.message.chat.id, f"👥 মোট ইউজার: {cursor.fetchone()[0]}")

bot.infinity_polling()
