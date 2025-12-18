from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.ext import ContextTypes

from database import users_collection

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["🎁 Добавить свой подарок"], 
        ["💝 Подобрать подарок для партнёра"],
        ["📋 Мой вишлист"],
        ["🎀 Подарено"]
    ],
    resize_keyboard=True
)


async def setup_commands(app):
    """Устанавливает команды в меню бота"""
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("stop", "Остановить и сбросить")
    ]
    await app.bot.set_my_commands(commands)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name or user.username or "друг"
    
    # Проверяем есть ли пользователь
    existing_user = users_collection.find_one({"telegram_id": user.id})
    
    if not existing_user:
        users_collection.insert_one({
            "telegram_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "partner_username": None,
            "partner_id": None
        })
    
    # Если партнёр уже привязан
    if existing_user and existing_user.get("partner_username"):
        await update.message.reply_text(
            f"✨ С возвращением, {name}! ✨\n\n"
            f"Твой партнёр: @{existing_user['partner_username']} 💑",
            reply_markup=MAIN_MENU
        )
        return
    
    welcome_text = (
        f"✨ Привет, {name}! ✨\n\n"
        "Рад тебя видеть! 💕\n\n"
        "Я — бот для создания вишлистов подарков. "
        "С моей помощью вы с партнёром сможете делиться желаниями "
        "и радовать друг друга идеальными подарками 🎁\n\n"
        "📌 Для правильной работы попроси своего партнёра "
        "зайти в бот и нажать /start\n\n"
        "После этого отправь мне его @username 💑"
    )
    
    await update.message.reply_text(welcome_text)


async def handle_partner_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    
    # Проверяем что пользователь зарегистрирован
    existing_user = users_collection.find_one({"telegram_id": user.id})
    if not existing_user:
        await update.message.reply_text("Отправь /start чтобы начать!")
        return
    
    # Если партнёр уже есть — игнорируем сообщение (меню обработает другой хендлер)
    if existing_user.get("partner_username"):
        return
    
    # Проверяем формат username
    if text.startswith("@"):
        partner_username = text[1:]  # убираем @
    else:
        partner_username = text
    
    # Валидация username
    if not partner_username or len(partner_username) < 3:
        await update.message.reply_text("❌ Отправь корректный @username партнёра")
        return
    
    # Ищем партнёра в базе по username
    partner = users_collection.find_one({"username": partner_username})
    
    if not partner:
        await update.message.reply_text(
            f"❌ Пользователь @{partner_username} не найден в боте.\n\n"
            "Попросите партнёра сначала зайти в бот и нажать /start"
        )
        return
    
    # Сохраняем партнёра
    users_collection.update_one(
        {"telegram_id": user.id},
        {"$set": {
            "partner_username": partner_username,
            "partner_id": partner["telegram_id"]
        }}
    )
    
    await update.message.reply_text(
        f"✅ Отлично! Партнёр @{partner_username} сохранён! 💕\n\n"
        "Теперь вы можете создавать вишлисты для друг друга 🎁",
        reply_markup=MAIN_MENU
    )


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "⏹ Все процессы остановлены.\n\n"
        "Нажми /start чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )

