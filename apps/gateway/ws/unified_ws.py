# apps/gateway/ws/unified_ws.py
from __future__ import annotations

import asyncio
import json
import uuid
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from starlette.websockets import WebSocketState

from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues, Exchanges
from libs.utils.logging_setup import app_logger as logger

# --- DI зависимости (settings опционально) ---
from apps.gateway.dependencies import get_message_bus, get_client_connection_manager
try:
    from apps.gateway.dependencies import get_settings
except Exception:
    get_settings = None  # settings может отсутствовать на этом этапе

# --- Новые DTO ---
from libs.domain.dto.ws import (
    ClientWSFrame, WSCommandFrame, WSPongFrame, WSHelloFrame, WSErrorFrame
)
from libs.domain.dto.backend import BackendInboundCommandEnvelope, RoutingInfo, AuthInfo, OriginInfo


router = APIRouter(tags=["Unified WebSocket"])

def _defaults():
    # TODO: заменить на GatewaySettings из .env, когда добавите get_settings
    return SimpleNamespace(
        WS_HEARTBEAT_SEC=30,
        WS_AUTH_TIMEOUT_SEC=5,
        WS_MAX_MSG_BYTES=65536,
    )

@router.websocket("/v1/connect")
async def unified_websocket_endpoint(
    websocket: WebSocket,
    client_conn_manager: ClientConnectionManager = Depends(get_client_connection_manager),
    message_bus: IMessageBus = Depends(get_message_bus),
    settings: Optional[object] = Depends(get_settings) if get_settings else None,
):
    cfg = settings or _defaults()
    await websocket.accept()
    client_addr = f"{getattr(websocket.client, 'host', '0.0.0.0')}:{getattr(websocket.client, 'port', '0')}"
    account_id: Optional[int] = None
    conn_key: Optional[str] = None

    logger.info(f"🔌 WS: входящее соединение от {client_addr}. Ожидаем auth.validate_token ...")

    try:
        # --- 1) Первое сообщение = auth.validate_token ---
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=cfg.WS_AUTH_TIMEOUT_SEC)
        try:
            data = json.loads(raw)
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid JSON")
            return

        try:
            frame = ClientWSFrame.model_validate(data)
        except Exception as e:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid frame schema")
            return

        if not (isinstance(frame, WSCommandFrame) and frame.domain == "auth" and frame.command == "validate_token"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="First message must be auth.validate_token")
            return

        token = (frame.payload or {}).get("token")
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token required")
            return

        # RPC в auth для валидации токена
        try:
            rpc_resp = await message_bus.call_rpc(
                queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
                payload={"token": token},
                timeout=cfg.WS_AUTH_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Auth service timeout")
            return

        if not (rpc_resp and rpc_resp.get("valid", False)):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token")
            return

        # Берём account_id (INTEGER как ты просил)
        try:
            account_id = int(rpc_resp.get("account_id"))
        except Exception:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Auth response missing account_id")
            return

        # Регистрируем соединение (ключи менеджера строковые)
        conn_key = str(account_id)
        await client_conn_manager.connect(websocket, client_id=conn_key, client_type="PLAYER")

        # Отправляем HELLO
        hello = WSHelloFrame(connection_id=conn_key, heartbeat_sec=cfg.WS_HEARTBEAT_SEC)
        await websocket.send_text(hello.model_dump_json())

        logger.info(f"✅ WS авторизован: account_id={account_id}")

        # --- 2) Основной цикл приёма кадров ---
        while True:
            msg = await websocket.receive_text()

            # Лёгкий ping без полной схемы
            if msg.strip().startswith('{"type":"ping"'):
                pong = WSPongFrame()
                await websocket.send_text(pong.model_dump_json())
                continue

            data = json.loads(msg)
            frame = ClientWSFrame.model_validate(data)

            if isinstance(frame, WSCommandFrame):
                # Публикуем команду в шину (cmd.<domain>.<command>)
                rqid = frame.request_id or f"req_{uuid.uuid4().hex}"
                env = BackendInboundCommandEnvelope(
                    request_id=rqid,
                    routing=RoutingInfo(domain=frame.domain, command=frame.command),
                    auth=AuthInfo(account_id=account_id),
                    origin=OriginInfo(transport="ws", connection_id=conn_key, ip=getattr(websocket.client, 'host', None)),
                    payload=frame.payload or {},
                )
                routing_key = f"{RoutingKeys.COMMAND_PREFIX}.{frame.domain}.{frame.command}"  # "cmd.<domain>.<command>"
                await message_bus.publish(
                    exchange_name=Exchanges.COMMANDS,
                    routing_key=routing_key,
                    message=env.model_dump(mode="json"),
                    correlation_id=rqid,
                )
            else:
                # subscribe/unsubscribe не реализованы пока
                err = WSErrorFrame(error={"code": "common.NOT_IMPLEMENTED", "message": "Only 'command' supported now"})
                await websocket.send_text(err.model_dump_json())

    except WebSocketDisconnect:
        logger.info(f"WS disconnect: {conn_key or client_addr}")
    except asyncio.TimeoutError:
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout")
    except Exception as e:
        logger.exception("WS error")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error")
    finally:
        if conn_key:
            client_conn_manager.disconnect(conn_key)
        logger.info(f"WS close: {conn_key or client_addr}")
