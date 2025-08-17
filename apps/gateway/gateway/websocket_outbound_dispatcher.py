from __future__ import annotations

import asyncio
import json
from typing import Optional, Dict, Any

# логгер
try:
    from utils.logging_setup import app_logger as logger
except Exception:  # fallback
    import logging
    logger = logging.getLogger(__name__)

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager


class OutboundWebSocketDispatcher:
    """
    Потребляет сообщения из единой очереди и отправляет их
    в соответствующее активное WebSocket-соединение.

    JSON-only, без msgpack и без прямого aio_pika.IncomingMessage.
    Ack/Nack делает IMessageBus.
    """

    def __init__(self, message_bus: IMessageBus, client_connection_manager: ClientConnectionManager) -> None:
        self.message_bus = message_bus
        self.client_connection_manager = client_connection_manager
        self._listen_task: Optional[asyncio.Task] = None
        self.outbound_queue_name = Queues.GATEWAY_OUTBOUND_WS_MESSAGES
        logger.info("✅ OutboundWebSocketDispatcher инициализирован.")

    async def start_listening_for_outbound_messages(self) -> None:
        if self._listen_task is None or self._listen_task.done():
            logger.info(f"🎧 Слушаю исходящие WS-сообщения из очереди '{self.outbound_queue_name}'.")
            self._listen_task = asyncio.create_task(self._listen_loop())
        else:
            logger.warning("OutboundWebSocketDispatcher уже запущен.")

    async def _listen_loop(self) -> None:
        try:
            await self.message_bus.consume(self.outbound_queue_name, self._on_message_received)
        except Exception as e:
            logger.critical(f"Критическая ошибка при запуске OutboundWebSocketDispatcher: {e}", exc_info=True)
            raise

    async def _on_message_received(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """
        Колбэк шины. data — уже распарсенный JSON (dict), meta — метаданные (routing_key, correlation_id, ...).

        Ожидается одно из двух:
          1) Плоское сообщение для клиента: { "client_id": "...", ... }
          2) Обёртка: { "payload": { "client_id": "...", ... }, ... }
        """
        try:
            # извлекаем фактическое WS-сообщение
            payload = data.get("payload") if isinstance(data, dict) else None
            ws_msg = payload if isinstance(payload, dict) and "client_id" in payload else data

            if not isinstance(ws_msg, dict):
                logger.warning("OutboundDispatcher: сообщение не dict — пропущено")
                return

            target_client_id = ws_msg.get("client_id")
            if not target_client_id:
                corr = meta.get("correlation_id")
                logger.warning(f"OutboundDispatcher: нет client_id (corr={corr}) — пропуск")
                return

            message_json = json.dumps(ws_msg, ensure_ascii=False, separators=(",", ":"))
            ok = await self.client_connection_manager.send_message_to_client(target_client_id, message_json)

            corr = meta.get("correlation_id")
            if ok:
                logger.debug(f"Ответ для клиента {target_client_id} (corr={corr}) отправлен")
            else:
                logger.warning(f"Не удалось отправить сообщение клиенту {target_client_id} (corr={corr}) — нет соединения")

        except Exception as e:
            corr = meta.get("correlation_id")
            logger.error(f"Ошибка при обработке исходящего WS-сообщения (corr={corr}): {e}", exc_info=True)
