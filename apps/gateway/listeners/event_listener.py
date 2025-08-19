# apps/gateway/listeners/event_listener.py
from __future__ import annotations
import json
from typing import Any, Dict

from libs.messaging.base_listener import BaseMicroserviceListener
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from libs.utils.logging_setup import app_logger as logger


class EventBroadcastListener(BaseMicroserviceListener):
    """Слушает события и рассылает их всем активным WS-клиентам."""

    def __init__(self, client_manager: ClientConnectionManager, **kwargs):
        super().__init__(**kwargs)
        self.client_manager = client_manager

    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        routing_key = meta.get("routing_key", "unknown.event")

        # Формируем стандартный конверт для WS
        ws_payload = {
            "type": "event",
            "topic": routing_key,
            "payload": data,
        }
        message_json = json.dumps(ws_payload)

        # Рассылаем всем
        active_clients = list(self.client_manager.active_connections.keys())
        if not active_clients:
            return

        logger.info(f"Broadcasting event '{routing_key}' to {len(active_clients)} clients.")
        for client_id in active_clients:
            await self.client_manager.send_message_to_client(client_id, message_json)