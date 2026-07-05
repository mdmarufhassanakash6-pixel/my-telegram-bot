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
    markup.row('🛒 BUY GMAIL', '💰 SELL GMAIL')
    markup.row('📢 CHANNEL', '📞 CONTACT')
    if chat_id == ADMIN_ID:
        markup.row('⚙️ ADMIN PANEL')
    bot.send_message(chat_id, "👋 WELCOME! PLEASE CHOOSE AN OPTION:", reply_markup=markup)

# --- Start Handler ---
@bot.message_handler(commands=['start'])
def start(message):
    if not is_subscribed(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📢 JOIN MAIN CHANNEL", url=CHANNEL_URL))
        markup.add(types.InlineKeyboardButton("🔑 VERIFY", callback_data='verify_sub'))
        bot.send_message(message.chat.id, "⚠️ PLEASE JOIN THE CHANNEL TO USE THE BOT!", reply_markup=markup)
        return
    send_main_menu(message.chat.id)

# --- Main Text Handler ---
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    if not is_subscribed(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ PLEASE JOIN THE CHANNEL AND TYPE /start!")
        return

    # BUY FLOW
    if message.text == '🛒 BUY GMAIL':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('  OLD GMAIL (35 TK)  ', '  NEW GMAIL (32 TK)  ')
        markup.row('⬅️ BACK', '🏠 MAIN MENU')
        bot.send_message(message.chat.id, "📦 PLEASE SELECT CATEGORY:", reply_markup=markup)
    
    elif message.text in ['  OLD GMAIL (35 TK)  ', '  NEW GMAIL (32 TK)  ']:
        cat = 'Old' if '35' in message.text else 'New'
        price = 35 if cat == 'Old' else 32
        bot.send_message(message.chat.id, f"YOU SELECTED {cat}. HOW MANY DO YOU WANT?")
        bot.register_next_step_handler(message, ask_payment_info, cat, price)

    # SELL FLOW
    elif message.text == '💰 SELL GMAIL':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row('💰 SELL OLD GMAIL', '💰 SELL NEW GMAIL')
        markup.row('⬅️ BACK', '🏠 MAIN MENU')
        bot.send_message(message.chat.id, "💰 SELECT CATEGORY TO SELL:", reply_markup=markup)

    elif message.text in ['💰 SELL OLD GMAIL', '💰 SELL NEW GMAIL']:
        cat = 'Old' if 'OLD' in message.text else 'New'
        bot.send_message(message.chat.id, f"HOW MANY PIECES OF {cat} GMAIL DO YOU WANT TO SELL?")
        bot.register_next_step_handler(message, ask_gmail_credentials, cat)

    # NAVIGATIONS
    elif message.text == '🏠 MAIN MENU': send_main_menu(message.chat.id)
    elif message.text == '⬅️ BACK': send_main_menu(message.chat.id)
    elif message.text == '📢 CHANNEL': bot.send_message(message.chat.id, f"📢 CHANNEL: {CHANNEL_URL}")
    elif message.text == '📞 CONTACT': bot.send_message(message.chat.id, "📞 CONTACT: @AK_A_SH_002")
    
    # ADMIN
    elif message.text == '⚙️ ADMIN PANEL' and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ ADD GMAIL", callback_data='admin_add'),
                   types.InlineKeyboardButton("📊 CHECK STOCK", callback_data='admin_stock'))
        bot.send_message(message.chat.id, "⚙️ ADMIN PANEL:", reply_markup=markup)

# --- Steps Logic ---
def ask_payment_info(message, cat, price):
    if message.text in ['⬅️ BACK', '🏠 MAIN MENU']: return handle_text(message)
    try:
        qty = int(message.text)
        bot.send_message(message.chat.id, f"ORDER: {qty} x {cat}. TOTAL: {qty * price} TK.\nBKASH: 01762921053\nPLEASE SEND TRXID AND NUMBER.")
        bot.register_next_step_handler(message, finalize_order, cat, qty)
    except: bot.send_message(message.chat.id, "PLEASE ENTER A NUMBER ONLY!")

def finalize_order(message, cat, qty):
    bot.send_message(ADMIN_ID, f"🔔 PAYMENT REQUEST!\nUSER: {message.chat.id}\nITEM: {qty} x {cat}\nDETAILS: {message.text}")
    bot.send_message(message.chat.id, "✅ REQUEST SENT TO ADMIN.")

def ask_gmail_credentials(message, cat):
    if message.text in ['⬅️ BACK', '🏠 MAIN MENU']: return handle_text(message)
    qty = message.text
    bot.send_message(message.chat.id, "PLEASE SEND GMAIL AND PASSWORD:")
    bot.register_next_step_handler(message, ask_payment_method, cat, qty)

def ask_payment_method(message, cat, qty):
    creds = message.text
    bot.send_message(message.chat.id, "PLEASE SEND YOUR PAYMENT NUMBER (BKASH/NAGAD):")
    bot.register_next_step_handler(message, finish_sell_order, cat, qty, creds)

def finish_sell_order(message, cat, qty, creds):
    bot.send_message(ADMIN_ID, f"💰 SELL REQUEST!\nITEM: {qty} x {cat}\nINFO: {creds}\nPAYMENT: {message.text}")
    bot.send_message(message.chat.id, "✅ REQUEST SENT SUCCESSFULLY.")

# --- Callback Handler ---
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == 'verify_sub':
        if is_subscribed(call.message.chat.id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            send_main_menu(call.message.chat.id)
        else: bot.answer_callback_query(call.id, "❌ YOU HAVE NOT JOINED THE CHANNEL!", show_alert=True)
    elif call.data == 'admin_add':
        bot.send_message(call.message.chat.id, "FORMAT: Email Pass Category Price")
        bot.register_next_step_handler(call.message, save_email)
    elif call.data == 'admin_stock':
        cursor.execute("SELECT category, COUNT(*) FROM emails WHERE status='available' GROUP BY category")
        data = cursor.fetchall()
        msg = "📊 CURRENT STOCK:\n" + "\n".join([f"{r[0]}: {r[1]} PIECES" for r in data])
        bot.send_message(call.message.chat.id, msg or "STOCK IS EMPTY!")

def save_email(message):
    try:
        email, password, cat, price = message.text.split()
        cursor.execute("INSERT INTO emails VALUES (NULL, ?, ?, ?, ?, 'available')", (email, password, cat, float(price)))
        conn.commit()
        bot.reply_to(message, "✅ ADDED SUCCESSFULLY!")
    except: bot.reply_to(message, "FORMAT ERROR!")

if __name__ == "__main__":
    bot.infinity_polling()