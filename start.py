"""Production launcher for JOY BINGO.

Starts both FastAPI/Uvicorn and the Telegram bot polling loop
in the same asyncio event loop.
"""

import asyncio
import logging
import os

import uvicorn
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import free_deploy as service


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
)

logger = logging.getLogger("joybingo.start")


def build_bot():
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("BOT_TOKEN is required")

    bot = Application.builder().token(token).build()

    # Commands
    bot.add_handler(CommandHandler("start", service.start_command))
    bot.add_handler(CommandHandler("register", service.register_command))
    bot.add_handler(CommandHandler("about", service.about_command))
    bot.add_handler(CommandHandler("help", service.help_command))
    bot.add_handler(CommandHandler("admin", service.admin_command))
    bot.add_handler(CommandHandler("id", service.id_command))
    bot.add_handler(CommandHandler("play", service.play_command))
    bot.add_handler(CommandHandler("balance", service.balance_command))
    bot.add_handler(CommandHandler("deposit", service.deposit_command))
    bot.add_handler(CommandHandler("withdraw", service.withdraw_command))
    bot.add_handler(CommandHandler("profile", service.profile_command))
    bot.add_handler(CommandHandler("rules", service.rules_command))

    # Inline keyboard buttons
    bot.add_handler(
        CallbackQueryHandler(service.button_callback)
    )

    # Normal text messages
    bot.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            service.message_handler,
        )
    )

    return bot


async def main():

    logger.info("Starting JOY BINGO...")

    # Initialize PostgreSQL
    await service.db.init_pool()
    logger.info("✅ Database initialized")

    # Create Telegram application
    bot = build_bot()

    # Make it available to free_deploy.py
    service.bot_app = bot

    # Start Telegram
    await bot.initialize()
    await bot.start()

    await bot.updater.start_polling(
        drop_pending_updates=True
    )

    logger.info("✅ Telegram bot polling started")

    # Start FastAPI/Uvicorn
    port = int(os.getenv("PORT", "8000"))

    config = uvicorn.Config(
        service.app,
        host="0.0.0.0",
        port=port,
        log_level="info",
    )

    server = uvicorn.Server(config)

    try:
        await server.serve()

    finally:
        logger.info("Stopping JOY BINGO...")

        if bot.updater and bot.updater.running:
            await bot.updater.stop()

        if bot.running:
            await bot.stop()

        await bot.shutdown()

        if service.db.pool:
            await service.db.pool.close()

        logger.info("JOY BINGO stopped")


if __name__ == "__main__":
    asyncio.run(main())
