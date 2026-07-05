import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"

bot = telebot.TeleBot(TOKEN)

# DB Setup
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails
                  (id INTEGER PRIMARY KEY, email TEXT, password TEXT,
                   category TEXT, price REAL, status TEXT)''')
conn.commit()

# --- Helpers ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 Buy Gmail', '💰 Sell Gmail')
    markup.row('📢 Channel', '📞 Contact')
    if chat_id == ADMIN_ID:
        markup.row('⚙️ Admin Panel')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- Start Handler ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Main Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔑 Verify", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেলে জয়েন করুন!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

# --- Main Text Handler ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ আগে চ্যানেলে জয়েন করুন!")
        return

    # BUY FLOW
    if message.text == '🛒 Buy Gmail':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('Old Gmail (35 TK)', 'New Gmail (32 TK)')
        markup.row('⬅️ Back', '🏠 Main Menu')
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif message.text in ['Old Gmail (35 TK)', 'New Gmail (32 TK)']:
        cat = 'Old' if '35' in message.text else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(message.chat.id, f"আপনি {cat} বেছে নিয়েছেন। কয়টি নিতে চান?")
        bot.register_next_step_handler(message, ask_payment_info, cat, price)

    # SELL FLOW
    elif message.text == '💰 Sell Gmail':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('Sell Old Gmail', 'Sell New Gmail')
        markup.row('⬅️ Back', '🏠 Main Menu')
        bot.send_message(message.chat.id, "💰 সেল করতে ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)

    elif message.text in ['Sell Old Gmail', 'Sell New Gmail']:
        cat = 'Old' if 'Old' in message.text else 'New'
        bot.send_message(message.chat.id, f"কত পিস {cat} জিমেইল সেল করতে চান?")
        bot.register_next_step_handler(message, ask_gmail_credentials, cat)

    # NAVIGATIONS
    elif message.text == '🏠 Main Menu': send_main_menu(message.chat.id)
    elif message.text == '⬅️ Back': send_main_menu(message.chat.id)
    elif message.text == '📢 Channel': bot.send_message(message.chat.id, f"📢 চ্যানেল: {CHANNEL_URL}")
    elif message.text == '📞 Contact': bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")
    
    # ADMIN
    elif message.text == '⚙️ Admin Panel' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Gmail", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 Check Stock", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)

# --- Steps Logic ---
def ask_payment_info(message, cat, price):
    if message.text in ['⬅️ Back', '🏠 Main Menu']: return handle_text(message)
    try:
        qty = int(message.text)
        bot.send_message(message.chat.id, f"অর্ডার: {qty} টি {cat}। মোট: {qty * price} টাকা।\nবিকাশ: 01762921053\nTrxID ও নাম্বার দিন।")
        bot.register_next_step_handler(message, finalize_order, cat, qty)
    except: bot.send_message(message.chat.id, "শুধু সংখ্যা লিখুন!")

def finalize_order(message, cat, qty):
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nডিটেইলস: {message.text}")
    bot.send_message(message.chat.id, "✅ অ্যাডমিনের কাছে পাঠানো হয়েছে।")

def ask_gmail_credentials(message, cat):
    if message.text in ['⬅️ Back', '🏠 Main Menu']: return handle_text(message)
    qty = message.text
    bot.send_message(message.chat.id, "জিমেইল এবং পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(message, ask_payment_method, cat, qty)

def ask_payment_method(message, cat, qty):
    creds = message.text
    bot.send_message(message.chat.id, "পেমেন্ট নাম্বার (বিকাশ/নগদ) দিন:")
    bot.register_next_step_handler(message, finish_sell_order, cat, qty, creds)

def finish_sell_order(message, cat, qty, creds):
    bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nপণ্য: {qty} {cat}\nতথ্য: {creds}\nপেমেন্ট: {message.text}")
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

# --- Callback Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else: bot.answer_callback_query(call.id, "❌ চ্যানেলে জয়েন করেননি!", show_alert=True)
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email Pass Category Price")
        bot.register_next_step_handler(call.message, save_email)
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 বর্তমান স্টক:\n" + "\n".join([f"{r[0]}: {r[1]} টি" for r in data])
        bot.send_message(call.message.chat.id, msg or "স্টক খালি!")

def save_email(message):
    try:
        email, password, cat, price = message.text.split()
        cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", (email, password, cat, float(price)))
        conn.commit()
        bot.reply_to(message, "✅ যুক্ত হয়েছে!")
    except: bot.reply_to(message, "Error!")

if __name__ == "__main__":
    bot.infinity_polling()