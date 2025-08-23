# apps/gateway/ws/unified_ws.py
from __future__ import annotations

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
            pass
    if token:
        return token

    await websocket.close(
        code=status.WS_1008_POLICY_VIOLATION, reason="Token not provided"
    )
    raise WebSocketDisconnect(
        code=status.WS_1008_POLICY_VIOLATION, reason="Token not provided"
    )


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
        # 1. Валидация токена через RPC (без изменений)
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

        # 2. Регистрация соединения (без изменений)
        await client_conn_manager.connect(
            websocket, client_id=conn_id, client_type="PLAYER"
        )
        logger.info(
            f"✅ WS connected: account_id={account_id}, conn_id={conn_id}, ip={client_addr}"
        )

        # 3. Отправка HELLO (без изменений)
        hello = WSHelloFrame(
            connection_id=conn_id,
            heartbeat_sec=settings.GATEWAY_WS_PING_INTERVAL,
            v=1,
            request_id=str(uuid.uuid4()),
        )
        await websocket.send_text(hello.model_dump_json())

        # --- ГЛАВНОЕ ИЗМЕНЕНИЕ ЗДЕСЬ ---
        # 4. Основной цикл теперь без блокирующего таймаута
        while True:
            # Просто ждем сообщение от клиента
            raw_data = await websocket.receive_text()

            # При любом сообщении обновляем время активности
            if conn_id:
                client_conn_manager.update_activity(conn_id)

            # В будущем здесь будет обработка входящих команд
            if "ping" in raw_data:
                await websocket.send_text(
                    WSPongFrame(v=1, request_id=str(uuid.uuid4())).model_dump_json()
                )

    except WebSocketDisconnect:
        logger.info(f"🔌 WS disconnect: account_id={account_id}, conn_id={conn_id}")
    # Убираем обработку asyncio.TimeoutError, так как ее больше не будет
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
