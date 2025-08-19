# game_server\api_fast\rest_routers\routers_config.py
from .auth.auth_config import auth_routers
# ===================================================================
# 1. ИМПОРТИРУЕМ ГОТОВЫЕ СПИСКИ ИЗ КАЖДОГО ДОМЕНА
# ===================================================================

# from .rest_routers.discord.discord_config import discord_routers
# from .rest_routers.character.character_config import character_routers

# --- ИСПРАВЛЕНИЕ: Добавляем недостающие импорты ---
# from .rest_routers.utils_route.utils_config import utils_routers  # <-- ДОБАВЛЕНО
from .health_config import health_routers            # <-- ДОБАВЛЕНО




# ===================================================================
# 2. СОБИРАЕМ ВСЕ КОНФИГУРАЦИИ В ОДИН ОБЩИЙ СПИСОК
# ===================================================================

ROUTERS_CONFIG = (
    auth_routers +
    health_routers

)