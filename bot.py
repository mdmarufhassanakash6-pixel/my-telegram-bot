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

# --- Start Handler ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 Join Main Channel", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔑 Verify", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ You Must Join Channel to use this bot!", reply_markup=markup)
        return
    
    send_main_menu(message.chat.id)

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 Buy Gmail', '💰 Sell Gmail')
    markup.row('📢 Channel', '📞 Contact')
    if chat_id == ADMIN_ID:
        markup.row('⚙️ Admin Panel')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- Text Handler ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ আগে চ্যানেলে জয়েন করুন এবং /start দিন।")
        return

    if message.text == '🛒 Buy Gmail':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Old Gmail (35 TK)", callback_data='buy_old'),
                   types.InlineKeyboardButton("New Gmail (32 TK)", callback_data='buy_new'))
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif message.text == '💰 Sell Gmail':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Old Gmail", callback_data='sell_old'),
                   types.InlineKeyboardButton("New Gmail", callback_data='sell_new'))
        bot.send_message(message.chat.id, "💰 সেল করতে ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)

    elif message.text == '⚙️ Admin Panel' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Gmail", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 Check Stock", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    elif message.text == '📢 Channel': bot.send_message(message.chat.id, f"📢 চ্যানেল: {CHANNEL_URL}")
    elif message.text == '📞 Contact': bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")

# --- Sell Flow ---
def ask_gmail_credentials(message, cat, qty):
    bot.send_message(message.chat.id, "এখন জিমেইল এবং পাসওয়ার্ডটি দিন (একসাথে):\nউদা: email@gmail.com pass123")
    bot.register_next_step_handler(message, ask_payment_method, cat, qty)

def ask_payment_method(message, cat, qty):
    creds = message.text
    bot.send_message(message.chat.id, "আপনার পেমেন্ট মেথড (বিকাশ/নগদ) এবং নাম্বারটি দিন:")
    bot.register_next_step_handler(message, finish_sell_order, cat, qty, creds)

def finish_sell_order(message, cat, qty, creds):
    payment_info = message.text
    admin_msg = (f"💰 নতুন সেল রিকোয়েস্ট!\nইউজার ID: {message.chat.id}\n"
                 f"ক্যাটাগরি: {cat}\nপরিমাণ: {qty}\nজিমেইল ও পাস: {creds}\nপেমেন্ট ডিটেইলস: {payment_info}")
    bot.send_message(ADMIN_ID, admin_msg)
    bot.send_message(message.chat.id, "✅ আপনার সেল রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- Payment Flow ---
def ask_payment_info(message, cat, price):
    try:
        qty = int(message.text)
        total = qty * price
        bot.send_message(message.chat.id, f"অর্ডার: {qty} টি {cat} জিমেইল। মোট: {total} টাকা।\n\nবিকাশ: 01762921053\nটাকা পাঠিয়ে [TrxID] ও [বিকাশ নাম্বার] লিখে পাঠান।")
        bot.register_next_step_handler(message, finalize_order, cat, qty)
    except:
        bot.send_message(message.chat.id, "ভুল ইনপুট! শুধু সংখ্যা লিখুন।")

def finalize_order(message, cat, qty):
    trx_info = message.text
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"pay_approve_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nবিস্তারিত: {trx_info}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ পেমেন্ট রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- Callback Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.answer_callback_query(call.id, "✅ ভেরিফাইড!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)
        return

    if not is_subscribed(call.message.chat.id):
        bot.answer_callback_query(call.id, "চ্যানেলে জয়েন করা বাধ্যতামূলক!")
        return

    # Sell Logic
    if call.data in ['sell_old', 'sell_new']:
        cat = 'Old' if 'old' in call.data else 'New'
        bot.send_message(call.message.chat.id, f"কত পিস {cat} জিমেইল সেল করতে চান?")
        bot.register_next_step_handler(call.message, ask_gmail_credentials, cat)
    
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "পণ্য পাঠান: Email Password Category Price")
        bot.register_next_step_handler(call.message, save_email)
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 বর্তমান স্টক:\n" + "\n".join([f"{r[0]}: {r[1]} টি" for r in data])
        bot.send_message(call.message.chat.id, msg or "স্টক খালি!")
    elif call.data in ['buy_old', 'buy_new']:
        cat = 'Old' if 'old' in call.data else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(call.message.chat.id, f"কয়টি {cat} জিমেইল নিতে চান?")
        bot.register_next_step_handler(call.message, ask_payment_info, cat, price)

def save_email(message):
    try:
        email, password, cat, price = message.text.split()
        cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", (email, password, cat, float(price)))
        conn.commit()
        bot.reply_to(message, "✅ জিমেইল যুক্ত হয়েছে!")
    except:
        bot.reply_to(message, "Error: ফরম্যাট 'Email Pass Category Price'")

if __name__ == "__main__":
    bot.infinity_polling()