from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)

def get_contact_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для запроса контакта"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить контакт", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_ticket_actions_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с тикетом для администраторов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Взять в работу",
                    callback_data=f"take_ticket:{ticket_id}"
                ),
                InlineKeyboardButton(
                    text="Просмотреть",
                    callback_data=f"view_ticket:{ticket_id}"
                )
            ]
        ]
    )

def get_admin_keyboard(is_ceo: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    buttons = [
        [
            InlineKeyboardButton(
                text="Мои тикеты",
                callback_data="my_tickets"
            ),
            InlineKeyboardButton(
                text="Открытые тикеты",
                callback_data="open_tickets"
            )
        ],
        [
            InlineKeyboardButton(
                text="Закрытые тикеты",
                callback_data="closed_tickets"
            ),
            InlineKeyboardButton(
                text="Аналитика",
                callback_data="analytics"
            )
        ]
    ]
    
    # Дополнительные кнопки для CEO
    if is_ceo:
        buttons.extend([
            [
                InlineKeyboardButton(
                    text="Управление админами",
                    callback_data="manage_admins"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Экспорт данных",
                    callback_data="export_menu"
                )
            ]
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_ticket_priority_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора приоритета тикета"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обычный",
                    callback_data=f"priority:{ticket_id}:normal"
                ),
                InlineKeyboardButton(
                    text="Срочный",
                    callback_data=f"priority:{ticket_id}:urgent"
                ),
                InlineKeyboardButton(
                    text="VIP",
                    callback_data=f"priority:{ticket_id}:vip"
                )
            ]
        ]
    )

def get_ticket_close_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    """Клавиатура закрытия тикета"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Закрыть тикет",
                    callback_data=f"close_ticket:{ticket_id}"
                )
            ]
        ]
    )
