import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import register_all_handlers, init_managers
from admin_panel import register_admin_handlers
from group_commands import register_group_handlers
from database import init_db
from analytics import AnalyticsManager
from missed_responses import MissedResponsesChecker
from init_data import init_ceo_admins

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Проверка наличия необходимых переменных окружения
if not os.getenv('BOT_TOKEN'):
    raise ValueError("BOT_TOKEN не найден в .env файле")

async def check_missed_responses(bot: Bot):
    """Проверка пропущенных ответов"""
    from handlers import notification_manager
    if notification_manager:
        checker = MissedResponsesChecker(notification_manager)
        await checker.check_missed_responses()

async def main():
    # Получаем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    logger.info(f"Используется токен бота: {bot_token[:10]}...")
    
    # Инициализация бота и диспетчера
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных
    await init_db()
    
    # Инициализация CEO администраторов
    await init_ceo_admins()

    # Инициализация менеджеров
    init_managers(bot)

    # Инициализация планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_missed_responses,
        'interval',
        minutes=1,
        args=[bot]
    )
    scheduler.start()

    # Регистрация всех хендлеров
    register_all_handlers(dp)
    register_admin_handlers(dp)
    register_group_handlers(dp)

    # Запуск бота
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main())
