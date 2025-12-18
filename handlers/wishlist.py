import random
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from database import users_collection, gifts_collection

# Состояния для ConversationHandler
NAME, PRICE, LINK, DESCRIPTION, CONFIRM = range(5)


async def add_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎁 Давай добавим подарок в твой вишлист!\n\n"
        "Введи название подарка:"
    )
    return NAME


async def gift_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gift_name"] = update.message.text.strip()
    await update.message.reply_text("💰 Введи примерную цену:")
    return PRICE


async def gift_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    price = parse_price(text)
    
    if price == 0:
        await update.message.reply_text("❌ Введи корректную цену (число):")
        return PRICE
    
    context.user_data["gift_price"] = text
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip_link")]
    ])
    await update.message.reply_text(
        "🔗 Отправь ссылку на товар:",
        reply_markup=keyboard
    )
    return LINK


async def gift_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gift_link"] = update.message.text.strip()
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip_description")]
    ])
    await update.message.reply_text(
        "📝 Добавь описание подарка:",
        reply_markup=keyboard
    )
    return DESCRIPTION


async def skip_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["gift_link"] = None
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏭ Пропустить", callback_data="skip_description")]
    ])
    await query.edit_message_text(
        "📝 Добавь описание подарка:",
        reply_markup=keyboard
    )
    return DESCRIPTION


async def gift_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gift_description"] = update.message.text.strip()
    return await show_gift_summary(update, context)


async def skip_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["gift_description"] = None
    return await show_gift_summary(update, context, edit_message=query)


async def show_gift_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=None):
    name = context.user_data["gift_name"]
    price = context.user_data["gift_price"]
    link = context.user_data.get("gift_link") or "—"
    description = context.user_data.get("gift_description") or "—"
    
    summary = (
        "📋 Проверь данные подарка:\n\n"
        f"🎁 Название: {name}\n"
        f"💰 Цена: {price}\n"
        f"🔗 Ссылка: {link}\n"
        f"📝 Описание: {description}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Сохранить", callback_data="gift_save"),
            InlineKeyboardButton("✏️ Изменить", callback_data="gift_edit"),
            InlineKeyboardButton("❌ Отменить", callback_data="gift_cancel")
        ]
    ])
    
    if edit_message:
        await edit_message.edit_message_text(summary, reply_markup=keyboard)
    else:
        await update.message.reply_text(summary, reply_markup=keyboard)
    return CONFIRM


async def gift_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "gift_save":
        user = users_collection.find_one({"telegram_id": update.effective_user.id})
        
        gifts_collection.insert_one({
            "user_id": user["_id"],
            "name": context.user_data["gift_name"],
            "price": context.user_data["gift_price"],
            "link": context.user_data.get("gift_link"),
            "description": context.user_data.get("gift_description")
        })
        
        await query.edit_message_text("✅ Подарок сохранён в твой вишлист! 🎉")
        
        # Уведомляем партнёра
        if user.get("partner_id"):
            try:
                await context.bot.send_message(
                    chat_id=user["partner_id"],
                    text="💕 У твоей половинки новое желание! Загляни в бот 🎁"
                )
            except Exception:
                pass  # Партнёр заблокировал бота или другая ошибка
        
        context.user_data.clear()
        return ConversationHandler.END
    
    elif action == "gift_edit":
        await query.edit_message_text(
            "✏️ Начнём заново!\n\n"
            "Введи название подарка:"
        )
        return NAME
    
    elif action == "gift_cancel":
        await query.edit_message_text("❌ Добавление подарка отменено")
        context.user_data.clear()
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Добавление подарка отменено")
    return ConversationHandler.END


# ConversationHandler для добавления подарка
add_gift_handler = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^🎁 Добавить свой подарок$"), add_gift)],
    per_message=False,
    states={
        NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_name)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, gift_price)],
        LINK: [
            CallbackQueryHandler(skip_link, pattern="^skip_link$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, gift_link)
        ],
        DESCRIPTION: [
            CallbackQueryHandler(skip_description, pattern="^skip_description$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, gift_description)
        ],
        CONFIRM: [CallbackQueryHandler(gift_confirm, pattern="^gift_")]
    },
    fallbacks=[MessageHandler(filters.COMMAND, cancel)]
)


async def find_gift_for_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = users_collection.find_one({"telegram_id": update.effective_user.id})
    
    if not user or not user.get("partner_id"):
        await update.message.reply_text("❌ Сначала привяжи партнёра!")
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("До 1000₽", callback_data="price_0_1000")],
        [InlineKeyboardButton("1000 - 5000₽", callback_data="price_1000_5000")],
        [InlineKeyboardButton("5000 - 10000₽", callback_data="price_5000_10000")],
        [InlineKeyboardButton("Больше 10000₽", callback_data="price_10000_999999")]
    ])
    
    await update.message.reply_text(
        "💰 Выбери диапазон цены:",
        reply_markup=keyboard
    )


def parse_price(price_str: str) -> int:
    """Извлекает число из строки цены"""
    if not price_str:
        return 0
    numbers = re.findall(r'\d+', price_str.replace(" ", ""))
    if numbers:
        return int(numbers[0])
    return 0


async def handle_price_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Парсим диапазон из callback_data
    _, min_price, max_price = query.data.split("_")
    min_price, max_price = int(min_price), int(max_price)
    
    user = users_collection.find_one({"telegram_id": update.effective_user.id})
    partner = users_collection.find_one({"telegram_id": user["partner_id"]})
    
    if not partner:
        await query.edit_message_text("❌ Партнёр не найден")
        return
    
    # Получаем все подарки партнёра
    partner_gifts = list(gifts_collection.find({"user_id": partner["_id"]}))
    
    if not partner_gifts:
        await query.edit_message_text(
            f"😔 У @{partner.get('username', 'партнёра')} пока нет подарков в вишлисте"
        )
        return
    
    # Фильтруем по цене и исключаем подаренные
    filtered_gifts = []
    for gift in partner_gifts:
        if gift.get("gifted"):
            continue
        price = parse_price(gift.get("price", "0"))
        if min_price <= price <= max_price:
            filtered_gifts.append(gift)
    
    if not filtered_gifts:
        await query.edit_message_text(
            f"😔 Нет подарков в диапазоне {min_price} - {max_price}₽\n\n"
            "Попробуй другой диапазон!"
        )
        return
    
    # Выбираем случайный подарок
    gift = random.choice(filtered_gifts)
    
    link_text = f"\n🔗 Ссылка: {gift['link']}" if gift.get("link") else ""
    desc_text = f"\n📝 {gift['description']}" if gift.get("description") else ""
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎀 Подарено!", callback_data=f"gifted_{gift['_id']}")]
    ])
    
    await query.edit_message_text(
        f"🎁 Вот что хочет твой партнёр:\n\n"
        f"✨ {gift['name']}\n"
        f"💰 {gift.get('price', '—')}"
        f"{link_text}"
        f"{desc_text}",
        reply_markup=keyboard
    )


async def my_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Все", callback_data="mywish_0_999999999")],
        [InlineKeyboardButton("До 1000₽", callback_data="mywish_0_1000")],
        [InlineKeyboardButton("1000 - 5000₽", callback_data="mywish_1000_5000")],
        [InlineKeyboardButton("5000 - 10000₽", callback_data="mywish_5000_10000")],
        [InlineKeyboardButton("Больше 10000₽", callback_data="mywish_10000_999999999")]
    ])
    
    await update.message.reply_text(
        "💰 Выбери диапазон цены:",
        reply_markup=keyboard
    )


async def handle_my_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, min_price, max_price = query.data.split("_")
    min_price, max_price = int(min_price), int(max_price)
    
    user = users_collection.find_one({"telegram_id": update.effective_user.id})
    
    if not user:
        await query.edit_message_text("❌ Пользователь не найден")
        return
    
    my_gifts = list(gifts_collection.find({"user_id": user["_id"]}))
    
    if not my_gifts:
        await query.edit_message_text("😔 Твой вишлист пуст. Добавь подарки!")
        return
    
    # Фильтруем по цене
    filtered_gifts = []
    for gift in my_gifts:
        price = parse_price(gift.get("price", "0"))
        if min_price <= price <= max_price:
            filtered_gifts.append(gift)
    
    if not filtered_gifts:
        await query.edit_message_text(
            f"😔 Нет подарков в этом диапазоне\n\n"
            "Попробуй другой!"
        )
        return
    
    await query.edit_message_text("📋 Твой вишлист:")
    
    for gift in filtered_gifts:
        link_text = f"\n🔗 {gift['link']}" if gift.get("link") else ""
        desc_text = f"\n📝 {gift['description']}" if gift.get("description") else ""
        
        text = (
            f"🎁 {gift['name']}\n"
            f"💰 {gift.get('price', '—')}"
            f"{link_text}"
            f"{desc_text}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{gift['_id']}"),
                InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{gift['_id']}")
            ]
        ])
        
        await query.message.reply_text(text, reply_markup=keyboard)


async def delete_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = query.data.replace("delete_", "")
    
    from bson import ObjectId
    gifts_collection.delete_one({"_id": ObjectId(gift_id)})
    
    await query.edit_message_text("🗑 Подарок удалён")


async def mark_gifted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = query.data.replace("gifted_", "")
    
    from bson import ObjectId
    gifts_collection.update_one(
        {"_id": ObjectId(gift_id)},
        {"$set": {
            "gifted": True,
            "gifted_by": update.effective_user.id
        }}
    )
    
    await query.edit_message_text("🎀 Отмечено как подаренное! Твой партнёр будет рад 💕")


async def gifted_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Что мне подарили", callback_data="gifted_to_me")],
        [InlineKeyboardButton("💝 Что я подарил(а)", callback_data="gifted_by_me")]
    ])
    
    await update.message.reply_text(
        "🎀 Что хочешь посмотреть?",
        reply_markup=keyboard
    )


async def handle_gifted_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = users_collection.find_one({"telegram_id": update.effective_user.id})
    
    if query.data == "gifted_to_me":
        # Подарки которые мне подарили (мои подарки с флагом gifted)
        gifts = list(gifts_collection.find({"user_id": user["_id"], "gifted": True}))
        
        if not gifts:
            await query.edit_message_text("😔 Пока тебе ничего не подарили")
            return
        
        await query.edit_message_text("🎁 Тебе подарили:")
        
        for gift in gifts:
            text = f"✨ {gift['name']} — {gift.get('price', '—')}"
            await query.message.reply_text(text)
    
    elif query.data == "gifted_by_me":
        # Подарки которые я подарил (чужие подарки где gifted_by = мой id)
        gifts = list(gifts_collection.find({"gifted_by": update.effective_user.id}))
        
        if not gifts:
            await query.edit_message_text("😔 Ты пока ничего не дарил(а)")
            return
        
        await query.edit_message_text("💝 Ты подарил(а):")
        
        for gift in gifts:
            text = f"✨ {gift['name']} — {gift.get('price', '—')}"
            await query.message.reply_text(text)


async def edit_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    gift_id = query.data.replace("edit_", "")
    context.user_data["edit_gift_id"] = gift_id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Название", callback_data="editfield_name")],
        [InlineKeyboardButton("Цена", callback_data="editfield_price")],
        [InlineKeyboardButton("Ссылка", callback_data="editfield_link")],
        [InlineKeyboardButton("Описание", callback_data="editfield_description")],
        [InlineKeyboardButton("❌ Отмена", callback_data="editfield_cancel")]
    ])
    
    await query.edit_message_text("Что изменить?", reply_markup=keyboard)
    return ConversationHandler.WAITING


async def edit_field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    field = query.data.replace("editfield_", "")
    
    if field == "cancel":
        await query.edit_message_text("❌ Редактирование отменено")
        return ConversationHandler.END
    
    context.user_data["edit_field"] = field
    field_names = {"name": "название", "price": "цену", "link": "ссылку", "description": "описание"}
    
    await query.edit_message_text(f"Введи новое {field_names[field]}:")
    return "EDIT_VALUE"


async def edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bson import ObjectId
    
    gift_id = context.user_data.get("edit_gift_id")
    field = context.user_data.get("edit_field")
    value = update.message.text.strip()
    
    if field == "price":
        if parse_price(value) == 0:
            await update.message.reply_text("❌ Введи корректную цену:")
            return "EDIT_VALUE"
    
    gifts_collection.update_one(
        {"_id": ObjectId(gift_id)},
        {"$set": {field: value}}
    )
    
    await update.message.reply_text("✅ Подарок обновлён!")
    context.user_data.pop("edit_gift_id", None)
    context.user_data.pop("edit_field", None)
    return ConversationHandler.END


edit_gift_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_gift, pattern="^edit_")],
    per_message=False,
    states={
        ConversationHandler.WAITING: [CallbackQueryHandler(edit_field_select, pattern="^editfield_")],
        "EDIT_VALUE": [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)]
    },
    fallbacks=[MessageHandler(filters.COMMAND, cancel)]
)
