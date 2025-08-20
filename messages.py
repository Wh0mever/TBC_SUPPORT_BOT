from aiogram.types import Message
from typing import Optional, List
import json

class MessageManager:
    """Класс для управления сообщениями и медиафайлами"""
    
    @staticmethod
    def serialize_message(message: Message) -> str:
        """Сериализация сообщения для сохранения в БД"""
        data = {
            'message_id': message.message_id,
            'text': message.text,
            'media_type': None,
            'media_id': None,
            'caption': None
        }

        # Обработка фото
        if message.photo:
            data['media_type'] = 'photo'
            data['media_id'] = message.photo[-1].file_id
            data['caption'] = message.caption

        # Обработка видео
        elif message.video:
            data['media_type'] = 'video'
            data['media_id'] = message.video.file_id
            data['caption'] = message.caption

        # Обработка документа
        elif message.document:
            data['media_type'] = 'document'
            data['media_id'] = message.document.file_id
            data['caption'] = message.caption

        # Обработка голосового сообщения
        elif message.voice:
            data['media_type'] = 'voice'
            data['media_id'] = message.voice.file_id

        return json.dumps(data)

    @staticmethod
    def deserialize_message(data: str) -> dict:
        """Десериализация сообщения из БД"""
        return json.loads(data)

    @staticmethod
    def get_message_type(message: Message) -> str:
        """Определение типа сообщения"""
        if message.photo:
            return 'photo'
        elif message.video:
            return 'video'
        elif message.document:
            return 'document'
        elif message.voice:
            return 'voice'
        elif message.text:
            return 'text'
        return 'unknown'

    @staticmethod
    def get_file_id(message: Message) -> Optional[str]:
        """Получение file_id медиафайла"""
        if message.photo:
            return message.photo[-1].file_id
        elif message.video:
            return message.video.file_id
        elif message.document:
            return message.document.file_id
        elif message.voice:
            return message.voice.file_id
        return None
