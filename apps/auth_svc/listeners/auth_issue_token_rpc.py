from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import ValidationError

from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.i_message_bus import IMessageBus

from apps.auth_svc.handlers.auth_issue_token_rpc_handler import (
    AuthIssueTokenRpcHandler,
    IssueTokenRequest,
)


class AuthIssueTokenRpc(BaseMicroserviceListener):
    """
    RPC-слушатель: выдача access_token (JWT).
    Вход: envelope с payload или плоский DTO.
    Ответ: JSON в reply_to с тем же correlation_id.
    """

    def __init__(
        self,
        *,
        queue_name: str,
        message_bus: IMessageBus,
        handler: AuthIssueTokenRpcHandler,
        prefetch: int = 1,
        consumer_count: int = 1,
    ) -> None:
        super().__init__(
            name="auth.issue_token.rpc",
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
            payload = data

        # Валидация DTO
        try:
            req = IssueTokenRequest.model_validate(payload)
        except ValidationError as ve:
            await self._reply(
                reply_to=meta.get("reply_to"),
                correlation_id=meta.get("correlation_id"),
                body={
                    "error_code": "dto.invalid",
                    "error_message": ve.errors(),
                },
            )
            return

        # Выполнить обработчик
        resp = await self._handler.process(req)

        # Ответ RPC
        await self._reply(
            reply_to=meta.get("reply_to"),
            correlation_id=meta.get("correlation_id"),
            body=resp.model_dump(mode="json"),
        )

    async def _reply(self, *, reply_to: Optional[str], correlation_id: Optional[str], body: Dict[str, Any]) -> None:
        if not reply_to:
            return
        await self.bus.publish_rpc_response(reply_to=reply_to, response=body, correlation_id=correlation_id)
