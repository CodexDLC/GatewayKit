from __future__ import annotations
from typing import Any, Dict, Optional
from pydantic import ValidationError
from libs.messaging.base_listener import BaseMicroserviceListener
from libs.messaging.i_message_bus import IMessageBus

from apps.auth_svc.handlers.auth_register_rpc_handler import (
    AuthRegisterRpcHandler, RegisterRequest
)

class AuthRegisterRpc(BaseMicroserviceListener):
    def __init__(self, *, queue_name: str, message_bus: IMessageBus,
                 handler: AuthRegisterRpcHandler, prefetch: int = 1, consumer_count: int = 1) -> None:
        super().__init__(name="auth.register.rpc", queue_name=queue_name,
                         message_bus=message_bus, prefetch=prefetch,
                         consumer_count=consumer_count, envelope_model=None)
        self._handler = handler

    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        payload = data["payload"] if isinstance(data, dict) and isinstance(data.get("payload"), dict) else data
        try:
            req = RegisterRequest.model_validate(payload)
        except ValidationError as ve:
            await self._reply(meta.get("reply_to"), meta.get("correlation_id"),
                              {"success": False, "error_code": "dto.invalid", "error_message": ve.errors()})
            return
        resp = await self._handler.process(req)
        await self._reply(meta.get("reply_to"), meta.get("correlation_id"), resp.model_dump(mode="json"))

    async def _reply(self, reply_to: Optional[str], correlation_id: Optional[str], body: Dict[str, Any]) -> None:
        if not reply_to:
            return
        await self.bus.publish_rpc_response(reply_to=reply_to, response=body, correlation_id=correlation_id)
