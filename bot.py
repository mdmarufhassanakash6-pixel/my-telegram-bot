import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = 8357226129 
CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"
FB_GROUP_URL = "https://www.facebook.com/share/g/1FChgcyZrp/"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ সেটআপ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# --- হেল্পার ফাংশন ---
def is_subscribed(user_id):
    try: return bot.get_chat_member(CHANNEL_ID, user_id).status in ['member', 'administrator', 'creator']
    except: return False

def get_stock_text():
    cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
    res = cursor.fetchall()
    return "📦 বর্তমান স্টক:\n" + "\n".join([f"🔹 {r[0]}: {r[1]} টি" for r in res]) if res else "📦 স্টক খালি!"

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID: markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! অপশন বেছে নিন:", reply_markup=markup)

# --- হ্যান্ডলারসমূহ ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেল", url=CHANNEL_URL), types.InlineKeyboardButton("👥 ফেসবুক গ্রুপ", url=FB_GROUP_URL))
        markup.add(types.InlineKeyboardButton("🔑 ভেরিফাই", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য জয়েন করুন!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id): return
    text = message.text.strip()

    if text == '🛒 জিমেইল কিনুন':
        bot.send_message(message.chat.id, f"{get_stock_text()}\n\nক্যাটাগরি সিলেক্ট করুন:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row('পুরানো জিমেইল (৩৫ টাকা)').row('🏠 মেইন মেনু'))
    elif text == 'পুরানো জিমেইল (৩৫ টাকা)':
        bot.send_message(message.chat.id, "কয়টি নিতে চান এবং পেমেন্ট আইডি (TrxID) দিন (সংখ্যা:ID):")
        bot.register_next_step_handler(message, finalize_buy)
    elif text == '💰 জিমেইল বেচুন':
        bot.send_message(message.chat.id, "জিমেইল:পাসওয়ার্ড ফরম্যাটে দিন:")
        bot.register_next_step_handler(message, process_sell)
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("➕ জিমেইল যোগ", callback_data='admin_add'),
            types.InlineKeyboardButton("➖ জিমেইল রিমুভ", callback_data='admin_remove'),
            types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'),
            types.InlineKeyboardButton("👥 ইউজার সংখ্যা", callback_data='admin_users')
        )
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

# --- লজিক ---
def finalize_buy(message):
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"buy_app_{message.chat.id}_{message.text}"),
        types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"can_{message.chat.id}")
    )
    bot.send_message(ADMIN_ID, f"🔔 ক্রয় রিকোয়েস্ট!\nইউজার: {message.chat.id}\nডিটেইলস: {message.text}", reply_markup=markup)
    bot.reply_to(message, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

def process_sell(message):
    try:
        email, password = message.text.split(':')
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"sell_app_{message.chat.id}_{email}_{password}"),
            types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"can_{message.chat.id}")
        )
        bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nতথ্য: {email}:{password}", reply_markup=markup)
        bot.reply_to(message, "✅ জিমেইল জমা হয়েছে, অ্যাডমিন এপ্রুভ করলে স্টকে আসবে।")
    except: bot.reply_to(message, "❌ ভুল ফরম্যাট! Email:Password দিন।")

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    data = call.data.split('_')
    if call.data.startswith('buy_app_'):
        cursor.execute("SELECT id, email, password FROM emails WHERE category='Old' AND status='available' LIMIT 1")
        row = cursor.fetchone()
        if row:
            bot.send_message(data[2], f"✅ ডেলিভারি: {row[1]} | {row[2]}")
            cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (row[0],))
            conn.commit()
            bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ স্টক শেষ!")
    elif call.data.startswith('sell_app_'):
        try:
            cursor.execute("INSERT INTO emails (email, password, category, status) VALUES (?, ?, 'Old', 'available')", (data[3], data[4]))
            conn.commit()
            bot.edit_message_text("✅ এপ্রুভড! জিমেইল স্টকে যোগ হয়েছে।", ADMIN_ID, call.message.message_id)
        except: bot.answer_callback_query(call.id, "❌ ডুপ্লিকেট জিমেইল!")
    elif call.data.startswith('can_'):
        bot.send_message(data[1], "❌ আপনার রিকোয়েস্ট ক্যানসেল করা হয়েছে।")
        bot.edit_message_text("❌ ক্যানসেলড!", ADMIN_ID, call.message.message_id)
    elif call.data == 'admin_stock':
        bot.send_message(ADMIN_ID, get_stock_text())
    elif call.data == 'admin_add':
        bot.send_message(ADMIN_ID, "ফরম্যাট: Email:Password")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT INTO emails (email, password, category, status) VALUES (?, ?, 'Old', 'available')", m.text.split(':')), conn.commit(), bot.reply_to(m, "✅ যুক্ত হয়েছে!")])
    elif call.data == 'admin_remove':
        bot.send_message(ADMIN_ID, "রিমুভ করতে জিমেইলটি লিখুন:")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("DELETE FROM emails WHERE email=?", (m.text.strip(),)), conn.commit(), bot.reply_to(m, "✅ রিমুভড!")])
    elif call.data == 'admin_users':
        cursor.execute("SELECT COUNT(*) FROM users")
        bot.send_message(ADMIN_ID, f"👥 মোট ইউজার: {cursor.fetchone()[0]}")

bot.infinity_polling()
