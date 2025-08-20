import json
from typing import Union
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import (
    add_user, get_user, create_ticket, get_ticket,
    update_ticket_status, is_admin, is_ceo, get_all_admins,
    add_admin
)
from keyboards import (
    get_contact_keyboard, get_ticket_actions_keyboard,
    get_admin_keyboard, get_ticket_priority_keyboard,
    get_ticket_close_keyboard
)
from messages import MessageManager
from notifications import NotificationManager

# Создаем роутер
router = Router()

# Импорт состояний
from states import UserRegistration, TicketResponse, AdminManagement

# Инициализация менеджеров
message_manager = MessageManager()
notification_manager: NotificationManager = None

def init_managers(bot: Bot):
    """Инициализация менеджеров"""
    global notification_manager
    notification_manager = NotificationManager(bot)

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    from init_data import check_admin_role
    
    # Проверяем роль пользователя
    role = await check_admin_role(message.from_user.id)
    
    if role == "CEO":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Панель управления",
                        callback_data="admin_panel"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="Добавить администратора",
                        callback_data="add_admin"
                    )
                ]
            ]
        )
        await message.answer(
            f"Добро пожаловать, руководитель!\n\n"
            f"Вы имеете полный доступ к управлению системой поддержки.\n"
            f"Используйте панель управления для:\n"
            f"• Просмотра статистики\n"
            f"• Управления администраторами\n"
            f"• Работы с тикетами",
            reply_markup=keyboard
        )
        return
    elif role == "admin":
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Панель управления",
                        callback_data="admin_panel"
                    )
                ]
            ]
        )
        await message.answer(
            f"Добро пожаловать, администратор!\n\n"
            f"Вы можете:\n"
            f"• Просматривать тикеты\n"
            f"• Отвечать на обращения\n"
            f"• Видеть свою статистику",
            reply_markup=keyboard
        )
        return
    
    # Для обычных пользователей
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer(
            "Добро пожаловать в службу поддержки! Для начала работы, пожалуйста, "
            "предоставьте свой контактный номер телефона.",
            reply_markup=get_contact_keyboard()
        )
        await state.set_state(UserRegistration.waiting_for_contact)
    else:
        await message.answer(
            "Вы уже зарегистрированы. Отправьте сообщение, чтобы создать тикет."
        )

# Обработчик получения контакта
@router.message(UserRegistration.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext):
    contact = message.contact
    
    success = await add_user(
        user_id=message.from_user.id,
        username=message.from_user.username or "No username",
        full_name=message.from_user.first_name,
        phone=contact.phone_number
    )
    
    if success:
        await message.answer(
            "Спасибо за регистрацию! Теперь вы можете отправить свой вопрос.",
            reply_markup=None
        )
        await state.clear()
    else:
        await message.answer(
            "Произошла ошибка при регистрации. Пожалуйста, попробуйте позже."
        )

# Обработчик добавления нового админа
@router.message(AdminManagement.waiting_for_admin_id)
async def process_new_admin_id(message: Message, state: FSMContext):
    """Обработка ID нового администратора"""
    if not await is_ceo(message.from_user.id):
        await message.answer("У вас нет прав CEO")
        await state.clear()
        return

    try:
        admin_id = int(message.text.strip())
        # Проверяем, не является ли уже админом
        if await is_admin(admin_id):
            await message.answer("Этот пользователь уже является администратором!")
            await state.clear()
            return
            
        success = await add_admin(
            admin_id=admin_id,
            username="Admin",  # Будет обновлено при первом использовании
            role="admin"
        )
        
        if success:
            await message.answer(
                f"✅ Администратор (ID: {admin_id}) успешно добавлен!\n"
                f"Попросите нового администратора написать /start боту для активации."
            )
        else:
            await message.answer("❌ Ошибка при добавлении администратора.")
    except ValueError:
        await message.answer("❌ Некорректный ID. Пожалуйста, отправьте числовой ID.")
    
    await state.clear()

# Обработчик callback для добавления админа
@router.callback_query(lambda c: c.data == "add_admin")
async def process_add_admin_button(callback: CallbackQuery, state: FSMContext):
    """Обработка нажатия кнопки добавления админа"""
    if not await is_ceo(callback.from_user.id):
        await callback.answer("У вас нет прав CEO")
        return

    await callback.message.answer(
        "Отправьте Telegram ID нового администратора.\n"
        "ID должен быть числом, например: 123456789"
    )
    await state.set_state(AdminManagement.waiting_for_admin_id)
    await callback.answer()

# Обработчик всех типов сообщений для создания тикета
@router.message(F.content_type.in_({'text', 'photo', 'video', 'document', 'voice'}), F.chat.type == "private")
async def handle_message(message: Message, state: FSMContext):
    """
    Обработка входящих сообщений для создания тикетов
    """
    # Проверяем, не находится ли пользователь в процессе какого-либо действия
    current_state = await state.get_state()
    if current_state is not None:
        # Если пользователь в каком-то состоянии, пропускаем обработку
        return

    # Проверяем, не является ли отправитель админом
    if await is_admin(message.from_user.id):
        # Для админов показываем сообщение о том, что они не могут создавать тикеты
        await message.answer(
            "Вы являетесь администратором и не можете создавать тикеты. "
            "Используйте команду /admin для доступа к панели управления."
        )
        return

    user = await get_user(message.from_user.id)
    
    if not user:
        await message.answer(
            "Пожалуйста, сначала зарегистрируйтесь с помощью команды /start"
        )
        return

    # Сериализуем сообщение
    message_data = message_manager.serialize_message(message)
    
    # Создаем тикет
    ticket_id = await create_ticket(
        user_id=message.from_user.id,
        message_data=message_data
    )
    
    if ticket_id:
        # Создаем клавиатуру для админов
        keyboard = get_ticket_actions_keyboard(ticket_id)
        
        # Получаем список всех админов
        admins = await get_all_admins()
        admin_ids = [admin[1] for admin in admins]  # admin_id находится во втором столбце
        
        # Формируем имя пользователя для уведомления
        user_name = message.from_user.username or message.from_user.first_name
        
        # Отправляем уведомления
        await notification_manager.notify_ticket_created(
            ticket_id=ticket_id,
            user_name=user_name,
            admin_ids=admin_ids,
            keyboard=keyboard
        )
        
        await message.answer(
            f"Ваш тикет #{ticket_id} создан. Мы ответим вам в ближайшее время."
        )
    else:
        await message.answer(
            "Произошла ошибка при создании тикета. Пожалуйста, попробуйте позже."
        )

# Обработчик просмотра тикета
@router.callback_query(lambda c: c.data.startswith('view_ticket:'))
async def process_ticket_view(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    ticket_id = int(callback.data.split(':')[1])
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден")
        return
    
    # Получаем информацию о пользователе
    user = await get_user(ticket[1])  # ticket[1] это user_id
    message_data = json.loads(ticket[9]) if ticket[9] else {}  # ticket[9] это message_data
    
    # Формируем текст сообщения
    text = (
        f"📋 Тикет #{ticket_id}\n"
        f"От: {user[3]}\n"  # user[3] это full_name
        f"Статус: {ticket[2]}\n"  # ticket[2] это status
        f"Создан: {ticket[4]}\n\n"  # ticket[4] это created_at
    )

    # Добавляем содержимое сообщения
    if message_data.get('text'):
        text += f"Сообщение: {message_data['text']}\n"
    
    # Создаем клавиатуру с кнопкой "Взять в работу"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Взять в работу",
                    callback_data=f"take_ticket:{ticket_id}"
                )
            ]
        ]
    )

    # Отправляем медиафайл, если есть
    if message_data.get('media_type') and message_data.get('media_id'):
        media_type = message_data['media_type']
        media_id = message_data['media_id']
        caption = text[:1024]  # Ограничение на длину подписи

        if media_type == 'photo':
            await callback.message.answer_photo(media_id, caption=caption, reply_markup=keyboard)
        elif media_type == 'video':
            await callback.message.answer_video(media_id, caption=caption, reply_markup=keyboard)
        elif media_type == 'document':
            await callback.message.answer_document(media_id, caption=caption, reply_markup=keyboard)
        elif media_type == 'voice':
            await callback.message.answer_voice(media_id, caption=caption, reply_markup=keyboard)
    else:
        # Если нет медиафайла, отправляем просто текст
        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()

# Обработчик взятия тикета в работу
@router.callback_query(lambda c: c.data.startswith('take_ticket:'))
async def process_ticket_taken(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    ticket_id = int(callback.data.split(':')[1])
    
    # Проверяем, не взят ли уже тикет
    ticket = await get_ticket(ticket_id)
    if ticket[2] == 'in_progress':  # ticket[2] это status
        await callback.answer("Этот тикет уже взят в работу другим администратором")
        return
    
    # Обновляем статус тикета
    await update_ticket_status(
        ticket_id=ticket_id,
        status='in_progress',
        admin_id=callback.from_user.id
    )
    
    # Получаем информацию о пользователе
    user = await get_user(ticket[1])  # ticket[1] это user_id
    
    # Отправляем уведомления
    await notification_manager.notify_ticket_taken(
        ticket_id=ticket_id,
        admin_username=callback.from_user.username
    )
    
    # Отправляем сообщение пользователю
    try:
        await callback.bot.send_message(
            chat_id=ticket[1],  # user_id
            text=f"Ваш тикет #{ticket_id} взят в обработку специалистом поддержки"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление пользователю: {e}")
    
    # Обновляем сообщение с тикетом
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Ответить",
                    callback_data=f"reply:{ticket_id}"
                ),
                InlineKeyboardButton(
                    text="Закрыть тикет",
                    callback_data=f"close:{ticket_id}"
                )
            ]
        ]
    )
    
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer("Тикет взят в работу")

# Обработчик ответа на тикет
@router.callback_query(lambda c: c.data.startswith('reply:'))
async def process_reply_start(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    ticket_id = int(callback.data.split(':')[1])
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден")
        return
    
    if ticket[2] != 'in_progress' or ticket[3] != callback.from_user.id:  # status и assigned_admin_id
        await callback.answer("Этот тикет не находится в вашей работе")
        return
    
    await state.set_state(TicketResponse.waiting_for_response)
    await state.update_data(ticket_id=ticket_id)
    
    await callback.message.answer(
        "Отправьте ваш ответ на тикет. Поддерживаются текст, фото, видео и документы."
    )
    await callback.answer()

# Обработчик ответа администратора
@router.message(TicketResponse.waiting_for_response)
async def process_admin_response(message: Message, state: FSMContext):
    data = await state.get_data()
    ticket_id = data.get('ticket_id')
    
    if not ticket_id:
        await message.answer("Произошла ошибка. Попробуйте начать ответ заново.")
        await state.clear()
        return
    
    ticket = await get_ticket(ticket_id)
    if not ticket:
        await message.answer("Тикет не найден")
        await state.clear()
        return
    
    try:
        # Отправляем ответ пользователю
        if message.text:
            await message.bot.send_message(
                chat_id=ticket[1],  # user_id
                text=f"Ответ на ваш тикет #{ticket_id}:\n{message.text}\n\nС уважением,\nСлужба поддержки"
            )
        elif message.photo:
            await message.bot.send_photo(
                chat_id=ticket[1],
                photo=message.photo[-1].file_id,
                caption=f"Ответ на ваш тикет #{ticket_id}\n\nС уважением,\nСлужба поддержки"
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=ticket[1],
                video=message.video.file_id,
                caption=f"Ответ на ваш тикет #{ticket_id}\n\nС уважением,\nСлужба поддержки"
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=ticket[1],
                document=message.document.file_id,
                caption=f"Ответ на ваш тикет #{ticket_id}\n\nС уважением,\nСлужба поддержки"
            )
        
        # Отправляем уведомление в группу
        await notification_manager.notify_ticket_answered(
            ticket_id=ticket_id,
            admin_username=message.from_user.username
        )
        
        await message.answer("Ваш ответ отправлен пользователю")
    except Exception as e:
        await message.answer(f"Ошибка при отправке ответа: {e}")
    
    await state.clear()

# Обработчик закрытия тикета
@router.callback_query(lambda c: c.data.startswith('close:'))
async def process_ticket_close(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("У вас нет прав администратора")
        return

    ticket_id = int(callback.data.split(':')[1])
    ticket = await get_ticket(ticket_id)
    
    if not ticket:
        await callback.answer("Тикет не найден")
        return
    
    if ticket[2] != 'in_progress' or ticket[3] != callback.from_user.id:
        await callback.answer("Этот тикет не находится в вашей работе")
        return
    
    # Закрываем тикет
    await update_ticket_status(
        ticket_id=ticket_id,
        status='closed',
        admin_id=callback.from_user.id
    )
    
    # Отправляем уведомление пользователю
    try:
        await callback.bot.send_message(
            chat_id=ticket[1],  # user_id
            text=f"Ваш тикет #{ticket_id} был закрыт. Спасибо за обращение!"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление пользователю: {e}")
    
    # Отправляем уведомление в группу
    await notification_manager.notify_ticket_closed(
        ticket_id=ticket_id,
        closed_by=f"@{callback.from_user.username}"
    )
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"Тикет #{ticket_id} закрыт.",
        reply_markup=None
    )
    
    await callback.answer("Тикет успешно закрыт")

# Обработчик меню экспорта
@router.callback_query(lambda c: c.data == "export_menu")
async def process_export_menu(callback: CallbackQuery):
    if not await is_ceo(callback.from_user.id):
        await callback.answer("У вас нет прав CEO")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="За день",
                    callback_data="export:day"
                ),
                InlineKeyboardButton(
                    text="За неделю",
                    callback_data="export:week"
                ),
                InlineKeyboardButton(
                    text="За месяц",
                    callback_data="export:month"
                )
            ],
            [
                InlineKeyboardButton(
                    text="« Назад",
                    callback_data="admin_panel"
                )
            ]
        ]
    )
    
    await callback.message.edit_text(
        "Выберите период для экспорта данных:",
        reply_markup=keyboard
    )
    await callback.answer()

# Обработчик команды /admin и кнопки "Панель управления"
@router.message(Command("admin"))
@router.callback_query(lambda c: c.data == "admin_panel")
async def cmd_admin(event: Union[Message, CallbackQuery]):
    # Проверяем тип события и получаем нужные данные
    if isinstance(event, Message):
        user_id = event.from_user.id
        reply_method = event.answer
    else:  # CallbackQuery
        user_id = event.from_user.id
        reply_method = event.message.answer
        await event.answer()  # Убираем часики с кнопки

    if not await is_admin(user_id):
        await reply_method("У вас нет доступа к админ-панели.")
        return

    is_ceo_user = await is_ceo(user_id)
    keyboard = get_admin_keyboard(is_ceo=is_ceo_user)
    
    await reply_method(
        "Панель управления:",
        reply_markup=keyboard
    )

def register_all_handlers(dp: Router):
    """Регистрация всех обработчиков"""
    dp.include_router(router)