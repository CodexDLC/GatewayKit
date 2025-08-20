# apps/auth_svc/listeners/auth_refresh_token_rpc.py
from __future__ import annotations
from typing import Any, Dict

from pydantic import ValidationError

from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.i_message_bus import IMessageBus
from libs.domain.dto.auth import RefreshTokenRequest
from apps.auth_svc.handlers.auth_refresh_token_rpc_handler import (
    AuthRefreshTokenRpcHandler,
)
from libs.domain.dto.rpc import RpcResponse
from libs.app.errors import ErrorCode


class AuthRefreshTokenRpc(BaseMicroserviceListener):
    def __init__(
        self,
        *,
        queue_name: str,
        message_bus: IMessageBus,
        handler: AuthRefreshTokenRpcHandler,
        **kwargs,
    ) -> None:
        super().__init__(
            name="auth.refresh_token.rpc",
            queue_name=queue_name,
            message_bus=message_bus,
            **kwargs,
        )
        self._handler = handler

    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        payload = data.get("payload", data)
        try:
            req = RefreshTokenRequest.model_validate(payload)
        except ValidationError as ve:
            rpc_response: RpcResponse = RpcResponse(
                success=False, error_code=ErrorCode.VALIDATION_FAILED, message=str(ve)
            )
            await self._reply(meta, rpc_response)
            return

        rpc_response = await self._handler.process(req) # ИЗМЕНЕНИЕ: убрали повторное объявление типа
        await self._reply(meta, rpc_response)

    async def _reply(self, meta: Dict[str, Any], rpc_response: RpcResponse):
        reply_to = meta.get("reply_to")
        correlation_id = meta.get("correlation_id")
        if not reply_to:
            return

        rpc_response.correlation_id = correlation_id
        await self.bus.publish_rpc_response(
            reply_to=reply_to,
            response=rpc_response.model_dump(mode="json"),
            correlation_id=correlation_id,
        )