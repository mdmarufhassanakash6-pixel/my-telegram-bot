import os
import telebot
from telebot import types
import sqlite3

TOKEN = os.getenv('TOKEN')
# রেলওয়েতে ADMIN_ID না থাকলেও যেন ক্র্যাশ না করে, সেজন্য এই সমাধান:
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
    # বটের ইউজার আইডি ডাটাবেজে ট্র্যাক করা
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    
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

    # --- বাই (Buy) ফ্লো ---
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

    # --- সেল (Sell) ফ্লো ---
    elif text == '💰 জিমেইল বেচুন':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('পুরানো জিমেইল বেচুন', 'নতুন জিমেইল বেচুন')
        markup.row('🏠 মেইন মেনু')
        bot.send_message(message.chat.id, "💰 সেল করতে ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)

    elif text in ['পুরানো জিমেইল বেচুন', 'নতুন জিমেইল বেচুন']:
        cat = 'Old' if 'পুরানো' in text else 'New'
        bot.send_message(message.chat.id, f"কয়টি {cat} জিমেইল বেচতে চান?")
        bot.register_next_step_handler(message, ask_gmail_credentials, cat)

    # --- নেভিগেশন ---
    elif text == '🏠 মেইন মেনু':
        send_main_menu(message.chat.id)
    elif text == '📢 চ্যানেল':
        bot.send_message(message.chat.id, f"📢 চ্যানেল: {CHANNEL_URL}")
    elif text == '📞 যোগাযোগ':
        bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")
    
    # --- অ্যাডমিন প্যানেল বাটন ---
    elif text == '⚙️ অ্যাডমিন প্যানেল' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ জিমেইল যোগ করুন", callback_data='admin_add'),
                   types.InlineKeyboardButton("➖ জিমেইল রিমুভ", callback_data='admin_remove'))
        markup.add(types.InlineKeyboardButton("📊 স্টক চেক", callback_data='admin_stock'),
                   types.InlineKeyboardButton("👥 ইউজার সংখ্যা", callback_data='admin_users'))
        bot.send_message(message.chat.id, "⚙️ অ্যাডমিন প্যানেল:", reply_markup=markup)

# --- পেমেন্ট লজিক (কিনুন) ---
def ask_payment_info(message, cat, price):
    if message.text == '🏠 মেইন মেনু': return handle_text(message)
    try:
        qty = int(message.text)
        total = qty * price
        bot.send_message(message.chat.id, f"অর্ডার: {qty} টি {cat}। মোট: {total} টাকা।\nবিকাশ: 01762921053\nTrxID ও আপনার নাম্বার দিন।")
        bot.register_next_step_handler(message, finalize_order, cat, qty, total)
    except:
        bot.send_message(message.chat.id, "❌ শুধু সংখ্যা লিখুন!")

def finalize_order(message, cat, qty, total):
    if message.text == '🏠 মেইন মেনু': return handle_text(message)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ এপ্রুভ করুন", callback_data=f"approve_{message.chat.id}_{qty}_{cat}_{total}"))
    admin_msg = f"🔔 পেমেন্ট রিকোয়েস্ট!\nইউজার: {message.chat.id}\nপণ্য: {qty} টি {cat}\nমোট: {total} টাকা\nডিটেইলস: {message.text}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট অ্যাডমিনের কাছে পাঠানো হয়েছে।")

# --- সেল লজিক (বেচুন) ---
def ask_gmail_credentials(message, cat):
    if message.text == '🏠 মেইন মেনু': return handle_text(message)
    qty = message.text
    bot.send_message(message.chat.id, "জিমেইল এবং পাসওয়ার্ড দিন:")
    bot.register_next_step_handler(message, ask_payment_method, cat, qty)

def ask_payment_method(message, cat, qty):
    if message.text == '🏠 মেইন মেনু': return handle_text(message)
    creds = message.text
    bot.send_message(message.chat.id, "আপনার পেমেন্ট নাম্বার (বিকাশ/নগদ) দিন:")
    bot.register_next_step_handler(message, finish_sell_order, cat, qty, creds)

def finish_sell_order(message, cat, qty, creds):
    if message.text == '🏠 mেইন মেনু': return handle_text(message)
    bot.send_message(ADMIN_ID, f"💰 সেল রিকোয়েস্ট!\nপণ্য: {qty} {cat}\nতথ্য: {creds}\nপেমেন্ট: {message.text}")
    bot.send_message(message.chat.id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")

# --- অ্যাডমিন অ্যাকশন ফাংশন ব্যাকএন্ড ---
def save_email(message):
    try:
        email, password, cat, price = message.text.split()
        cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", (email, password, cat, float(price)))
        conn.commit()
        bot.reply_to(message, "✅ জিমেইলটি সফলভাবে যুক্ত হয়েছে!")
    except:
        bot.reply_to(message, "❌ ভুল ফরম্যাট! সঠিক ফরম্যাট: Email Pass Category Price (যেমন: abc@gmail.com 1234 Old 35)")

def remove_email(message):
    email = message.text.strip()
    cursor.execute("DELETE FROM emails WHERE email = ?", (email,))
    conn.commit()
    if cursor.rowcount > 0:
        bot.reply_to(message, "✅ জিমেইলটি সফলভাবে রিমুভ করা হয়েছে!")
    else:
        bot.reply_to(message, "❌ জিমেইলটি ডাটাবেজে পাওয়া যায়নি।")

# --- কলব্যাক হ্যান্ডলার ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # চ্যানেল সাবস্ক্রিপশন ভেরিফাই
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "❌ আপনি এখনো চ্যানেলে জয়েন করেননি!", show_alert=True)
    
    # অ্যাডমিন পেমেন্ট এপ্রুভাল এবং অটো-ডেলিভারি
    elif call.data.startswith('approve_'):
        _, user_id, qty, cat, total = call.data.split('_')
        qty = int(qty)
        
        cursor.execute("SELECT id, email, password FROM emails WHERE category=? AND status='available' LIMIT ?", (cat, qty))
        rows = cursor.fetchall()
        
        if len(rows) < qty:
            bot.send_message(ADMIN_ID, f"❌ স্টক কম! ইউজার {user_id} এর অর্ডার পূরণ করা যাচ্ছে না।")
            bot.send_message(user_id, "দুঃখিত, বর্তমানে পর্যাপ্ত জিমেইল স্টকে নেই। অ্যাডমিনের সাথে যোগাযোগ করুন।")
        else:
            delivery_msg = "✅ আপনার জিমেইলগুলো নিচে দেওয়া হলো:\n\n"
            for row in rows:
                delivery_msg += f"📧 জিমেইল: {row[1]}\n🔑 পাসওয়ার্ড: {row[2]}\n\n"
                cursor.execute("UPDATE emails SET status='sold' WHERE id=?", (row[0],))
            conn.commit()
            
            # ইউজারকে ডেলিভারি দেওয়া
            bot.send_message(user_id, delivery_msg)
            bot.edit_message_text(f"✅ ডেলিভারি সম্পন্ন হয়েছে: {qty} টি {cat} (ইউজার: {user_id})", ADMIN_ID, call.message.message_id)
            
            # চ্যানেলে ইউজার আইডি সহ নোটিফিকেশন পাঠানো
            channel_msg = (f"🎉 নতুন ট্রানজেকশন সফল!\n"
                           f"👤 ইউজার আইডি: {user_id}\n"
                           f"📦 পণ্য: {qty} টি {cat}\n"
                           f"💰 পেমেন্ট: {total} টাকা\n"
                           f"✅ স্ট্যাটাস: ডেলিভারি কমপ্লিট!")
            bot.send_message(CHANNEL_ID, channel_msg)
    
    # অ্যাডমিন প্যানেল অ্যাকশনস
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "ফরম্যাট: Email Pass Category Price\n(যেমন: ex@gmail.com 123 Old 35)")
        bot.register_next_step_handler(call.message, save_email)
        
    elif call.data == 'admin_remove':
        bot.send_message(call.message.chat.id, "রিমুভ করতে জিমেইলটি লিখুন:")
        bot.register_next_step_handler(call.message, remove_email)
        
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 বর্তমান স্টক:\n" + "\n".join([f"{r[0]}: {r[1]} টি" for r in data])
        bot.send_message(call.message.chat.id, msg or "স্টক খালি!")
        
    elif call.data == 'admin_users':
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        bot.send_message(call.message.chat.id, f"👥 মোট ইউজার সংখ্যা: {count}")

if __name__ == "__main__":
    bot.infinity_polling()
