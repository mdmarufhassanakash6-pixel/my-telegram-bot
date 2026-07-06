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

# ডাটাবেজ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails (id INTEGER PRIMARY KEY, email TEXT, password TEXT, category TEXT, price REAL, status TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
conn.commit()

# --- ফাংশনস ---
def is_subscribed(user_id):
    try: return bot.get_chat_member(CHANNEL_ID, user_id).status in ['member', 'administrator', 'creator']
    except: return False

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID: markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- স্টার্ট ও ভেরিফিকেশন ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেল", url=CHANNEL_URL),
                   types.InlineKeyboardButton("👥 ফেসবুক গ্রুপ", url=FB_GROUP_URL))
        markup.add(types.InlineKeyboardButton("🔑 আমি জয়েন করেছি, ভেরিফাই করুন", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য আগে চ্যানেল ও ফেসবুক গ্রুপে জয়েন করুন!", reply_markup=markup)
    else: send_main_menu(message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == 'verify_sub')
def verify(call):
    if is_subscribed(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id)
    else: bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)

# --- হ্যান্ডলার ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id): return
    text = message.text
    
    if text == '🛒 জিমেইল কিনুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "ক্যাটাগরি বেছে নিন:", reply_markup=markup)
    elif 'জিমেইল (' in text:
        cat = 'Old' if '৩৫' in text else 'New'
        bot.send_message(message.chat.id, "কয়টি কিনবেন? (সংখ্যা দিন)")
        bot.register_next_step_handler(message, lambda m: ask_payment(m, cat, 35 if cat=='Old' else 32))
    elif text == '💰 জিমেইল বেচুন':
        bot.send_message(message.chat.id, "কতগুলো জিমেইল বেচবেন?")
        bot.register_next_step_handler(message, ask_gmail_creds)
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ জিমেইল যোগ", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

def ask_payment(message, cat, price):
    try:
        qty = int(message.text)
        bot.send_message(message.chat.id, f"মোট: {qty*price} টাকা।\nবিকাশ: 01762921053\nপেমেন্ট করার পর TrxID ও বিকাশ নাম্বার দিন:")
        bot.register_next_step_handler(message, lambda m: finalize_buy(m, cat, qty, qty*price))
    except: bot.send_message(message.chat.id, "❌ শুধু সংখ্যা দিন!")

def finalize_buy(message, cat, qty, total):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ", callback_data=f"approve_{message.chat.id}_{qty}_{cat}_{total}"))
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nডিটেইলস: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ আপনার পেমেন্ট রিকোয়েস্টটি পাঠানো হয়েছে।")

def ask_gmail_creds(message):
    qty = message.text
    bot.send_message(message.chat.id, "জিমেইল এবং পাসওয়ার্ড পাঠান:")
    bot.register_next_step_handler(message, lambda m: ask_pay_num(m, qty, m.text))

def ask_pay_num(message, qty, creds):
    bot.send_message(message.chat.id, "আপনার বিকাশ নাম্বার দিন:")
    bot.register_next_step_handler(message, lambda m: finish_sell(m, qty, creds, m.text))

def finish_sell(message, qty, creds, p_num):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ পেমেন্ট করেছি", callback_data=f"sell_approve_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি\nতথ্য: {creds}\nপেমেন্ট: {p_num}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট সফলভাবে পাঠানো হয়েছে।")

# --- কলব্যাক লজিক ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data.startswith('approve_'):
        _, user_id, qty, cat, total = call.data.split('_')
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (cat, int(qty)))
        rows = cursor.fetchall()
        if len(rows) < int(qty): bot.send_message(ADMIN_ID, "❌ স্টক শেষ!")
        else:
            msg = "✅ ডেলিভারি:\n" + "\n".join([f"{r[1]} | {r[2]}" for r in rows])
            for r in rows: cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (r[0],))
            conn.commit()
            bot.send_message(user_id, msg)
            bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)
    elif call.data.startswith('sell_approve_'):
        bot.send_message(call.data.split('_')[2], "🎉 পেমেন্ট সফল, আমাদের সাথে থাকার জন্য ধন্যবাদ!")
        bot.edit_message_text("✅ পেমেন্ট এপ্রুভড!", ADMIN_ID, call.message.message_id)
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        msg = "\n".join([f"{r[0]}: {r[1]} টি" for r in cursor.fetchall()])
        bot.send_message(call.message.chat.id, msg or "স্টক খালি!")
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email Pass Category Price")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", m.text.split()), conn.commit(), bot.reply_to(m, "✅ যুক্ত হয়েছে!")])

bot.infinity_polling()
