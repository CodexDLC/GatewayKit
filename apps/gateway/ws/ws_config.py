# apps/gateway/ws/ws_config.py

from .unified_ws import router as unified_ws_router

ws_routers = [{"router": unified_ws_router, "tags": ["WebSocket"]}]
