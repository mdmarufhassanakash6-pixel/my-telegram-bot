import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ সেটআপ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails
                  (id INTEGER PRIMARY KEY, email TEXT, password TEXT,
                   category TEXT, price REAL, status TEXT)''')
conn.commit()

# --- হেল্পার ফাংশন ---
def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

def send_main_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 জিমেইল কিনুন', '💰 জিমেইল বেচুন')
    markup.row('📢 চ্যানেল', '📞 যোগাযোগ')
    if chat_id == ADMIN_ID:
        markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- স্টার্ট হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔑 ভেরিফাই", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেলে জয়েন করুন!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

# --- মূল হ্যান্ডলার ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ আগে চ্যানেলে জয়েন করুন এবং /start লিখুন!")
        return

    text = message.text.strip()

    # বাই ফ্লো
    if text == '🛒 জিমেইল কিনুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)')
        markup.row('⬅️ ফিরে যান', '🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(message.chat.id, f"আপনি {cat} বেছে নিয়েছেন। কয়টি নিতে চান?")
        bot.register_next_step_handler(message, ask_payment_info, cat, price)

    # সেল ফ্লো
    elif text == '💰 জিমেইল বেচুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল বেচুন', 'নতুন জিমেইল বেচুন')
        markup.row('⬅️ ফিরে যান', '🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "💰 সেল করতে ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)

    elif text in ['পুরানো জিমেইল বেচুন', 'নতুন জিমেইল বেচুন']:
        cat = 'Old' if 'পুরানো' in text else 'New'
        bot.send_message(message.chat.id, f"কয়টি {cat} জিমেইল বেচতে চান?")
        bot.register_next_step_handler(message, ask_gmail_credentials, cat)

    # নেভিগেশন
    elif text == '🏠 মেইন মেনু' or text == '⬅️ ফিরে যান': send_main_menu(message.chat.id)
    elif text == '📢 চ্যানেল': bot.send_message(message.chat.id, f"📢 চ্যানেল: {CHANNEL_URL}")
    elif text == '📞 যোগাযোগ': bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")
    
    # অ্যাডমিন
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ জিমেইল যোগ করুন", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)

# --- পেমেন্ট লজিক ---
def ask_payment_info(message, cat, price):
    if message.text in ['🏠 মেইন মেনু', '⬅️ ফিরে যান']: return handle_text(message)
    try:
        qty = int(message.text)
        total = qty * price
        bot.send_message(message.chat.id, f"অর্ডার: {qty} টি {cat}। মোট: {total} টাকা।\nবিকাশ: 01762921053\nTrxID ও আপনার নাম্বার দিন।")
        bot.register_next_step_handler(message, finalize_order, cat, qty, total)
    except: bot.send_message(message.chat.id, "শুধু সংখ্যা লিখুন!")

def finalize_order(message, cat, qty, total):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"approve_{message.chat.id}_{qty}_{cat}_{total}"))
    admin_msg = f"🔔 পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nমোট: {total} টাকা\nডিটেইলস: {message.text}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- সেল লজিক ---
def ask_gmail_credentials(message, cat):
    qty = message.text
    bot.send_message(message.chat.id, "জিমেইল এবং পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(message, ask_payment_method, cat, qty)

def ask_payment_method(message, cat, qty):
    creds = message.text
    bot.send_message(message.chat.id, "আপনার পেমেন্ট নাম্বার (বিকাশ/নগদ) দিন:")
    bot.register_next_step_handler(message, finish_sell_order, cat, qty, creds)

def finish_sell_order(message, cat, qty, creds):
    bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nপণ্য: {qty} {cat}\nতথ্য: {creds}\nপেমেন্ট: {message.text}")
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

# --- কলব্যাক হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else: bot.answer_callback_query(call.id, "❌ আপনি চ্যানেলে জয়েন করেননি!", show_alert=True)
    
    elif call.data.startswith('approve_'):
        _, user_id, qty, cat, total = call.data.split('_')
        bot.edit_message_text(f"✅ এপ্রুভ করা হয়েছে: {qty} {cat} (ইউজার: {user_id})", ADMIN_ID, call.message.message_id)
        bot.send_message(user_id, "🎉 অভিনন্দন! আপনার পেমেন্ট কনফার্ম হয়েছে।")
        bot.send_message(CHANNEL_ID, f"🎉 নতুন ট্রানজেকশন সফল!\n📦 {qty} টি {cat}\n💰 পেমেন্ট: {total} টাকা\n✅ সিস্টেম ভেরিফাইড!")
    
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
    except: bot.reply_to(message, "ভুল ফরম্যাট!")

if __name__ == "__main__":
    bot.infinity_polling()
