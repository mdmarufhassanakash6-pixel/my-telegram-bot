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

# ডাটাবেজ সেটআপ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT UNIQUE, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS sold_pending (id INTEGER PRIMARY KEY, user_id INTEGER, email TEXT UNIQUE, password TEXT, category TEXT, p_num TEXT)''')
conn.commit()

# --- হেল্পার ফাংশন ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
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
    bot.send_message(chat_id, "👋 স্বাগতম! মেনু থেকে বেছে নিন:", reply_markup=markup)

# --- মূল হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেলে জয়েন করুন!", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL)))
        return
    send_main_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id): return
    text = message.text.strip()

    if text == '🛒 জিমেইল কিনুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, f"{get_stock_text()}\n\nক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(message.chat.id, "কয়টি নিতে চান?")
        bot.register_next_step_handler(message, lambda m: ask_payment_info(m, cat, price))

    elif text == '💰 জিমেইল বেচুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "💰 কোন ক্যাটাগরির জিমেইল বেচবেন?", reply_markup=markup)

    elif text in ['পুরানো জিমেইল (২৫ টাকা)', 'নতুন জিমেইল (২২ টাকা)']:
        cat = 'Old' if '২৫' in text else 'New'
        bot.send_message(message.chat.id, "জিমেইল:পাসওয়ার্ড:পেমেন্ট_নাম্বার দিন:")
        bot.register_next_step_handler(message, lambda m: finish_sell_order(m, cat))

    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ জিমেইল যোগ", callback_data='admin_add'),
                   types.InlineKeyboardButton("➖ জিমেইল রিমুভ", callback_data='admin_remove'))
        markup.add(types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'),
                   types.InlineKeyboardButton("📥 সেল জিমেইল", callback_data='admin_view_sold'))
        markup.add(types.InlineKeyboardButton("👥 ইউজার সংখ্যা", callback_data='admin_users'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

# --- ফাংশন ও কলব্যাক ---
def ask_payment_info(message, cat, price):
    try:
        qty = int(message.text)
        bot.send_message(message.chat.id, f"মোট {qty*price} টাকা। বিকাশ 01762921053-এ পাঠিয়ে TrxID দিন:")
        bot.register_next_step_handler(message, lambda m: finalize_buy_order(m, cat, qty, m.text))
    except: bot.send_message(message.chat.id, "❌ শুধু সংখ্যা লিখুন!")

def finalize_buy_order(message, cat, qty, details):
    markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"buy_app_{message.chat.id}_{qty}_{cat}"), types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"buy_can_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"🔔 ক্রয় রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} {cat}\nডিটেইলস: {details}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

def finish_sell_order(message, cat):
    try:
        email, password, p_num = message.text.split(':')
        cursor.execute("INSERT INTO sold_pending (user_id, email, password, category, p_num) VALUES (?, ?, ?, ?, ?)", (message.chat.id, email, password, cat, p_num))
        conn.commit()
        markup = types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"sell_app_{message.chat.id}_{cat}_{email}_{password}"), types.InlineKeyboardButton("❌ ক্যানসেল", callback_data=f"sell_can_{message.chat.id}"))
        bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nতথ্য: {email}:{password}\nপেমেন্ট: {p_num}", reply_markup=markup)
        bot.send_message(message.chat.id, "✅ জমা হয়েছে।")
    except: bot.send_message(message.chat.id, "❌ ভুল ফরম্যাট! Email:Pass:Number দিন।")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data.split('_')
    if call.data.startswith('buy_app_'):
        u_id, qty, cat = data[2], int(data[3]), data[4]
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (cat, qty))
        rows = cursor.fetchall()
        for r in rows: cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (r[0],))
        conn.commit()
        bot.send_message(u_id, "\n".join([f"{r[1]} | {r[2]}" for r in rows]))
        bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
    elif call.data.startswith('sell_app_'):
        try:
            cursor.execute("INSERT INTO emails (email, password, category, status) VALUES (?, ?, ?, 'available')", (data[4], data[5], data[3]))
            cursor.execute("DELETE FROM sold_pending WHERE email=?", (data[4],))
            conn.commit()
            bot.send_message(data[2], "✅ পেমেন্ট সফল, জিমেইল স্টকে যোগ হয়েছে!")
            bot.edit_message_text("✅ এপ্রুভড!", ADMIN_ID, call.message.message_id)
        except: bot.answer_callback_query(call.id, "❌ ডুপ্লিকেট জিমেইল!")
    elif call.data == 'admin_stock': bot.send_message(call.message.chat.id, get_stock_text())
    elif call.data == 'admin_users': 
        cursor.execute("SELECT COUNT(*) FROM users")
        bot.send_message(call.message.chat.id, f"👥 মোট ইউজার: {cursor.fetchone()[0]}")
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email:Pass:Category:Price")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT OR IGNORE INTO emails (email, password, category, price, status) VALUES (?, ?, ?, ?, 'available')", m.text.split(':')), conn.commit(), bot.reply_to(m, "✅ যুক্ত হয়েছে!")])
    elif call.data == 'admin_remove':
        bot.send_message(call.message.chat.id, "রিমুভ করতে জিমেইলটি লিখুন:")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("DELETE FROM emails WHERE email=?", (m.text.strip(),)), conn.commit(), bot.reply_to(m, "✅ রিমুভড!")])
    elif call.data == 'admin_view_sold':
        cursor.execute("SELECT email, password, category FROM sold_pending")
        rows = cursor.fetchall()
        bot.send_message(call.message.chat.id, "\n".join([f"{r[0]} | {r[1]} ({r[2]})" for r in rows]) if rows else "কোনো রিকোয়েস্ট নেই।")
    elif call.data.startswith('buy_can_') or call.data.startswith('sell_can_'):
        bot.send_message(data[2], "❌ ক্যানসেল করা হয়েছে।")
        bot.edit_message_text("❌ ক্যানসেলড!", ADMIN_ID, call.message.message_id)

bot.infinity_polling()
