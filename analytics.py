import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Используем не-интерактивный бэкенд
import matplotlib.pyplot as plt
from io import BytesIO
import aiosqlite
from datetime import datetime, timedelta
import os

class AnalyticsManager:
    """Класс для управления аналитикой"""
    
    def __init__(self, db_path: str = 'support_bot.db'):
        self.db_path = db_path

    async def get_tickets_stats(self, period: str = 'day') -> dict:
        """Получение статистики по тикетам за период"""
        if period == 'day':
            date_filter = datetime.now() - timedelta(days=1)
        elif period == 'week':
            date_filter = datetime.now() - timedelta(weeks=1)
        elif period == 'month':
            date_filter = datetime.now() - timedelta(days=30)
        else:
            date_filter = datetime.now() - timedelta(days=1)

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Общее количество тикетов
            total_tickets = await db.execute(
                'SELECT COUNT(*) as count FROM tickets WHERE created_at > ?',
                (date_filter,)
            )
            total = (await total_tickets.fetchone())['count']

            # Тикеты по статусам
            status_stats = await db.execute('''
                SELECT status, COUNT(*) as count 
                FROM tickets 
                WHERE created_at > ?
                GROUP BY status
            ''', (date_filter,))
            
            statuses = {row['status']: row['count'] 
                       for row in await status_stats.fetchall()}

            return {
                'total': total,
                'statuses': statuses,
                'period': period
            }

    async def get_admin_stats(self, admin_id: int = None) -> dict:
        """Получение статистики по администратору"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            if admin_id:
                # Статистика конкретного админа
                query = '''
                    SELECT 
                        a.username,
                        COUNT(*) as total_tickets,
                        SUM(CASE WHEN t.missed_flag = 1 THEN 1 ELSE 0 END) as missed,
                        AVG(
                            CASE 
                                WHEN t.first_response_time IS NOT NULL 
                                THEN strftime('%s', t.first_response_time) - strftime('%s', t.created_at)
                                ELSE NULL 
                            END
                        ) as avg_response_time
                    FROM tickets t
                    JOIN admins a ON t.assigned_admin_id = a.admin_id
                    WHERE t.assigned_admin_id = ?
                '''
                stats = await db.execute(query, (admin_id,))
            else:
                # Общая статистика по всем админам
                query = '''
                    SELECT 
                        a.username,
                        COUNT(*) as total_tickets,
                        SUM(CASE WHEN t.missed_flag = 1 THEN 1 ELSE 0 END) as missed,
                        AVG(
                            CASE 
                                WHEN t.first_response_time IS NOT NULL 
                                THEN strftime('%s', t.first_response_time) - strftime('%s', t.created_at)
                                ELSE NULL 
                            END
                        ) as avg_response_time
                    FROM tickets t
                    JOIN admins a ON t.assigned_admin_id = a.admin_id
                    GROUP BY t.assigned_admin_id, a.username
                '''
                stats = await db.execute(query)

            rows = await stats.fetchall()
            return [dict(row) for row in rows]

    async def generate_hourly_chart(self) -> BytesIO:
        """Генерация графика активности по часам"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = '''
                SELECT 
                    strftime('%H', created_at) as hour,
                    COUNT(*) as count
                FROM tickets
                GROUP BY hour
                ORDER BY hour
            '''
            data = await db.execute(query)
            rows = await data.fetchall()

            hours = [row['hour'] for row in rows]
            counts = [row['count'] for row in rows]

            # Создаем новый график
            plt.figure(figsize=(12, 6))
            
            # Настраиваем стиль
            plt.style.use('default')  # Используем стандартный стиль
            
            # Создаем график
            bars = plt.bar(hours, counts)
            
            # Добавляем значения над столбцами
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height,
                        f'{int(height)}',
                        ha='center', va='bottom')
            
            # Настраиваем оси и заголовок
            plt.title('Активность по часам', pad=20, size=14)
            plt.xlabel('Час', labelpad=10)
            plt.ylabel('Количество тикетов', labelpad=10)
            
            # Добавляем сетку
            plt.grid(True, linestyle='--', alpha=0.7)
            
            # Настраиваем ось X
            plt.xticks(range(24))  # Показываем все 24 часа
            
            # Добавляем отступы
            plt.tight_layout()
            
            # Сохраняем в буфер
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=300, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf

    async def export_to_csv(self, period: str = 'month') -> str:
        """Экспорт данных в CSV"""
        # Определяем период и его описание
        if period == 'day':
            date_filter = datetime.now() - timedelta(days=1)
            period_desc = "за последние 24 часа"
        elif period == 'week':
            date_filter = datetime.now() - timedelta(weeks=1)
            period_desc = "за последнюю неделю"
        elif period == 'month':
            date_filter = datetime.now() - timedelta(days=30)
            period_desc = "за последние 30 дней"
        else:
            date_filter = datetime.now() - timedelta(days=30)
            period_desc = "за последние 30 дней"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            # Получаем основные данные по тикетам
            query = '''
                SELECT 
                    t.id as "№ Тикета",
                    t.status as "Статус",
                    t.priority as "Приоритет",
                    datetime(t.created_at) as "Создан",
                    datetime(t.closed_at) as "Закрыт",
                    datetime(t.first_response_time) as "Первый ответ",
                    CASE 
                        WHEN t.missed_flag = 1 THEN 'Да'
                        ELSE 'Нет'
                    END as "Пропущен",
                    CASE 
                        WHEN t.first_response_time IS NOT NULL 
                        THEN round((julianday(t.first_response_time) - julianday(t.created_at)) * 24 * 60, 0)
                        ELSE NULL 
                    END as "Время ответа (минуты)",
                    CASE 
                        WHEN t.closed_at IS NOT NULL 
                        THEN round((julianday(t.closed_at) - julianday(t.created_at)) * 24 * 60, 0)
                        ELSE NULL 
                    END as "Время решения (минуты)",
                    u.full_name as "Пользователь",
                    a.username as "Администратор"
                FROM tickets t
                LEFT JOIN users u ON t.user_id = u.user_id
                LEFT JOIN admins a ON t.assigned_admin_id = a.admin_id
                WHERE t.created_at > ?
                ORDER BY t.created_at DESC
            '''
            
            cursor = await db.execute(query, (date_filter,))
            rows = await cursor.fetchall()
            
            # Получаем статистику
            stats_query = '''
                SELECT 
                    COUNT(*) as total_tickets,
                    SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open_tickets,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_tickets,
                    SUM(CASE WHEN missed_flag = 1 THEN 1 ELSE 0 END) as missed_tickets,
                    round(AVG(CASE 
                        WHEN first_response_time IS NOT NULL 
                        THEN (julianday(first_response_time) - julianday(created_at)) * 24 * 60
                        END), 1) as avg_response_time,
                    round(AVG(CASE 
                        WHEN closed_at IS NOT NULL 
                        THEN (julianday(closed_at) - julianday(created_at)) * 24 * 60
                        END), 1) as avg_resolution_time
                FROM tickets
                WHERE created_at > ?
            '''
            
            stats_cursor = await db.execute(stats_query, (date_filter,))
            stats = dict(await stats_cursor.fetchone())
            
            # Создаем DataFrame с данными
            df = pd.DataFrame([dict(row) for row in rows])
            
            # Создаем файл
            filename = f'tickets_export_{period}_{datetime.now().strftime("%Y%m%d")}.csv'
            
            # Создаем два DataFrame - для статистики и для данных
            stats_df = pd.DataFrame([{
                'Показатель': 'Всего тикетов',
                'Значение': stats['total_tickets']
            }, {
                'Показатель': 'Открытых тикетов',
                'Значение': stats['open_tickets']
            }, {
                'Показатель': 'Закрытых тикетов',
                'Значение': stats['closed_tickets']
            }, {
                'Показатель': 'Пропущенных тикетов',
                'Значение': stats['missed_tickets']
            }, {
                'Показатель': 'Среднее время ответа (минуты)',
                'Значение': stats['avg_response_time']
            }, {
                'Показатель': 'Среднее время решения (минуты)',
                'Значение': stats['avg_resolution_time']
            }])

            # Записываем в Excel
            filename = f'tickets_export_{period}_{datetime.now().strftime("%Y%m%d")}.xlsx'
            with pd.ExcelWriter(filename, engine='xlsxwriter') as writer:
                # Записываем заголовок
                workbook = writer.book
                header_format = workbook.add_format({
                    'bold': True,
                    'font_size': 12,
                    'align': 'center',
                    'valign': 'vcenter'
                })
                
                # Лист со статистикой
                stats_df.to_excel(writer, sheet_name='Статистика', index=False, startrow=2)
                worksheet = writer.sheets['Статистика']
                worksheet.write(0, 0, f'Отчет по тикетам {period_desc}', header_format)
                worksheet.write(1, 0, f'Сформирован: {datetime.now().strftime("%d.%m.%Y %H:%M:%S")}')
                worksheet.set_column('A:A', 30)  # Ширина первой колонки
                worksheet.set_column('B:B', 15)  # Ширина второй колонки
                
                # Лист с деталями
                if not df.empty:
                    df.to_excel(writer, sheet_name='Детальные данные', index=False)
                    detail_sheet = writer.sheets['Детальные данные']
                    # Устанавливаем ширину колонок
                    for idx, col in enumerate(df.columns):
                        max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                        detail_sheet.set_column(idx, idx, max_length)
            
            return filename

    async def get_sla_metrics(self) -> dict:
        """Получение метрик SLA"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            
            query = '''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN missed_flag = 0 THEN 1 ELSE 0 END) as on_time,
                    SUM(CASE WHEN missed_flag = 1 THEN 1 ELSE 0 END) as missed
                FROM tickets
                WHERE status = 'closed'
            '''
            
            stats = await db.execute(query)
            row = await stats.fetchone()
            
            total = row['total']
            if total > 0:
                on_time_percent = (row['on_time'] / total) * 100
                missed_percent = (row['missed'] / total) * 100
            else:
                on_time_percent = 0
                missed_percent = 0

            return {
                'total_closed': total,
                'on_time_percent': round(on_time_percent, 2),
                'missed_percent': round(missed_percent, 2)
            }
