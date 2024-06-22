import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext

# توکن ربات خود را اینجا قرار دهید
TOKEN = '6827525276:AAGjDkwDw7TrB0sC9LK0DKfYKtig4Isb-po'

# ایجاد یا اتصال به دیتابیس SQLite
def create_connection():
    conn = sqlite3.connect('crypto_wallet.db', check_same_thread=False)
    return conn

# ایجاد جدول برای ذخیره اطلاعات کاربران
def setup_database():
    conn = create_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, username TEXT, seats INTEGER, password TEXT, balance REAL, join_date TEXT, last_reward_date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, date TEXT)''')
    conn.commit()
    conn.close()

def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    conn = create_connection()
    c = conn.cursor()

    # بررسی وجود کاربر در دیتابیس
    c.execute('SELECT password FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result is None:
        # اگر کاربر وجود ندارد، درخواست رمز
        update.message.reply_text('🔒 لطفاً یک رمز برای حساب خود وارد کنید:')
        context.user_data['awaiting_password'] = True
    else:
        # اگر کاربر وجود دارد، درخواست رمز فعلی
        update.message.reply_text('🔒 لطفاً رمز خود را وارد کنید:')
        context.user_data['awaiting_existing_password'] = True

    conn.close()

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "بدون نام کاربری"
    text = update.message.text
    conn = create_connection()
    c = conn.cursor()

    if context.user_data.get('awaiting_password'):
        # ذخیره رمز جدید
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('INSERT INTO users (user_id, username, seats, password, balance, join_date, last_reward_date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  (user_id, username, 0, text, 0.0, join_date, ''))
        conn.commit()
        update.message.reply_text('✅ رمز شما ذخیره شد. می‌توانید از ربات استفاده کنید.')
        del context.user_data['awaiting_password']
        show_main_menu(update)
    elif context.user_data.get('awaiting_existing_password'):
        # بررسی رمز فعلی
        c.execute('SELECT password FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        if result and result[0] == text:
            update.message.reply_text('✅ رمز صحیح است. می‌توانید از ربات استفاده کنید.')
            show_main_menu(update)
        else:
            update.message.reply_text('❌ رمز اشتباه است. لطفاً دوباره تلاش کنید.')
        del context.user_data['awaiting_existing_password']

    conn.close()

def show_main_menu(update: Update):
    keyboard = [
        [InlineKeyboardButton("🛠 استخراج سیت", callback_data='extract_seat')],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data='user_account')],
        [InlineKeyboardButton("🎁 پاداش روزانه", callback_data='daily_reward')],
        [InlineKeyboardButton("📨 دعوت دوستان", callback_data='invite_friends')],
        [InlineKeyboardButton("🏆 رتبه‌بندی کاربران", callback_data='leaderboard')],
        [InlineKeyboardButton("📜 تاریخچه تراکنش‌ها", callback_data='transaction_history')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('📜 *منوی اصلی*', reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "بدون نام کاربری"
    
    conn = create_connection()
    c = conn.cursor()

    # بررسی وجود کاربر در دیتابیس
    c.execute('SELECT seats, balance, join_date, last_reward_date FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result is None:
        join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('INSERT INTO users (user_id, username, seats, password, balance, join_date, last_reward_date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                  (user_id, username, 0, '', 0.0, join_date, ''))
        conn.commit()
        result = (0, 0.0, join_date, '')
    seats, balance, join_date, last_reward_date = result

    if query.data == 'extract_seat':
        keyboard = [
            [InlineKeyboardButton("💎 استخراج سیت 💎", callback_data='do_extract_seat')],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text="برای استخراج سیت روی دکمه زیر کلیک کنید:", reply_markup=reply_markup)
    
    elif query.data == 'do_extract_seat':
        new_seat = seats + 1
        c.execute('UPDATE users SET seats = ? WHERE user_id = ?', (new_seat, user_id))
        conn.commit()
        c.execute('INSERT INTO transactions (user_id, type, amount, date) VALUES (?, ?, ?, ?)', 
                  (user_id, 'extract', 1, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        query.answer(text="💎 یک سیت به حساب شما اضافه شد ✅", show_alert=True)
        query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 استخراج سیت 💎", callback_data='do_extract_seat')],
                                                                           [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_menu')]]))
        
    elif query.data == 'user_account':
        query.edit_message_text(
            text=f"👤 *حساب کاربری*\n\n"
                 f"💳 تعداد سیت‌ها: {seats}\n"
                 f"💰 موجودی: {balance} سکه\n"
                 f"📅 تاریخ عضویت: {join_date}\n"
                 f"🎁 آخرین دریافت پاداش: {last_reward_date}",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == 'daily_reward':
        if not last_reward_date:
            last_reward_date_obj = datetime.min
        else:
            last_reward_date_obj = datetime.strptime(last_reward_date, "%Y-%m-%d %H:%M:%S")
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if last_reward_date_obj < today:
            new_balance = balance + 10
            c.execute('UPDATE users SET balance = ?, last_reward_date = ? WHERE user_id = ?', 
                      (new_balance, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
            conn.commit()
            query.answer(text="پاداش روزانه 10 سیت به حساب شما افزوده شد✅")
            query.edit_message_text(text="🎁 *پاداش روزانه*\n\n"
                                          "10 سیت به حساب شما افزوده شد✅\n\n"
                                          "می‌توانید هر روز برای دریافت پاداش مراجعه کنید.",
                                    parse_mode=ParseMode.MARKDOWN)
        else:
            query.answer(text="شما قبلاً امروز پاداش روزانه خود را دریافت کرده‌اید.")
    elif query.data == 'invite_friends':
        query.edit_message_text(
            text="📨 *دعوت دوستان*\n\n"
                 "لینک دعوت خود را به دوستانتان ارسال کنید تا برای هر دوستی که با لینک شما به ربات ملحق شود، 5 سیت به حساب شما اضافه شود.",
            parse_mode=ParseMode.MARKDOWN
        )
    elif query.data == 'leaderboard':
        c.execute('SELECT username, seats FROM users ORDER BY seats DESC LIMIT 10')
        users = c.fetchall()
        leaderboard_text = "🏆 *رتبه‌بندی کاربران*\n\n"
        for i, user in enumerate(users, start=1):
            leaderboard_text += f"{i}. {user[0]} - {user[1]} سیت\n"
        query.edit_message_text(text=leaderboard_text, parse_mode=ParseMode.MARKDOWN)
    elif query.data == 'transaction_history':
        c.execute('SELECT type, amount, date FROM transactions WHERE user_id = ? ORDER BY date DESC LIMIT 5', (user_id,))
        transactions = c.fetchall()
        if transactions:
            transactions_text = "📜 *تاریخچه تراکنش‌ها*\n\n"
            for transaction in transactions:
                transactions_text += f"🔹 {transaction[0]}: {transaction[1]} سیت - {transaction[2]}\n"
        else:
            transactions_text = "تراکنشی یافت نشد."
        query.edit_message_text(text=transactions_text, parse_mode=ParseMode.MARKDOWN)
    elif query.data == 'back_to_menu':
        show_main_menu(update)

    conn.close()

def main():
    setup_database()
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(button))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
