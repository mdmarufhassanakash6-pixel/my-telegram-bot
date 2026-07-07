import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ টেবিল
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sold_pending (id INTEGER PRIMARY KEY, user_id INTEGER, email TEXT UNIQUE, password TEXT, category TEXT, p_num TEXT)''')
conn.commit()

# --- হেল্পার ফাংশন ---
def is_subscribed(user_id):
    try: return bot.get_chat_member(CHANNEL_ID, user_id).status in ['member', 'administrator', 'creator']
    except: return False

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID: markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- মূল হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ চ্যানেলে জয়েন করুন!", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 জয়েন", url=CHANNEL_URL)))
        return
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text.strip()
    if text == '🛒 জিমেইল কিনুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)').row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        bot.send_message(message.chat.id, "কয়টি জিমেইল নিতে চান?")
        bot.register_next_step_handler(message, lambda m: ask_buy(m, cat))
    elif text == '💰 জিমেইল বেচুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True).row('পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)').row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "💰 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    elif text in ['পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)']:
        cat = 'Old' if '২৫' in text else 'New'
        bot.send_message(message.chat.id, "জিমেইল:পাসওয়ার্ড:পেমেন্ট_নাম্বার দিন:")
        bot.register_next_step_handler(message, lambda m: ask_sell(m, cat))
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("➕ যোগ", callback_data='admin_add'),
            types.InlineKeyboardButton("➖ রিমুভ", callback_data='admin_remove'),
            types.InlineKeyboardButton("📊 স্টক", callback_data='admin_stock'),
            types.InlineKeyboardButton("📥 সেল রিকোয়েস্ট", callback_data='admin_view_sold')
        )
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

def ask_buy(message, cat):
    markup = types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"buy_app_{message.chat.id}_{message.text}_{cat}"),
        types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"buy_can_{message.chat.id}")
    )
    bot.send_message(ADMIN_ID, f"🔔 ক্রয় রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {message.text} টি {cat}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

def ask_sell(message, cat):
    try:
        email, password, p_num = message.text.split(':')
        cursor.execute("INSERT INTO sold_pending (user_id, email, password, category, p_num) VALUES (?, ?, ?, ?, ?)", (message.chat.id, email, password, cat, p_num))
        conn.commit()
        markup = types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"sell_app_{message.chat.id}_{cat}_{email}_{password}"),
            types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"sell_can_{message.chat.id}")
        )
        bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nতথ্য: {email}:{password}\nপেমেন্ট: {p_num}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ জমা হয়েছে।")
    except: bot.send_message(message.chat.id, "❌ ফরম্যাট ভুল! (Email:Pass:Number)")

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    data = call.data.split('_')
    if call.data.startswith('buy_app_'):
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (data[4], int(data[3])))
        rows = cursor.fetchall()
        for r in rows: cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (r[0],))
        conn.commit()
        bot.send_message(data[2], "\n".join([f"{r[1]} | {r[2]}" for r in rows]))
        bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
    elif call.data.startswith('sell_app_'):
        try:
            cursor.execute("INSERT INTO emails (email, password, category, status) VALUES (?, ?, ?, 'available')", (data[4], data[5], data[3]))
            cursor.execute("DELETE FROM sold_pending WHERE email=?", (data[4],))
            conn.commit()
            bot.send_message(data[2], "🎉 সফল!")
            bot.edit_message_text("✅ এপ্রুভড!", ADMIN_ID, call.message.message_id)
        except: bot.answer_callback_query(call.id, "❌ ডুপ্লিকেট!")
    elif call.data == 'admin_stock': 
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        bot.send_message(call.message.chat.id, str(cursor.fetchall()))
    elif call.data == 'admin_view_sold':
        cursor.execute("SELECT email, password, category FROM sold_pending")
        bot.send_message(call.message.chat.id, str(cursor.fetchall()))
    elif call.data.startswith('buy_can_') or call.data.startswith('sell_can_'):
        bot.send_message(data[2], "❌ ক্যানসেল হয়েছে।")
        bot.edit_message_text("❌ ক্যানসেলড!", ADMIN_ID, call.message.message_id)

bot.infinity_polling()
