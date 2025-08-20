from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.i_message_bus import IMessageBus

from apps.auth_svc.handlers.auth_validate_token_rpc_handler import (
    AuthValidateTokenRpcHandler,
    ValidateTokenRequest,
)


class AuthValidateTokenRpc(BaseMicroserviceListener):
    """
    RPC-слушатель: принимает запрос на валидацию токена и отвечает в reply_to.
    Формат входа:
      - либо envelope с полем payload (рекомендуемо),
      - либо сразу JSON DTO (fallback).
    Ответ отправляется как JSON в очередь reply_to с тем же correlation_id.
    """

    def __init__(
        self,
        *,
        queue_name: str,
        message_bus: IMessageBus,
        handler: AuthValidateTokenRpcHandler,
        prefetch: int = 1,
        consumer_count: int = 1,
    ) -> None:
        super().__init__(
            name="auth.validate_token.rpc",
            queue_name=queue_name,
            message_bus=message_bus,
            prefetch=prefetch,
            consumer_count=consumer_count,
            envelope_model=None,
        )
        self._handler = handler

    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        # Извлечь payload (envelope или плоский JSON)
        payload: Dict[str, Any]
        if "payload" in data and isinstance(data["payload"], dict):
            payload = data["payload"]
        else:
            payload = data  # fallback: прислали сразу DTO

        # Валидация DTO
        try:
            # alias: поддерживаем payload["token"] как синоним "access_token"
            if "token" in payload and "access_token" not in payload:
                payload["access_token"] = payload.pop("token")
            req = ValidateTokenRequest.model_validate(payload)
        except ValidationError as ve:
            # Формируем отрицательный ответ без исключения (RPC-ответ)
            await self._reply(
                reply_to=meta.get("reply_to"),
                correlation_id=meta.get("correlation_id"),
                body={
                    "valid": False,
                    "error_code": "dto.invalid",
                    "error_message": ve.errors(),
                },
            )
            return

        # Выполнить обработчик
        resp = await self._handler.process(req)

        # Ответить в reply_to
        await self._reply(
            reply_to=meta.get("reply_to"),
            correlation_id=meta.get("correlation_id"),
            body=resp.model_dump(mode="json"),
        )

    async def _reply(
        self,
        *,
        reply_to: Optional[str],
        correlation_id: Optional[str],
        body: Dict[str, Any],
    ) -> None:
        if not reply_to:
            # Некуда отвечать — считаем одноразовой командой, просто игнорируем
            return
        await self.bus.publish_rpc_response(
            reply_to=reply_to, response=body, correlation_id=correlation_id
        )
