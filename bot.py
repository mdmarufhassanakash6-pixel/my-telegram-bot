import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
# লগ ক্র্যাশ এড়াতে এখানে ডিফল্ট হ্যান্ডলিং দেওয়া হয়েছে
admin_id_raw = os.getenv('ADMIN_ID')
ADMIN_ID = int(admin_id_raw) if admin_id_raw and admin_id_raw.isdigit() else 0

CHANNEL_ID = '@gmailbuyer1122'
CHANNEL_URL = "https://t.me/gmailbuyer1122"

bot = telebot.TeleBot(TOKEN)

# ডাটাবেজ সেটআপ
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails
                  (id INTEGER PRIMARY KEY, email TEXT, password TEXT,
                   category TEXT, price REAL, status TEXT)''')
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
    if chat_id == ADMIN_ID:
        markup.row('⚙️ অ্যাডমিন প্যানেল')
    bot.send_message(chat_id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- হ্যান্ডলার ---
@bot.message_handler(commands=['start'])
def start(message):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 চ্যানেলে জয়েন করুন", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔑 ভেরিফাই", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ বট ব্যবহারের জন্য চ্যানেলে জয়েন করুন!", reply_markup=markup)
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
        bot.send_message(message.chat.id, "📦 ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
    
    elif text in ['পুরানো জিমেইল (৩৫ টাকা)', 'নতুন জিমেইল (৩২ টাকা)']:
        cat = 'Old' if '৩৫' in text else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(message.chat.id, f"আপনি {cat} বেছে নিয়েছেন। কয়টি নিতে চান?")
        bot.register_next_step_handler(message, ask_payment_info, cat, price)

    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ যোগ", callback_data='admin_add'),
                   types.InlineKeyboardButton("➖ রিমুভ", callback_data='admin_remove'))
        markup.add(types.InlineKeyboardButton("📊 স্টক", callback_data='admin_stock'),
                   types.InlineKeyboardButton("👥 ইউজার", callback_data='admin_users'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)
    
    elif text == '🏠 মেইন মেনু': send_main_menu(message.chat.id)

# --- পেমেন্ট ও ডেলিভারি ---
def ask_payment_info(message, cat, price):
    try:
        qty = int(message.text)
        total = qty * price
        bot.send_message(message.chat.id, f"মোট: {total} টাকা।\nবিকাশ: 01762921053\nTrxID ও নাম্বার দিন।")
        bot.register_next_step_handler(message, finalize_order, cat, qty, total)
    except: bot.send_message(message.chat.id, "শুধু সংখ্যা লিখুন!")

def finalize_order(message, cat, qty, total):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"approve_{message.chat.id}_{qty}_{cat}_{total}"))
    bot.send_message(ADMIN_ID, f"🔔 রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nমোট: {total} টাকা\nডিটেইলস: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else: bot.answer_callback_query(call.id, "❌ জয়েন করেননি!", show_alert=True)
    
    elif call.data.startswith('approve_'):
        _, user_id, qty, cat, total = call.data.split('_')
        qty = int(qty)
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (cat, qty))
        rows = cursor.fetchall()
        
        if len(rows) < qty:
            bot.send_message(ADMIN_ID, "❌ স্টক শেষ!")
        else:
            delivery = "✅ ডেলিভারি:\n"
            for row in rows:
                delivery += f"📧 {row[1]} | 🔑 {row[2]}\n"
                cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (row[0],))
            conn.commit()
            bot.send_message(user_id, delivery)
            bot.send_message(CHANNEL_ID, f"🎉 সেল সফল!\n👤 ইউজার আইডি: {user_id}\n📦 {qty} টি {cat}\n💰 {total} টাকা")
            bot.edit_message_text("✅ ডেলিভারি সম্পন্ন!", ADMIN_ID, call.message.message_id)

    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 স্টক:\n" + "\n".join([f"{r[0]}: {r[1]} টি" for r in data])
        bot.send_message(call.message.chat.id, msg or "খালি!")
    
    elif call.data == 'admin_users':
        cursor.execute("SELECT COUNT(*) FROM users")
        bot.send_message(call.message.chat.id, f"👥 মোট ইউজার: {cursor.fetchone()[0]}")

    elif call.data == 'admin_remove':
        bot.send_message(call.message.chat.id, "রিমুভ করতে জিমেইলটি লিখুন:")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("DELETE FROM emails WHERE email=?", (m.text.strip(),)), conn.commit(), bot.reply_to(m, "✅ রিমুভড!")])

    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email Pass Category Price")
        bot.register_next_step_handler(call.message, lambda m: [cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", m.text.split()), conn.commit(), bot.reply_to(m, "✅ যোগ হয়েছে!")])

if __name__ == "__main__":
    bot.infinity_polling()
