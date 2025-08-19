# apps/gateway/gateway/event_broadcast_handler.py
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Optional, Dict, Any

from libs.messaging.rabbitmq_names import Queues
from libs.messaging.i_message_bus import IMessageBus
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from libs.utils.logging_setup import app_logger as logger


class EventBroadcastHandler:
    """
    Слушает очередь событий и рассылает их всем активным WebSocket-клиентам.
    JSON-only. Без msgpack. Без прямой работы с AMQP-сообщениями.
    """

    def __init__(self, message_bus: IMessageBus, client_connection_manager: ClientConnectionManager) -> None:
        self.message_bus = message_bus
        self.client_connection_manager = client_connection_manager
        self._listen_task: Optional[asyncio.Task] = None
        self.inbound_queue_name = Queues.GATEWAY_INBOUND_EVENTS
        logger.info("✅ EventBroadcastHandler (broadcast-to-all) инициализирован.")

    async def start_listening_for_events(self) -> None:
        """Запускает прослушивание очереди входящих событий."""
        if self._listen_task is None or self._listen_task.done():
            logger.info(f"🎧 Слушаю события из очереди '{self.inbound_queue_name}' для массовой рассылки.")
            self._listen_task = asyncio.create_task(self._listen_loop())
        else:
            logger.warning("EventBroadcastHandler уже запущен.")

    async def _listen_loop(self) -> None:
        """Регистрирует коллбэк в шине сообщений."""
        try:
            await self.message_bus.consume(self.inbound_queue_name, self._on_message_received)
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске EventBroadcastHandler: {e}", exc_info=True)
            raise

    async def _on_message_received(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """
        Коллбэк шины. data — уже распарсенный JSON, meta — метаданные (routing_key, correlation_id, ...).
        """
        try:
            routing_key = meta.get("routing_key") or "event.unknown"
            logger.info(f"EventBroadcastHandler: получено событие '{routing_key}'")
            logger.debug(f"payload: {data}")

            # список клиентов
            all_client_ids = list(self.client_connection_manager.active_connections.keys())
            if not all_client_ids:
                return

            # Формируем единый конверт под WebSocket (без зависимостей от моделей)
            envelope = {
                "type": "EVENT",
                "correlation_id": meta.get("correlation_id") or str(uuid.uuid4()),
                "payload": {
                    "type": routing_key,
                    "payload": data,
                },
            }
            message_json = json.dumps(envelope, ensure_ascii=False, separators=(",", ":"))

            logger.info(f"Рассылка события '{routing_key}' {len(all_client_ids)} клиентам.")
            for client_id in all_client_ids:
                await self.client_connection_manager.send_message_to_client(client_id, message_json)

        except Exception as e:
            logger.error(f"Ошибка при массовой рассылке события: {e}", exc_info=True)

    @property
    def listen_task(self):
        return self._listen_task
