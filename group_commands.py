from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types.input_file import FSInputFile
from datetime import datetime, timedelta
import os

from database import is_ceo, is_admin
from analytics import AnalyticsManager

router = Router()
analytics_manager = AnalyticsManager()

# Список доступных команд
ADMIN_COMMANDS = """
Доступные команды для администраторов:
/stats - Статистика по тикетам
/my_stats - Ваша личная статистика
/open_tickets - Список открытых тикетов
/help - Список команд

Дополнительные команды для CEO:
/admin_stats - Статистика по всем администраторам
/export_day - Экспорт данных за день
/export_week - Экспорт данных за неделю
/export_month - Экспорт данных за месяц
"""

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать список доступных команд"""
    if not await is_admin(message.from_user.id):
        return
    
    await message.answer(ADMIN_COMMANDS)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать общую статистику"""
    if not await is_admin(message.from_user.id):
        return
    
    stats = await analytics_manager.get_tickets_stats('day')
    sla = await analytics_manager.get_sla_metrics()
    
    text = "📊 Статистика за сегодня:\n\n"
    text += f"Всего тикетов: {stats['total']}\n\n"
    text += "По статусам:\n"
    for status, count in stats['statuses'].items():
        text += f"• {status}: {count}\n"
    
    text += f"\nSLA метрики:\n"
    text += f"• Закрыто вовремя: {sla['on_time_percent']}%\n"
    text += f"• Пропущено: {sla['missed_percent']}%"
    
    await message.answer(text)

@router.message(Command("my_stats"))
async def cmd_my_stats(message: Message):
    """Показать статистику администратора"""
    if not await is_admin(message.from_user.id):
        return
    
    admin_stats = await analytics_manager.get_admin_stats(message.from_user.id)
    missed_stats = await analytics_manager.get_missed_responses_stats(message.from_user.id)
    
    if admin_stats:
        stats = admin_stats[0]  # Берем первый элемент, так как запрашиваем для конкретного админа
        text = "📊 Ваша статистика:\n\n"
        text += f"Всего тикетов: {stats['total_tickets']}\n"
        text += f"Среднее время ответа: {stats['avg_response_time'] // 60} минут\n"
        text += f"Пропущено: {stats['missed']}\n"
        if missed_stats:
            text += f"Процент пропусков: {missed_stats[0]['missed_percent']:.1f}%"
        
        await message.answer(text)
    else:
        await message.answer("У вас пока нет статистики")

@router.message(Command("admin_stats"))
async def cmd_admin_stats(message: Message):
    """Показать статистику по всем администраторам (только для CEO)"""
    if not await is_ceo(message.from_user.id):
        return
    
    admin_stats = await analytics_manager.get_admin_stats()
    
    text = "👥 Статистика администраторов:\n\n"
    for stats in admin_stats:
        text += f"Админ @{stats['username']}:\n"
        text += f"• Тикетов: {stats['total_tickets']}\n"
        avg_time = stats.get('avg_response_time', 0)
        if avg_time is not None:
            text += f"• Среднее время ответа: {int(avg_time) // 60} минут\n"
        else:
            text += "• Среднее время ответа: нет данных\n"
        text += f"• Пропущено: {stats['missed']}\n\n"
    
    await message.answer(text)

@router.message(Command("open_tickets"))
async def cmd_open_tickets(message: Message):
    """Показать список открытых тикетов"""
    if not await is_admin(message.from_user.id):
        return
    
    from database import get_open_tickets
    tickets = await get_open_tickets()
    
    if not tickets:
        await message.answer("Нет открытых тикетов")
        return
    
    text = "📝 Открытые тикеты:\n\n"
    for ticket in tickets:
        text += f"Тикет #{ticket['id']}\n"
        text += f"От: {ticket['user_name']}\n"
        text += f"Создан: {ticket['created_at']}\n"
        text += "-------------------\n"
    
    await message.answer(text)

@router.message(Command(commands=["export_day", "export_week", "export_month"]))
async def cmd_export(message: Message):
    """Экспорт данных (только для CEO)"""
    if not await is_ceo(message.from_user.id):
        return
    
    period = message.text.split('_')[1]  # day, week или month
    filename = await analytics_manager.export_to_csv(period)
    
    with open(filename, 'rb') as file:
        await message.answer_document(
            document=FSInputFile(filename),
            caption=f"Экспорт данных за {period}"
        )
    # Удаляем временный файл
    os.remove(filename)

def register_group_handlers(dp: Router):
    """Регистрация обработчиков групповых команд"""
    dp.include_router(router)
