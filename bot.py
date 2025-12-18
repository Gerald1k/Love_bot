import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

load_dotenv()

from handlers.registration import start, stop, handle_partner_username, setup_commands
from handlers.wishlist import add_gift_handler, find_gift_for_partner, handle_price_selection, my_wishlist, handle_my_wishlist, delete_gift, edit_gift_handler, mark_gifted, gifted_menu, handle_gifted_history


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен")

    app = Application.builder().token(token).build()
    app.post_init = setup_commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(add_gift_handler)
    app.add_handler(MessageHandler(filters.Regex("^💝 Подобрать подарок для партнёра$"), find_gift_for_partner))
    app.add_handler(MessageHandler(filters.Regex("^📋 Мой вишлист$"), my_wishlist))
    app.add_handler(MessageHandler(filters.Regex("^🎀 Подарено$"), gifted_menu))
    app.add_handler(CallbackQueryHandler(handle_price_selection, pattern="^price_"))
    app.add_handler(CallbackQueryHandler(handle_my_wishlist, pattern="^mywish_"))
    app.add_handler(CallbackQueryHandler(delete_gift, pattern="^delete_"))
    app.add_handler(CallbackQueryHandler(handle_gifted_history, pattern="^gifted_to_me$|^gifted_by_me$"))
    app.add_handler(CallbackQueryHandler(mark_gifted, pattern="^gifted_"))
    app.add_handler(edit_gift_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_partner_username))
    
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
