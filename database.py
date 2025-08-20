import aiosqlite
import os
from datetime import datetime

DB_PATH = 'support_bot.db'

async def init_db():
    """Инициализация базы данных и создание таблиц"""
    async with aiosqlite.connect(DB_PATH) as db:
        # Создание таблицы пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы тикетов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT CHECK(status IN ('open', 'in_progress', 'closed')),
                assigned_admin_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                closed_at TIMESTAMP,
                priority TEXT DEFAULT 'normal',
                first_response_time TIMESTAMP,
                missed_flag BOOLEAN DEFAULT 0,
                message_data TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # Создание таблицы администраторов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER UNIQUE,
                username TEXT,
                role TEXT CHECK(role IN ('admin', 'CEO')),
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Создание таблицы логов
        await db.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                ticket_id INTEGER,
                admin_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id),
                FOREIGN KEY (admin_id) REFERENCES admins(admin_id)
            )
        ''')

        await db.commit()

# Функции для работы с пользователями
async def add_user(user_id: int, username: str, full_name: str, phone: str) -> bool:
    """Добавление нового пользователя"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                'INSERT INTO users (user_id, username, full_name, phone) VALUES (?, ?, ?, ?)',
                (user_id, username, full_name, phone)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error adding user: {e}")
        return False

async def get_user(user_id: int):
    """Получение информации о пользователе"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM users WHERE user_id = ?',
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()

# Функции для работы с тикетами
async def create_ticket(user_id: int, priority: str = 'normal', message_data: str = None) -> int:
    """Создание нового тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            'INSERT INTO tickets (user_id, status, priority, message_data) VALUES (?, "open", ?, ?)',
            (user_id, priority, message_data)
        )
        await db.commit()
        return cursor.lastrowid

async def get_ticket(ticket_id: int):
    """Получение информации о тикете"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM tickets WHERE id = ?',
            (ticket_id,)
        ) as cursor:
            return await cursor.fetchone()

async def update_ticket_status(ticket_id: int, status: str, admin_id: int = None):
    """Обновление статуса тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        if status == 'closed':
            await db.execute(
                'UPDATE tickets SET status = ?, closed_at = ? WHERE id = ?',
                (status, datetime.now(), ticket_id)
            )
        else:
            await db.execute(
                'UPDATE tickets SET status = ?, assigned_admin_id = ? WHERE id = ?',
                (status, admin_id, ticket_id)
            )
        await db.commit()

# Функции для работы с администраторами
async def add_admin(admin_id: int, username: str, role: str = 'admin') -> bool:
    """Добавление нового администратора"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                'INSERT INTO admins (admin_id, username, role) VALUES (?, ?, ?)',
                (admin_id, username, role)
            )
            await db.commit()
            return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False

async def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM admins WHERE admin_id = ?',
            (user_id,)
        ) as cursor:
            return bool(await cursor.fetchone())

async def is_ceo(user_id: int) -> bool:
    """Проверка, является ли пользователь CEO"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            'SELECT * FROM admins WHERE admin_id = ? AND role = "CEO"',
            (user_id,)
        ) as cursor:
            return bool(await cursor.fetchone())

async def get_all_admins():
    """Получение списка всех администраторов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('SELECT * FROM admins') as cursor:
            return await cursor.fetchall()

async def get_admin_tickets(admin_id: int):
    """Получение тикетов администратора"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = '''
            SELECT 
                t.*,
                u.full_name as user_name
            FROM tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.assigned_admin_id = ? AND t.status != 'closed'
            ORDER BY t.created_at DESC
        '''
        async with db.execute(query, (admin_id,)) as cursor:
            return await cursor.fetchall()

async def get_open_tickets():
    """Получение открытых тикетов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = '''
            SELECT 
                t.*,
                u.full_name as user_name
            FROM tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'open'
            ORDER BY t.created_at DESC
        '''
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def get_closed_tickets():
    """Получение закрытых тикетов"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = '''
            SELECT 
                t.*,
                u.full_name as user_name
            FROM tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'closed'
            ORDER BY t.closed_at DESC
            LIMIT 50
        '''
        async with db.execute(query) as cursor:
            return await cursor.fetchall()

async def update_ticket_priority(ticket_id: int, priority: str):
    """Обновление приоритета тикета"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            'UPDATE tickets SET priority = ? WHERE id = ?',
            (priority, ticket_id)
        )
        await db.commit()
