# game_server/app_gateway/ws_routers/unified_ws.py

import asyncio
import json
from typing import Optional, Dict, Any
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends
from starlette.websockets import WebSocketState


from game_server.config.logging.logging_setup import app_logger as logger
from game_server.Logic.InfrastructureLogic.messaging.i_message_bus import IMessageBus
from game_server.app_gateway.gateway.client_connection_manager import ClientConnectionManager

from game_server.app_gateway.rest_api_dependencies import get_client_connection_manager_dependency, get_message_bus_dependency
from game_server.config.settings.rabbitmq.rabbitmq_names import Exchanges, RoutingKeys, Queues
from game_server.contracts.shared_models.base_responses import ResponseStatus
from game_server.contracts.shared_models.websocket_base_models import WebSocketMessage, WebSocketResponsePayload

logger.info("--- 🚀 Загружен унифицированный WebSocket-роутер (unified_ws.py) ---")

router = APIRouter(tags=["Unified WebSocket"])

# Константы для типов клиентов
CLIENT_TYPE_PLAYER = "PLAYER"
CLIENT_TYPE_DISCORD_BOT = "DISCORD_BOT"
CLIENT_TYPE_ADMIN_PANEL = "ADMIN_PANEL"

# ЕДИНСТВЕННЫЙ УНИФИЦИРОВАННЫЙ WebSocket-эндпоинт
@router.websocket("/v1/connect")
async def unified_websocket_endpoint(
    websocket: WebSocket,
    client_conn_manager: ClientConnectionManager = Depends(get_client_connection_manager_dependency),
    message_bus: IMessageBus = Depends(get_message_bus_dependency),
    # 🔥 УДАЛЕНО: token и client_type из Query. Ожидаем их в JSON-сообщении
    # client_type: str = Query(..., alias="clientType"),
    # token: str = Query(None),
):
    client_id: Optional[str] = None
    client_type: Optional[str] = None
    client_address = f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "N/A"
    
    await websocket.accept()
    logger.info(f"🔌 Входящее соединение от {client_address} принято. Ожидание аутентификации...")

    try:
        # 🔥 ИСПРАВЛЕНО: Читаем JSON-сообщение для аутентификации
        auth_payload_str = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        auth_payload = json.loads(auth_payload_str)

        # Извлекаем данные из JSON-сообщения
        command_from_ws_auth = auth_payload.get("command") # 🔥 НОВОЕ: Ожидаем command
        token_to_validate = auth_payload.get("token")
        requested_client_type = auth_payload.get("client_type")
        bot_name_from_payload = auth_payload.get("bot_name") # Если нужно передать bot_name в RPC

        if not command_from_ws_auth or not token_to_validate or not requested_client_type: # Проверка на наличие command
            logger.warning(f"❌ Отсутствуют необходимые поля в аутентификационных данных от {client_address}.")
            raise ValueError("Missing 'command', 'token' or 'client_type' in authentication data.")

        rpc_request_data = {
            "command": command_from_ws_auth, # 🔥 ИСПРАВЛЕНО: Берем command из JSON-сообщения
            "token": token_to_validate,
            "client_type": requested_client_type,
            # Дополнительные поля для RPC, если нужны (например, bot_name)
            "bot_name": bot_name_from_payload # Передаем bot_name в RPC
        }
        
        logger.info(f"Отправка RPC-запроса на валидацию токена для типа клиента: {requested_client_type}...")
        
        validation_result = await message_bus.call_rpc(
            queue_name=Queues.AUTH_VALIDATE_TOKEN_RPC,
            payload=rpc_request_data
        )
        logger.debug(f"DEBUG_GATEWAY_RPC_RESPONSE: Получен ответ от RPC-валидации: {validation_result}")

        # Получаем payload из ответа RPC
        rpc_payload = validation_result.get("payload")

        # Проверяем, что payload существует и содержит is_valid
        if rpc_payload and rpc_payload.get("is_valid"):
            client_id = rpc_payload.get("client_id")
            client_type = rpc_payload.get("client_type")

            if not client_id or not client_type:
                error_message = "Неполные данные аутентификации от RPC-сервиса."
                logger.warning(f"❌ Аутентификация клиента {client_address} не удалась: {error_message}")
                raise ValueError(f"Authentication failed: {error_message}")

            auth_confirm_correlation_id = uuid.uuid4()

            auth_confirm_payload = WebSocketResponsePayload(
                request_id=auth_confirm_correlation_id,
                status=ResponseStatus.SUCCESS,
                message="Authentication successful.",
                data={"client_id": client_id, "client_type": client_type}
            )
            auth_confirm_message = WebSocketMessage(
                type="AUTH_CONFIRM",
                correlation_id=auth_confirm_correlation_id,
                payload=auth_confirm_payload
            )
            await websocket.send_text(auth_confirm_message.model_dump_json())
            logger.info(f"Отправлено подтверждение аутентификации клиенту {client_id}.")

        else:
            # Если payload невалиден или is_valid не True
            error_message = rpc_payload.get("error") if rpc_payload else None
            if not error_message:
                error_message = "Неизвестная ошибка валидации токена."
            logger.warning(f"❌ Аутентификация клиента {client_address} не удалась: {error_message}")
            raise ValueError(f"Authentication failed: {error_message}")

        if not client_id:
            raise ValueError("В аутентификационных данных отсутствует 'client_id' после обработки.")
        
        # --- ШАГ 2: РЕГИСТРАЦИЯ СОЕДИНЕНИЯ ---
        await client_conn_manager.connect(websocket, client_id, client_type)

        # --- ШАГ 3: ОСНОВНОЙ ЦИКЛ ОБРАБОТКИ КОМАНД ---
        while True:
            message_text = await websocket.receive_text()
            raw_message_dict = json.loads(message_text)

            websocket_msg = WebSocketMessage.model_validate(raw_message_dict)


            if websocket_msg.type == "COMMAND":
                # 1. Извлекаем "обертку" команды
                command_wrapper = websocket_msg.payload                                
                logger.debug(f"DEBUG: Содержимое 'command_wrapper': {command_wrapper}")    
                            
                # 2. Извлекаем саму "чистую" команду
                actual_command_dto = command_wrapper['payload']
                actual_command_dto['client_id'] = client_id
                # ▼▼▼ ДОБАВИТЬ ЭТУ СТРОКУ ▼▼▼
                actual_command_dto['correlation_id'] = websocket_msg.correlation_id
                # ▼▼▼ ЭТОТ БЛОК НУЖНО ПРОВЕРИТЬ И ИСПРАВИТЬ ▼▼▼
                
                # 3. Получаем домен из "обертки"
                domain = command_wrapper.get("domain", "system") # 'system' как запасной вариант
                
                # 4. Получаем имя команды из "чистой" команды
                command_name = actual_command_dto.get("command", "default")
                
                # 5. Собираем правильный ключ
                routing_key = f"{RoutingKeys.COMMAND_PREFIX}.{domain}.{command_name}"
                
                # ▲▲▲ КОНЕЦ БЛОКА ДЛЯ ПРОВЕРКИ ▲▲▲

                logger.debug(f"Получена команда от {client_id}. Ключ: '{routing_key}'.")

                await message_bus.publish(
                    exchange_name=Exchanges.COMMANDS,
                    routing_key=routing_key,
                    message=actual_command_dto
                )
                logger.info(f"Команда '{command_name}' от {client_id} опубликована в {Exchanges.COMMANDS} с ключом '{routing_key}'.")

    except WebSocketDisconnect:
        logger.info(f"Клиент {client_id or client_address} отключился.")
    except asyncio.TimeoutError:
        logger.warning(f"Таймаут аутентификации для клиента {client_address}. Соединение закрыто.")
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication timeout.")
    except Exception as e:
        logger.error(f"Произошла ошибка в WebSocket-соединении для {client_id or client_address}: {e}", exc_info=True)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal server error.")
    finally:
        if client_id:
            client_conn_manager.disconnect(client_id)
        logger.info(f"Соединение с {client_id or client_address} полностью закрыто.")
