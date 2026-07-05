import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = '@gmailbuyer1122'

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

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেল জয়েন করুন", url="https://t.me/gmailbuyer1122"))
        bot.send_message(message.chat.id, "❌ বট ব্যবহারের আগে অবশ্যই আমাদের চ্যানেলে জয়েন করুন এবং আবার /start দিন।", reply_markup=markup)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 Buy Gmail', '💰 Sell Gmail')
    markup.row('📢 Channel', '📞 Contact')
    if message.chat.id == ADMIN_ID:
        markup.row('⚙️ Admin Panel')
    bot.send_message(message.chat.id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "অনুগ্রহ করে চ্যানেলে জয়েন করে /start দিন।")
        return

    if message.text == '🛒 Buy Gmail':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Old Gmail (35 TK)", callback_data='buy_old'),
                   types.InlineKeyboardButton("New Gmail (32 TK)", callback_data='buy_new'))
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    elif message.text == '⚙️ Admin Panel' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Add Gmail", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 Check Stock", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    # বাকি মেনু বাটন...
    elif message.text == '📢 Channel': bot.send_message(message.chat.id, "📢 চ্যানেল: https://t.me/gmailbuyer1122")
    elif message.text == '📞 Contact': bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")

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
    markup.add(types.InlineKeyboardButton("✅ Approve Payment", callback_data=f"pay_approve_{message.chat.id}_{qty}_{cat}"))
    bot.send_message(ADMIN_ID, f"🔔 নতুন পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nবিস্তারিত: {trx_info}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ পেমেন্ট রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- Callback ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if not is_subscribed(call.message.chat.id):
        bot.answer_callback_query(call.id, "চ্যানেলে জয়েন করা বাধ্যতামূলক!")
        return

    if call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "পণ্য পাঠান: Email Password Category Price")
        bot.register_next_step_handler(call.message, save_email)
    elif call.data in ['buy_old', 'buy_new']:
        cat = 'Old' if 'old' in call.data else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(call.message.chat.id, f"কয়টি {cat} জিমেইল নিতে চান?")
        bot.register_next_step_handler(call.message, ask_payment_info, cat, price)
    elif call.data.startswith('pay_approve_'):
        # এখানে আপনার approve_order_logic ফাংশনটি কল করবেন
        bot.answer_callback_query(call.id, "এপ্রুভ করা হয়েছে!")

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