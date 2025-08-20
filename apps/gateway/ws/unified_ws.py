# apps/gateway/ws/unified_ws.py
from __future__ import annotations
import asyncio
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    status,
    Depends,
    Query,
    Header,
)
from starlette.websockets import WebSocketState

from apps.gateway.gateway.client_connection_manager import ClientConnectionManager
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues, Exchanges
from libs.utils.logging_setup import app_logger as logger

from apps.gateway.dependencies import (
    get_message_bus,
    get_client_connection_manager,
    get_settings,
)
from apps.gateway.config.setting_gateway import GatewaySettings

from libs.domain.dto.ws import WSHelloFrame, WSPongFrame

router = APIRouter(tags=["Unified WebSocket"])


async def get_token_from_ws(
    websocket: WebSocket,
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Query(None),
) -> str:
    """Извлекает токен из заголовка или query-параметра."""
    if authorization:
        try:
            scheme, value = authorization.split()
            if scheme.lower() == "bearer":
                return value
        except ValueError:
            pass  # Игнорируем неверный формат заголовка
    if token:
        return token

    # Если токен не найден нигде
    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION, reason="Token not provided"
    )
    raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION, reason="Token not provided") # ИЗМЕНЕНИЕ


@router.websocket("/v1/connect")
async def unified_websocket_endpoint(
    websocket: WebSocket,
    token: str = Depends(get_token_from_ws),
    client_conn_manager: ClientConnectionManager = Depends(
        get_client_connection_manager
    ),
    message_bus: IMessageBus = Depends(get_message_bus),
    settings: GatewaySettings = Depends(get_settings),
):
    await websocket.accept()
    client_addr = f"{getattr(websocket.client, 'host', '0.0.0.0')}:{getattr(websocket.client, 'port', '0')}"
    account_id: Optional[int] = None
    conn_id: Optional[str] = None

    try:
        # 1. Валидация токена через RPC
        rpc_resp = await message_bus.call_rpc(
            exchange_name=Exchanges.RPC,
            routing_key=Queues.AUTH_VALIDATE_TOKEN_RPC,
            payload={"access_token": token},
        )

        if not (
            rpc_resp and rpc_resp.get("valid", False) and rpc_resp.get("account_id")
        ):
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token"
            )
            return

        account_id = int(rpc_resp["account_id"])
        conn_id = f"ws_{account_id}_{uuid.uuid4().hex[:8]}"

        # 2. Регистрация соединения
        await client_conn_manager.connect(
            websocket, client_id=conn_id, client_type="PLAYER"
        )
        logger.info(
            f"✅ WS connected: account_id={account_id}, conn_id={conn_id}, ip={client_addr}"
        )

        # 3. Отправка HELLO
        hello = WSHelloFrame(
            connection_id=conn_id, heartbeat_sec=settings.GATEWAY_WS_PING_INTERVAL, v=1, request_id=str(uuid.uuid4()) # ИЗМЕНЕНИЕ
        )
        await websocket.send_text(hello.model_dump_json())

        # 4. Основной цикл (пока просто держим соединение)
        while True:
            # Ждем сообщение с таймаутом, чтобы реализовать idle disconnect
            raw_data = await asyncio.wait_for(
                websocket.receive_text(), timeout=settings.GATEWAY_WS_IDLE_TIMEOUT
            )
            # В будущем здесь будет обработка входящих команд
            # Пока просто отвечаем pong на ping для keep-alive
            if "ping" in raw_data:
                await websocket.send_text(WSPongFrame(v=1, request_id=str(uuid.uuid4())).model_dump_json()) # ИЗМЕНЕНИЕ

    except WebSocketDisconnect:
        logger.info(f"🔌 WS disconnect: account_id={account_id}, conn_id={conn_id}")
    except asyncio.TimeoutError:
        logger.warning(
            f"🔌 WS idle timeout: account_id={account_id}, conn_id={conn_id}"
        )
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION, reason="Idle timeout"
            )
    except Exception as e:
        logger.exception(
            f"WS error for account_id={account_id}, conn_id={conn_id}: {e}"
        )
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(
                code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error"
            )
    finally:
        if conn_id:
            client_conn_manager.disconnect(conn_id)