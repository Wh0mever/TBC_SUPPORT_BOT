from datetime import datetime, timedelta
import aiosqlite
from notifications import NotificationManager
from database import DB_PATH

class MissedResponsesChecker:
    """Класс для проверки пропущенных ответов"""
    
    def __init__(self, notification_manager: NotificationManager):
        self.notification_manager = notification_manager
        self.response_timeout = timedelta(minutes=30)

    async def check_missed_responses(self):
        """Проверка пропущенных ответов"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем тикеты в работе без ответа более 30 минут
            query = '''
                SELECT 
                    t.*,
                    u.full_name as user_name,
                    a.username as admin_username,
                    a.admin_id
                FROM tickets t
                JOIN users u ON t.user_id = u.user_id
                JOIN admins a ON t.assigned_admin_id = a.admin_id
                WHERE 
                    t.status = 'in_progress'
                    AND t.first_response_time IS NULL
                    AND t.missed_flag = 0
                    AND datetime(t.created_at, '+30 minutes') <= datetime('now')
            '''
            
            async with db.execute(query) as cursor:
                missed_tickets = await cursor.fetchall()

            # Получаем список всех админов для уведомления
            async with db.execute('SELECT admin_id FROM admins') as cursor:
                admin_ids = [row['admin_id'] for row in await cursor.fetchall()]

            # Обрабатываем каждый пропущенный тикет
            for ticket in missed_tickets:
                # Обновляем флаг пропуска
                await db.execute(
                    'UPDATE tickets SET missed_flag = 1 WHERE id = ?',
                    (ticket['id'],)
                )
                
                # Отправляем уведомления
                await self.notification_manager.notify_missed_response(
                    ticket_id=ticket['id'],
                    admin_ids=admin_ids,
                    admin_username=ticket['admin_username']
                )

            await db.commit()

    async def get_missed_responses_stats(self, admin_id: int = None):
        """Получение статистики по пропущенным ответам"""
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            
            if admin_id:
                query = '''
                    SELECT 
                        COUNT(*) as total_missed,
                        CAST(COUNT(*) * 100.0 / (
                            SELECT COUNT(*) 
                            FROM tickets 
                            WHERE assigned_admin_id = ?
                        ) AS REAL) as missed_percent
                    FROM tickets
                    WHERE 
                        assigned_admin_id = ?
                        AND missed_flag = 1
                '''
                params = (admin_id, admin_id)
            else:
                query = '''
                    SELECT 
                        a.username,
                        COUNT(t.id) as total_missed,
                        CAST(COUNT(t.id) * 100.0 / (
                            SELECT COUNT(*) 
                            FROM tickets 
                            WHERE assigned_admin_id = a.admin_id
                        ) AS REAL) as missed_percent
                    FROM admins a
                    LEFT JOIN tickets t ON 
                        t.assigned_admin_id = a.admin_id 
                        AND t.missed_flag = 1
                    GROUP BY a.admin_id, a.username
                '''
                params = ()

            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()