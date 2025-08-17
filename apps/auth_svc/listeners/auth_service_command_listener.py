from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Type, Callable, Union

from pydantic import BaseModel, ValidationError

from libs.messaging.i_message_bus import IMessageBus
from ....libs.messaging.base_listener import BaseMicroserviceListener
from apps.auth_svc.handlers.i_auth_handler import IAuthHandler


DtoType = Type[BaseModel]
HandlerType = IAuthHandler
CommandMap = Dict[str, Tuple[DtoType, HandlerType]]  # "cmd.name" -> (DTO, handler)


class AuthServiceCommandListener(BaseMicroserviceListener):
    """
    Универсальный слушатель команд:
      - Поддерживает формат с envelope: {"type":"cmd.xxx", "payload":{...}}
      - И «плоский» старый формат: {"command":"cmd.xxx", ...}
    По результату:
      - Если есть meta.reply_to → отвечает через RPC (publish_rpc_response)
      - Иначе публикует событие в exchange emit_exchange с routing_key, рассчитанным routing_key_fn
    """

    def __init__(
        self,
        *,
        queue_name: str,
        message_bus: IMessageBus,
        command_map: CommandMap,
        emit_exchange: str = "EVENTS",
        routing_key_fn: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        prefetch: int = 1,
        consumer_count: int = 1,
    ) -> None:
        super().__init__(
            name="auth.commands.listener",
            queue_name=queue_name,
            message_bus=message_bus,
            prefetch=prefetch,
            consumer_count=consumer_count,
            envelope_model=None,  # валидируем DTO ниже
        )
        self._map = command_map
        self._emit_exchange = emit_exchange
        self._routing_key_fn = routing_key_fn or (lambda cmd_type, payload: f"response.{cmd_type}")

    async def process_message(self, data: Dict[str, Any], meta: Dict[str, Any]) -> None:
        # --- извлекаем тип и payload из любого формата ---
        cmd_type, payload = self._extract(data)
        if not cmd_type:
            await self._emit_error(
                code="cmd.missing_type",
                message="command type not found",
                meta=meta,
            )
            return

        entry = self._map.get(cmd_type)
        if not entry:
            await self._emit_error(
                code="cmd.unsupported",
                message=f"unsupported command: {cmd_type}",
                meta=meta,
                extra={"cmd": cmd_type},
            )
            return

        dto_cls, handler = entry

        # --- валидируем DTO ---
        try:
            dto = dto_cls.model_validate(payload)
        except ValidationError as ve:
            await self._emit_error(
                code="dto.invalid",
                message="payload validation failed",
                meta=meta,
                extra={"errors": ve.errors(), "cmd": cmd_type},
            )
            return

        # --- выполняем обработчик ---
        result = await handler.process(dto)

        # --- формируем ответ ---
        body = self._normalize_result(cmd_type, data, result, meta)

        # RPC-ответ, если есть reply_to
        reply_to = meta.get("reply_to")
        if reply_to:
            await self.bus.publish_rpc_response(reply_to=reply_to, response=body, correlation_id=meta.get("correlation_id"))
            return

        # Иначе — событие в exchange
        rk = self._routing_key_fn(cmd_type, payload)
        await self.bus.publish(self._emit_exchange, rk, body, correlation_id=meta.get("correlation_id"))

    # ---------------- helpers ----------------

    @staticmethod
    def _extract(data: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Возвращает (cmd_type, payload) для:
          - нового формата: {'type':'cmd.xxx','payload':{...}}
          - старого формата: {'command':'cmd.xxx', ...}
        """
        if "type" in data and isinstance(data["type"], str) and data["type"].startswith("cmd."):
            payload = data.get("payload") if isinstance(data.get("payload"), dict) else {}
            return data["type"], payload
        if "command" in data and isinstance(data["command"], str):
            cmd_type = data["command"]
            # старый формат — всё остальное считаем payload, кроме известных ключей
            payload = {k: v for k, v in data.items() if k not in {"command", "type", "payload"}}
            return cmd_type, payload
        return None, {}

    @staticmethod
    def _normalize_result(
        cmd_type: str,
        src: Dict[str, Any],
        result: Union[BaseModel, Dict[str, Any], Any],
        meta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Унифицируем тело ответа/события.
        """
        payload: Dict[str, Any]
        if isinstance(result, BaseModel):
            payload = result.model_dump(mode="json")
        elif isinstance(result, dict):
            payload = result
        else:
            payload = {"result": result}

        return {
            "type": f"response.{cmd_type}",
            "version": 1,
            "request_id": src.get("request_id"),
            "correlation_id": meta.get("correlation_id"),
            "payload": payload,
        }

    async def _emit_error(self, *, code: str, message: str, meta: Dict[str, Any], extra: Optional[Dict[str, Any]] = None) -> None:
        body = {
            "type": "error",
            "code": code,
            "message": message,
            "correlation_id": meta.get("correlation_id"),
            "details": extra or {},
        }
        reply_to = meta.get("reply_to")
        if reply_to:
            await self.bus.publish_rpc_response(reply_to=reply_to, response=body, correlation_id=meta.get("correlation_id"))
        else:
            await self.bus.publish(self._emit_exchange, "response.error", body, correlation_id=meta.get("correlation_id"))
