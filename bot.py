import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# এনভায়রনমেন্ট ভেরিয়েবল থেকে টোকেন ও আইডি নেয়া
TOKEN = os.getenv('TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Gmail Buy", callback_data='buy_menu')],
        [InlineKeyboardButton("Deposit", callback_data='deposit')]
    ]
    await update.message.reply_text("স্বাগতম! একটি অপশন বেছে নিন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Old Gmail", callback_data='old'), InlineKeyboardButton("New Gmail", callback_data='new')]
    ]
    await query.edit_message_text("কি ধরনের জিমেইল চান?", reply_markup=InlineKeyboardMarkup(keyboard))

async def quantity_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['type'] = query.data
    keyboard = [
        [InlineKeyboardButton("1 Pcs", callback_data='p_1'), InlineKeyboardButton("3 Pcs", callback_data='p_3')],
        [InlineKeyboardButton("5 Pcs", callback_data='p_5'), InlineKeyboardButton("10 Pcs", callback_data='p_10')]
    ]
    await query.edit_message_text("কত পিস প্রয়োজন?", reply_markup=InlineKeyboardMarkup(keyboard))

async def request_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['qty'] = query.data
    await query.edit_message_text("পেমেন্ট ট্রানজেকশন আইডি (TxID) বা স্ক্রিনশট পাঠান।")

async def handle_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user_id = update.message.from_user.id
    
    admin_msg = f"নতুন অর্ডার!\nইউজার আইডি: {user_id}\nপেমেন্ট প্রুফ: {user_msg}\nধরন: {context.user_data.get('type')}\nপরিমাণ: {context.user_data.get('qty')}"
    
    await context.bot.send_message(ADMIN_ID, admin_msg)
    await update.message.reply_text("আপনার পেমেন্ট রিসিভ হয়েছে, অ্যাডমিন চেক করার পর জিমেইল পাঠিয়ে দেওয়া হবে।")

def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buy_menu, pattern='^buy_menu$'))
    app.add_handler(CallbackQueryHandler(quantity_menu, pattern='^(old|new)$'))
    app.add_handler(CallbackQueryHandler(request_payment, pattern='^p_'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment))
    
    print("বট সচল আছে...")
    app.run_polling()

if __name__ == '__main__':
    main()
