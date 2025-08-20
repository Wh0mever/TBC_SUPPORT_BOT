from database import add_admin, is_admin, is_ceo

# CEO IDs
CEO_IDS = [1382917630, 1914567632]

async def init_ceo_admins():
    """Инициализация CEO администраторов"""
    for ceo_id in CEO_IDS:
        # Проверяем, не существует ли уже админ
        if not await is_admin(ceo_id):
            await add_admin(
                admin_id=ceo_id,
                username="CEO",
                role="CEO"
            )

async def check_admin_role(user_id: int) -> str:
    """Проверка роли пользователя"""
    if await is_ceo(user_id):
        return "CEO"
    elif await is_admin(user_id):
        return "admin"
    return "user"
