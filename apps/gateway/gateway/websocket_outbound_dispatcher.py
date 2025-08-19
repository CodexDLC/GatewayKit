from __future__ import annotations

import json
from typing import Optional, Dict, Any
from libs.utils.logging_setup import app_logger as logger

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues
from apps.gateway.gateway.client_connection_manager import ClientConnectionManager

# Новые DTO
from libs.domain.dto.backend import BackendOutboundEnvelope
from libs.domain.dto.ws import WSEventFrame, WSErrorFrame
from libs.domain.dto.errors import ErrorDTO


class OutboundWebSocketDispatcher:
    """
    Консьюмер исходящих сообщений из бекэндов и доставка их в WebSocket.
    Ждём новый envelope: BackendOutboundEnvelope.
    """
    def __init__(
        self,
        message_bus: IMessageBus,
        client_connection_manager: ClientConnectionManager
    ):
        self.message_bus = message_bus
        self.client_connection_manager = client_connection_manager
        self._listen_task: Optional[asyncio.Task] = None
        self.outbound_queue_name = Queues.GATEWAY_OUTBOUND_WS_MESSAGES
        logger.info("✅ OutboundWebSocketDispatcher инициализирован.")

    async def start_listening_for_outbound_messages(self):
        """
        Подписываемся на общую очередь исходящих сообщений к клиентам.
        """
        logger.info(f"📥 Подписка на очередь: {self.outbound_queue_name}")
        await self.message_bus.consume(
            queue_name=self.outbound_queue_name,
            handler=self._handle_outbound_message,
            prefetch=64,
        )

    async def _handle_outbound_message(self, body: Dict[str, Any], meta: Dict[str, Any]) -> None:
        """
        body: dict (JSON), meta: {message_id, correlation_id, routing_key, ...}
        Формат body соответствует BackendOutboundEnvelope.
        """
        try:
            env = BackendOutboundEnvelope.model_validate(body)
        except Exception as e:
            logger.warning(f"❌ Невалидный outbound envelope: {e} | body={body!r}")
            # бросаем исключение -> сообщение уйдёт в DLQ/отклонится (зависит от реализации bus)
            raise

        # --- Кому доставлять ---
        targets: list[str] = []
        if env.recipient:
            # приоритетное соединение
            if env.recipient.connection_id:
                targets.append(env.recipient.connection_id)
            elif env.recipient.account_id:
                targets.append(env.recipient.account_id)

        # TODO: групповые рассылки подключим позже (delivery.mode == "group")

        if not targets:
            logger.info(f"⚠️ Нет адресата в envelope (recipient/delivery пустые). Пропускаю. request_id={env.request_id}")
            return

        # --- Сформировать кадр ответа ---
        if env.status == "error":
            err = env.error or ErrorDTO(code="common.UNKNOWN", message="Unhandled backend error")
            frame = WSErrorFrame(error=err, request_id=env.request_id)
            payload_json = frame.model_dump_json()
        else:
            server_status = "final" if env.final else ("update" if env.status == "update" else "ok")
            frame = WSEventFrame(
                event=env.event,
                status=server_status,
                payload=env.payload or {},
                request_id=env.request_id,
                tick=env.tick,
                state_version=env.state_version,
            )
            payload_json = frame.model_dump_json()

        # --- Доставить всем таргетам ---
        delivered = 0
        for target_id in targets:
            ok = await self.client_connection_manager.send_message_to_client(target_id, payload_json)
            if not ok:
                logger.debug(f"Нет активного WS для '{target_id}' (corr={meta.get('correlation_id')})")
            else:
                delivered += 1

        if delivered == 0:
            logger.warning(
                f"🚫 Не удалось доставить outbound-сообщение ни одному адресату: {targets} "
                f"(corr={meta.get('correlation_id')}, event={env.event})"
            )
        else:
            logger.debug(
                f"✅ Доставлено {delivered}/{len(targets)} адресатам "
                f"(corr={meta.get('correlation_id')}, event={env.event})"
            )
