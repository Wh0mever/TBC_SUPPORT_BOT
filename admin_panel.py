import os
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import (
    is_admin, is_ceo, add_admin, get_all_admins,
    get_admin_tickets, get_open_tickets, get_closed_tickets
)
from analytics import AnalyticsManager
from keyboards import get_admin_keyboard

# Создаем роутер
router = Router()

# Состояния FSM
class AdminManagement(StatesGroup):
    waiting_for_admin_id = State()

# Инициализация менеджера аналитики
analytics_manager = AnalyticsManager()

# Обработчик команды /admin
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к админ-панели.")
        return

    is_ceo_user = await is_ceo(message.from_user.id)
    keyboard = get_admin_keyboard(is_ceo=is_ceo_user)
    
    await message.answer(
        "Панель управления:",
        reply_markup=keyboard
    )

# Обработчик просмотра тикетов
@router.callback_query(lambda c: c.data in ['my_tickets', 'open_tickets', 'closed_tickets'])
async def process_tickets_view(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    if callback.data == 'my_tickets':
        tickets = await get_admin_tickets(callback.from_user.id)
        title = "Мои тикеты"
    elif callback.data == 'open_tickets':
        tickets = await get_open_tickets()
        title = "Открытые тикеты"
    else:
        tickets = await get_closed_tickets()
        title = "Закрытые тикеты"

    if not tickets:
        await callback.message.answer(f"{title}: нет тикетов")
        return

    for ticket in tickets:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Ответить",
                        callback_data=f"reply:{ticket['id']}"
                    ),
                    InlineKeyboardButton(
                        text="Закрыть",
                        callback_data=f"close:{ticket['id']}"
                    )
                ]
            ]
        )
        
        text = (
            f"Тикет #{ticket['id']}\n"
            f"Статус: {ticket['status']}\n"
            f"Приоритет: {ticket['priority']}\n"
            f"Создан: {ticket['created_at']}\n"
            f"От: {ticket['user_name']}"
        )
        
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

# Обработчик просмотра аналитики
@router.callback_query(lambda c: c.data == 'analytics')
async def process_analytics(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    # Получаем статистику
    stats = await analytics_manager.get_tickets_stats('day')
    admin_stats = await analytics_manager.get_admin_stats(
        callback.from_user.id if not await is_ceo(callback.from_user.id) else None
    )
    sla = await analytics_manager.get_sla_metrics()

    # Формируем текст отчета
    text = "📊 Аналитика:\n\n"
    text += f"Всего тикетов за день: {stats['total']}\n"
    text += "\nСтатусы тикетов:\n"
    for status, count in stats['statuses'].items():
        text += f"- {status}: {count}\n"
    
    text += "\nSLA метрики:\n"
    text += f"Закрыто вовремя: {sla['on_time_percent']}%\n"
    text += f"Пропущено: {sla['missed_percent']}%\n"

    if await is_ceo(callback.from_user.id):
        # Добавляем кнопки экспорта для CEO
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Экспорт (день)",
                        callback_data="export:day"
                    ),
                    InlineKeyboardButton(
                        text="Экспорт (неделя)",
                        callback_data="export:week"
                    ),
                    InlineKeyboardButton(
                        text="Экспорт (месяц)",
                        callback_data="export:month"
                    )
                ]
            ]
        )
    else:
        keyboard = None

    # Отправляем график активности
    chart = await analytics_manager.generate_hourly_chart()
    await callback.message.answer_photo(
        photo=chart,
        caption=text,
        reply_markup=keyboard
    )

    await callback.answer()

# Обработчик экспорта данных
@router.callback_query(lambda c: c.data.startswith('export:'))
async def process_export(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id):
        await callback.answer("У вас нет прав CEO")
        return

    period = callback.data.split(':')[1]
    filename = await analytics_manager.export_to_csv(period)
    
    with open(filename, 'rb') as file:
        await callback.message.answer_document(
            document=file,
            caption=f"Экспорт данных за {period}"
        )
    
    # Удаляем временный файл
    os.remove(filename)
    await callback.answer()

# Управление администраторами (только для CEO)
@router.callback_query(lambda c: c.data == 'manage_admins')
async def process_manage_admins(callback: CallbackQuery, state: FSMContext):
    if not await is_ceo(callback.from_user.id):
        await callback.answer("У вас нет прав CEO")
        return

    admins = await get_all_admins()
    
    text = "Список администраторов:\n\n"
    for admin in admins:
        text += f"- @{admin['username']} ({admin['role']})\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Добавить админа",
                    callback_data="add_admin"
                )
            ]
        ]
    )
    
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()

# Обработчик добавления админа
@router.callback_query(lambda c: c.data == 'add_admin')
async def process_add_admin(callback: CallbackQuery, state: FSMContext):
    if not await is_ceo(callback.from_user.id):
        await callback.answer("У вас нет прав CEO")
        return

    await callback.message.answer(
        "Отправьте Telegram ID нового администратора:"
    )
    await state.set_state(AdminManagement.waiting_for_admin_id)
    await callback.answer()

# Обработчик получения ID нового админа
@router.message(AdminManagement.waiting_for_admin_id)
async def process_admin_id(message: Message, state: FSMContext):
    if not await is_ceo(message.from_user.id):
        await message.answer("У вас нет прав CEO")
        return

    try:
        admin_id = int(message.text)
        success = await add_admin(admin_id, "admin")
        
        if success:
            await message.answer("Администратор успешно добавлен!")
        else:
            await message.answer("Ошибка при добавлении администратора.")
    except ValueError:
        await message.answer("Некорректный ID. Попробуйте снова.")
    
    await state.clear()

def register_admin_handlers(dp: Router):
    """Регистрация обработчиков админ-панели"""
    dp.include_router(router)
