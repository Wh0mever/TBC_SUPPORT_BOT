# Telegram Бот Технической Поддержки Банка

Бот для обработки обращений клиентов с системой тикетов, админ-панелью и аналитикой.

## Общая схема работы

```mermaid
flowchart LR
    style U fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style B fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style GM fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style DB fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style A fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style C fill:#E9ECEF,stroke:#343A40,stroke-width:2px
    style AN fill:#E9ECEF,stroke:#343A40,stroke-width:2px

    U["👤 Пользователь"] --> |"✉️ Сообщение"| B["🤖 Бот"]
    B --> |"📝 Создает"| DB["💾 База данных"]
    B --> |"🔔 Уведомляет"| GM["👥 Группа<br/>мониторинга"]
    B --> |"🔔 Уведомляет"| A["👨‍💼 Админы"]
    C["👑 CEO"] --> |"👥 Управляет"| A
    C --> |"📊 Смотрит<br/>статистику"| AN["📈 Аналитика"]
    AN --> |"📑 Excel"| C
    A --> |"✅ Берут"| DB
    A --> |"💬 Отвечают"| U
```

## Процесс обработки обращения

```mermaid
sequenceDiagram
    participant U as 👤 Пользователь
    participant B as 🤖 Бот
    participant A as 👨‍💼 Админ
    participant DB as 💾 База данных
    participant G as 👥 Группа

    U->>+B: ✉️ Сообщение
    B->>DB: 📝 Создание тикета
    B->>G: 🔔 Уведомление
    B->>A: 🔔 Уведомление админов
    A->>B: ✅ Взятие тикета
    A->>U: 💬 Ответ
    Note over B,DB: ⏰ Если нет ответа 30 минут
    B->>A: ⚠️ Напоминание
    A->>B: 🔒 Закрытие тикета
```

## Структура данных

```mermaid
classDiagram
    direction LR
    class User {
        +id: int
        +full_name: str
        +username: str
        +contact: str
    }
    class Ticket {
        +id: int
        +user_id: int
        +status: str
        +message_data: str
        +created_at: datetime
        +taken_at: datetime
        +closed_at: datetime
        +admin_id: int
    }
    class Admin {
        +id: int
        +username: str
        +is_ceo: bool
        +stats: dict
    }
    
    User "1" --o "*" Ticket : создает
    Admin "1" --o "*" Ticket : обрабатывает
```

## Установка и настройка

1. Клонируйте репозиторий
2. Установите зависимости:
```bash
pip install -r requirements.txt
```
3. Создайте файл `.env` с настройками:
```env
BOT_TOKEN=ваш_токен_бота
PRIVATE_GROUP_ID=айди_группы_мониторинга
```

## Основные команды

### Пользователи
- `/start` - Начало работы с ботом
- Отправка любого сообщения создает новый тикет

### Админы
- `/admin` - Открыть админ-панель
- Кнопки в админ-панели:
  - 📋 Открытые тикеты
  - 📊 Аналитика
  - 👥 Управление админами (только для CEO)

### Команды в группе мониторинга
- `/stats` - Общая статистика
- `/my_stats` - Личная статистика админа
- `/admin_stats` - Статистика по всем админам
- `/export_day` - Экспорт за день
- `/export_week` - Экспорт за неделю
- `/export_month` - Экспорт за месяц

## Особенности

- **Роли**: Пользователь, Админ, CEO
- **Тикеты**: Создание, взятие в работу, ответ, закрытие
- **Уведомления**: 
  - Новые тикеты
  - Напоминания о пропущенных ответах (30 минут)
  - Уведомления в группу мониторинга
- **Аналитика**:
  - Статистика по тикетам
  - Время ответа и решения
  - Экспорт в Excel (день/неделя/месяц)
- **Безопасность**:
  - Проверка ролей
  - Защита от создания тикетов в группах
  - Конфиденциальность админов

## Технологии

- Python 3.9+
- Aiogram 3.13.1
- SQLite (aiosqlite)
- Pandas + XlsxWriter для отчетов
- APScheduler для напоминаний