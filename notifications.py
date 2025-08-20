from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
import os
from typing import List, Union
from datetime import datetime

class NotificationManager:
    """Класс для управления уведомлениями"""
    
    def __init__(self, bot: Bot):
        self.bot = bot
        self.private_group_id = os.getenv('PRIVATE_GROUP_ID')
        # Логируем значение private_group_id для отладки
        print(f"Private group ID: {self.private_group_id}")

    async def notify_admins(
        self,
        admin_ids: List[int],
        text: str,
        keyboard: Union[InlineKeyboardMarkup, None] = None
    ):
        """Отправка уведомления администраторам"""
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    reply_markup=keyboard
                )
            except Exception as e:
                if "bot can't initiate conversation with a user" in str(e):
                    print(f"Admin {admin_id} needs to start the bot first")
                else:
                    print(f"Error sending notification to admin {admin_id}: {e}")

    async def notify_private_group(
        self,
        text: str,
        keyboard: Union[InlineKeyboardMarkup, None] = None
    ):
        """Отправка уведомления в приватную группу"""
        if not self.private_group_id:
            print("WARNING: PRIVATE_GROUP_ID не установлен в .env файле")
            return
            
        try:
            group_id = self.private_group_id
            # Если ID не начинается с -100, добавляем префикс для супергруппы
            if not str(group_id).startswith('-100'):
                group_id = int(f"-100{str(group_id).replace('-', '')}")
            
            await self.bot.send_message(
                chat_id=group_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            if "group chat was upgraded to a supergroup chat" in str(e):
                print("Group was upgraded to supergroup. Please update the group ID in .env file")
            else:
                print(f"Error sending notification to private group: {e}")
            print(f"Attempted to send to group ID: {self.private_group_id}")

    async def notify_ticket_created(
        self,
        ticket_id: int,
        user_name: str,
        admin_ids: List[int],
        keyboard: InlineKeyboardMarkup
    ):
        """Уведомление о создании тикета"""
        text = f"Новый тикет #{ticket_id} от {user_name}"
        
        # Уведомляем админов
        await self.notify_admins(admin_ids, text, keyboard)
        
        # Уведомляем приватную группу
        await self.notify_private_group(text, keyboard)

    async def notify_ticket_taken(
        self,
        ticket_id: int,
        admin_username: str
    ):
        """Уведомление о взятии тикета в работу"""
        text = f"Тикет #{ticket_id} взял в работу @{admin_username}"
        await self.notify_private_group(text)

    async def notify_ticket_answered(
        self,
        ticket_id: int,
        admin_username: str
    ):
        """Уведомление об ответе на тикет"""
        text = f"Админ @{admin_username} ответил на тикет #{ticket_id}"
        await self.notify_private_group(text)

    async def notify_ticket_closed(
        self,
        ticket_id: int,
        closed_by: str
    ):
        """Уведомление о закрытии тикета"""
        text = f"Тикет #{ticket_id} закрыт пользователем {closed_by}"
        await self.notify_private_group(text)

    async def notify_missed_response(
        self,
        ticket_id: int,
        admin_ids: List[int],
        admin_username: str
    ):
        """Уведомление о пропущенном ответе"""
        text = f"⚠️ Тикет #{ticket_id} без ответа 30 минут! Ответственный: @{admin_username}"
        
        # Уведомляем админов
        await self.notify_admins(admin_ids, text)
        
        # Уведомляем приватную группу
        await self.notify_private_group(text)
