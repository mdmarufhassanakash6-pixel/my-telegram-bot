import os
import telebot
from telebot import types
import sqlite3

# এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন ও আইডি নেয়া
TOKEN = os.getenv('TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))

bot = telebot.TeleBot(TOKEN)

# DB Setup
conn = sqlite3.connect('gmail_store.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS emails
                  (id INTEGER PRIMARY KEY, email TEXT, password TEXT,
                   category TEXT, price REAL, status TEXT)''')
conn.commit()

# --- Main Menu ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('🛒 Buy Gmail', '💰 Sell Gmail')
    markup.row('📢 Channel', '📞 Contact')
    if message.chat.id == ADMIN_ID:
        markup.row('⚙️ Admin Panel')
    bot.send_message(message.chat.id, "👋 স্বাগতম! আপনার অপশনটি বেছে নিন:", reply_markup=markup)

# --- Button Handlers ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
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
    elif message.text == '📢 Channel':
        bot.send_message(message.chat.id, "📢 চ্যানেল: https://t.me/gmailbuyer1122")
    elif message.text == '📞 Contact':
        bot.send_message(message.chat.id, "📞 যোগাযোগ: @AK_A_SH_002")

# --- Callback & Logic (আপনার দেয়া আগের লজিক এখানে থাকবে) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "পণ্য পাঠান: Email Password Category Price\nউদা: user@mail.com pass123 Old 35")
        bot.register_next_step_handler(call.message, save_email)
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 বর্তমান স্টক:\n" + "\n".join([f"{r[0]}: {r[1]} টি" for r in data])
        bot.send_message(call.message.chat.id, msg or "স্টক খালি!")
    elif call.data in ['buy_old', 'buy_new']:
        cat = 'Old' if 'old' in call.data else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(call.message.chat.id, f"আপনি {cat} জিমেইল বেছে নিয়েছেন (দাম: {price} টাকা)। কয়টি নিতে চান?")
        bot.register_next_step_handler(call.message, ask_payment_info, cat, price)
    # বাকি লজিকগুলো এখানে যুক্ত করুন...

# (আপনার আগের সব ফাংশন - ask_payment_info, finalize_order ইত্যাদি নিচে একইভাবে থাকবে)

if __name__ == "__main__":
    bot.infinity_polling()
