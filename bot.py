import os
import telebot
from telebot import types
import sqlite3

# কনফিগারেশন
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ সেটআপ (ইমেইল ইউনিক করা হয়েছে)
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# --- হেল্পার ফাংশন ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return False

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID: markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! অপশনটি বেছে নিন:", reply_markup=markup)

# --- হ্যান্ডলারসমূহ ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 জয়েন করুন", url=CHANNEL_URL), types.InlineKeyboardButton("🔑 ভেরিফাই", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেলে জয়েন করুন!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id): return
    text = message.text.strip()

    if text == '🛒 জিমেইল কিনুন':
        bot.send_message(message.chat.id, "ক্যাটাগরি সিলেক্ট করুন:", reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)').row('🏠 মেইন মেনু'))
    
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        bot.send_message(message.chat.id, "কয়টি নিতে চান?")
        bot.register_next_step_handler(message, lambda m: ask_payment(m, cat))

    elif text == '💰 জিমেইল বেচুন':
        bot.send_message(message.chat.id, "জিমেইল:পাসওয়ার্ড ফরম্যাটে দিন:")
        bot.register_next_step_handler(message, lambda m: process_sell(m))

    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("➕ জিমেইল যোগ", callback_data='admin_add'), types.InlineKeyboardButton("➖ রিমুভ", callback_data='admin_remove'))
        bot.send_message(message.chat.id, "অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

# --- বাই ও সেল প্রসেসিং ---
def ask_payment(message, cat):
    bot.send_message(message.chat.id, "বিকাশ নাম্বার ও TrxID দিন:")
    bot.register_next_step_handler(message, lambda m: send_to_admin_buy(m, cat))

def send_to_admin_buy(message, cat):
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"buy_app_{message.chat.id}_{cat}"),
        types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"buy_can_{message.chat.id}")
    )
    bot.send_message(ADMIN_ID, f"🔔 ক্রয় রিকোয়েস্ট!\nইউজার: {message.chat.id}\nডিটেইলস: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

def process_sell(message):
    try:
        email, password = message.text.split(':')
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"sell_app_{message.chat.id}_{email}_{password}"),
            types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"sell_can_{message.chat.id}")
        )
        bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nতথ্য: {email}:{password}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ জিমেইলটি আমাদের কাছে জমা হয়েছে, চেক করার পর এপ্রুভ করা হবে।")
    except: bot.send_message(message.chat.id, "❌ ভুল ফরম্যাট! Email:Password ফরম্যাটে লিখুন।")

# --- কলব্যাক হ্যান্ডলার (এপ্রুভ/ক্যানসেল) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split('_')
    
    # কেনার এপ্রুভাল
    if call.data.startswith('buy_app_'):
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT 1", (data[3],))
        row = cursor.fetchone()
        if row:
            bot.send_message(data[2], f"✅ আপনার জিমেইল: {row[1]} | {row[2]}")
            cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (row[0],))
            conn.commit()
            bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
        else: bot.answer_callback_query(call.id, "❌ স্টক শেষ!")

    # সেল এপ্রুভাল (ডুপ্লিকেট চেকসহ)
    elif call.data.startswith('sell_app_'):
        try:
            cursor.execute("INSERT INTO emails (email, password, category, status) VALUES (?, ?, 'Old', 'available')", (data[3], data[4]))
            conn.commit()
            bot.send_message(data[2], "🎉 পেমেন্ট সফল, জিমেইল স্টকে যোগ হয়েছে!")
            bot.edit_message_text("✅ এপ্রুভড!", ADMIN_ID, call.message.message_id)
        except sqlite3.IntegrityError:
            bot.answer_callback_query(call.id, "❌ এই জিমেইলটি অলরেডি স্টকে আছে!")
            
    elif call.data.startswith('buy_can_') or call.data.startswith('sell_can_'):
        bot.send_message(data[2], "❌ দুঃখিত, আপনার রিকোয়েস্টটি ক্যানসেল করা হয়েছে।")
        bot.edit_message_text("❌ ক্যানসেল করা হয়েছে!", ADMIN_ID, call.message.message_id)
    
    elif call.data == 'admin_add':
        bot.send_message(ADMIN_ID, "ফরম্যাট: Email:Password:Category:Price")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT INTO emails (email, password, category, price, status) VALUES (?, ?, ?, ?, 'available')", m.text.split(':')), conn.commit(), bot.reply_to(m, "✅ যুক্ত হয়েছে!")])

bot.infinity_polling()
