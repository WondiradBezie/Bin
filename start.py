import os
import asyncio
import logging
import uvicorn
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
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
    bot.add_handler(CallbackQueryHandler(service.button_callback))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, service.message_handler))
    return bot

async def set_webhook(bot):
    # FIX: Use TELEGRAM_WEBHOOK_URL if it exists, otherwise fall back to WEBAPP_URL
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL") or os.getenv("WEBAPP_URL")
    
    if not webhook_url:
        logger.error("❌ CRITICAL: Neither TELEGRAM_WEBHOOK_URL nor WEBAPP_URL is set!")
        return False
        
    if not webhook_url.endswith("/api/webhook"):
        webhook_url = webhook_url.rstrip("/") + "/api/webhook"
        
    secret_token = os.getenv("TELEGRAM_SECRET_TOKEN")
    
    try:
        logger.info(f"🔄 Deleting old webhooks...")
        await bot.bot.delete_webhook(drop_pending_updates=True)
        
        logger.info(f"🚀 Setting new webhook to: {webhook_url}")
        await bot.bot.set_webhook(
            url=webhook_url,
            secret_token=secret_token,
            allowed_updates=["message", "callback_query"],
        )
        logger.info(f"✅ Webhook successfully set to {webhook_url}")
        return True
    except Exception as e:
        logger.error(f"❌ Webhook setup failed: {e}")
        return False

async def main():
    logger.info("Starting JOY BINGO...")
    
    # 1. Initialize Database
    await service.db.init_pool()
    logger.info("✅ Database initialized")
    
    # 2. Build and Start Bot
    bot = build_bot()
    service.bot_app = bot
    await bot.initialize()
    await bot.start()
    
    # 3. Set Webhook (NO POLLING FALLBACK)
    webhook_success = await set_webhook(bot)
    if not webhook_success:
        logger.error("❌ Failed to set webhook. Please check your WEBAPP_URL environment variable.")
        # We intentionally DO NOT fall back to polling to prevent the 409 Conflict error
        
    # 4. Start FastAPI Server
    port = int(os.getenv("PORT", "8000"))
    config = uvicorn.Config(service.app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    finally:
        # Cleanup on shutdown
        logger.info("🛑 Shutting down...")
        await bot.bot.delete_webhook()
        if bot.updater and bot.updater.running:
            await bot.updater.stop()
        await bot.stop()
        await bot.shutdown()
        if service.db.pool:
            await service.db.pool.close()

if __name__ == "__main__":
    asyncio.run(main())
