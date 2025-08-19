# apps/gateway/rest/routers_config.py

from .auth.auth_config import auth_routers
from .health_config import health_routers
# --- ДОБАВЬ ЭТОТ ИМПОРТ ---
from apps.gateway.ws.ws_config import ws_routers

# ===================================================================
# 2. СОБИРАЕМ ВСЕ КОНФИГУРАЦИИ В ОДИН ОБЩИЙ СПИСОК
# ===================================================================

ROUTERS_CONFIG = (
    auth_routers +
    health_routers +
    # --- И ДОБАВЬ ЭТУ СТРОКУ ---
    ws_routers
)