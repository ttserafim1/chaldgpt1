import logging
import subprocess
import os
from collections import deque
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import OpenAI

# Автоматическая установка недостающих пакетов
required_packages = ["openai", "python-telegram-bot"]
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        subprocess.run(["pip", "install", package])

# Данные бота
TELEGRAM_TOKEN = "7978192939:AAGnHNXWhTudLmCfj7Uvz28tbAuAnYClXEs"
BOT_USERNAME = "@YourBotUsername"
OPENROUTER_API_KEY = "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"
MODEL_NAME="google/gemini-2.0-flash-lite-001"
BOT_NAME = "ChaldGPT V5 (beta)"

# Инициализация клиента OpenRouter
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

# Логирование
LOG_FILE = "bot.log"
logging.basicConfig(filename=LOG_FILE, format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Очистка логов, если они больше 10 МБ
if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 10 * 1024 * 1024:
    with open(LOG_FILE, "w") as log:
        log.write("")

# Параметры памяти и лимитов
MESSAGE_HISTORY_LIMIT = 1000
DAILY_MESSAGE_LIMIT = 100
user_message_counts = {}
message_history = deque(maxlen=MESSAGE_HISTORY_LIMIT)

# Проверка лимита сообщений
def check_message_limit(user_id):
    today = datetime.now().date()
    if user_id not in user_message_counts or user_message_counts[user_id]["date"] != today:
        user_message_counts[user_id] = {"date": today, "count": 0}
    
    if user_message_counts[user_id]["count"] >= DAILY_MESSAGE_LIMIT:
        return False
    
    user_message_counts[user_id]["count"] += 1
    return True

async def start(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("🔄 Сменить модель", callback_data="change_model")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        f"🤖 Привет! Я {BOT_NAME} – твой AI-помощник.")
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def status(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    remaining = max(0, DAILY_MESSAGE_LIMIT - user_message_counts.get(user_id, {"count": 0})["count"])
    await update.message.reply_text(f"📊 У вас осталось {remaining} сообщений на сегодня.")

async def reset(update: Update, context: CallbackContext):
    global message_history
    message_history.clear()
    await update.message.reply_text("🗑 История сообщений очищена!")

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_message = update.message.text

    if not check_message_limit(user_id):
        await update.message.reply_text("❌ Вы достигли лимита сообщений на сегодня! Попробуйте завтра.")
        return

    message_history.append(user_message)
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": f"Ты {BOT_NAME}. Отвечай информативно и кратко."},
                {"role": "user", "content": user_message}
            ]
        ).choices[0].message.content
        
        await update.message.reply_text(response)
    except Exception as e:
        logging.error(f"Ошибка: {str(e)}")
        await update.message.reply_text("❌ Ошибка при обработке запроса!")

async def poweroff(update: Update, context: CallbackContext):
    global running
    running = False
    await update.message.reply_text("🔴 Бот выключен.")

async def poweron(update: Update, context: CallbackContext):
    global running
    running = True
    await update.message.reply_text("🟢 Бот включен.")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("poweroff", poweroff))
    application.add_handler(CommandHandler("poweron", poweron))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logging.info("Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
