# game_server/app_gateway/rest_routers/auth_routes.py

import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Annotated

from game_server.Logic.InfrastructureLogic.messaging.i_message_bus import IMessageBus
from game_server.app_gateway.rest_api_dependencies import get_message_bus_dependency

from game_server.config.settings.rabbitmq.rabbitmq_names import Exchanges, Queues, RoutingKeys
from game_server.config.logging.logging_setup import app_logger as logger

from game_server.contracts.api_models.auth.requests import AuthRequest
from game_server.contracts.api_models.auth.responses import AuthResponse
from game_server.contracts.api_models.system.requests import DiscordShardLoginRequest, HubRoutingRequest
from game_server.contracts.shared_models.base_responses import APIResponse, SuccessResponse

# Импорт моделей запроса и ответа


# Префикс будет добавляться при подключении роутера в основном файле приложения
router = APIRouter(tags=["Authentication"])

@router.post(
    "/hub-registered", # ИЗМЕНЕНО: Путь роута
    response_model=APIResponse[SuccessResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Инициировать регистрацию/первичный вход через Хаб" # ИЗМЕНЕНО: Описание
)
async def hub_login_command(
    request_data: HubRoutingRequest,
    message_bus: Annotated[IMessageBus, Depends(get_message_bus_dependency)],
    x_client_id: Annotated[str | None, Header()] = None
):
    """
    Принимает запрос от бота на маршрутизацию игрока, отправляет команду в сервис
    аутентификации и немедленно возвращает 202.
    """
    logger.info(f"Получен REST-запрос на hub-login для discord_id: {request_data.discord_user_id}.")
    
    if not x_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTP заголовок 'X-Client-ID' является обязательным.")

    command_payload = request_data.model_dump()
    command_payload['client_id'] = x_client_id
    
    routing_key = f"{RoutingKeys.COMMAND_PREFIX}.auth.hub_login"
    
    try:
        await message_bus.publish(Exchanges.COMMANDS, routing_key, command_payload)
        logger.info(f"Команда 'hub_login' для {request_data.discord_user_id} (CorrID: {request_data.correlation_id}) опубликована.")
        return APIResponse(success=True, message="Команда на маршрутизацию принята.", data=SuccessResponse(correlation_id=request_data.correlation_id))
    except Exception as e:
        logger.error(f"Ошибка публикации команды 'hub_login': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка отправки команды.")

@router.post(
    "/session-login",
    response_model=APIResponse[SuccessResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Инициировать создание игровой сессии"
)
async def create_session_command(
    request_data: DiscordShardLoginRequest,
    message_bus: Annotated[IMessageBus, Depends(get_message_bus_dependency)],
    x_client_id: Annotated[str | None, Header()] = None
):
    """
    Принимает запрос от бота на создание сессии, отправляет команду в сервис
    аутентификации и немедленно возвращает 202.
    """
    logger.info(f"Получен REST-запрос на session-login для discord_id: {request_data.discord_user_id}.")

    if not x_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTP заголовок 'X-Client-ID' является обязательным.")

    command_payload = request_data.model_dump()
    command_payload['client_id'] = x_client_id
    
    routing_key = f"{RoutingKeys.COMMAND_PREFIX}.auth.session_login"

    try:
        await message_bus.publish(Exchanges.COMMANDS, routing_key, command_payload)
        logger.info(f"Команда 'session_login' для {request_data.discord_user_id} (CorrID: {request_data.correlation_id}) опубликована.")
        return APIResponse(success=True, message="Команда на создание сессии принята.", data=SuccessResponse(correlation_id=request_data.correlation_id))
    except Exception as e:
        logger.error(f"Ошибка публикации команды 'session_login': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Ошибка отправки команды.")
    
    
@router.post(
    "/token",
    response_model=APIResponse[AuthResponse],
    status_code=status.HTTP_200_OK,
    summary="Универсальный эндпоинт для получения токена аутентификации"
)
async def get_auth_token(
    request_data: AuthRequest,
    message_bus: Annotated[IMessageBus, Depends(get_message_bus_dependency)],
):
    logger.info(f"Получен REST-запрос на /token от клиента типа: {request_data.client_type}.")

    
    rpc_request_payload = request_data.model_dump()
    rpc_request_payload['command'] = "issue_auth_token" 
    
    rpc_queue_name = None

    if request_data.client_type == "DISCORD_BOT":
        if not request_data.bot_name or not request_data.bot_secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для DISCORD_BOT требуются bot_name и bot_secret.")
        rpc_queue_name = Queues.AUTH_ISSUE_BOT_TOKEN_RPC
        logger.info(f"Запрос токена для Discord-бота: {request_data.bot_name}")

    elif request_data.client_type == "PLAYER":
        if not request_data.username or not request_data.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Для PLAYER требуются username и password.")
        rpc_queue_name = Queues.AUTH_ISSUE_PLAYER_TOKEN_RPC
        logger.info(f"Запрос токена для игрока: {request_data.username}")

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Неизвестный тип клиента: {request_data.client_type}.")

    if not rpc_queue_name:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Не удалось определить RPC-очередь для типа клиента.")

    try:
        rpc_response_full = await message_bus.call_rpc( # Переименовал для ясности
            queue_name=rpc_queue_name,
            payload=rpc_request_payload,
            timeout=5
        )

        # 🔥 ИСПРАВЛЕНО: Извлекаем payload из полного RPC-ответа
        rpc_response_payload = rpc_response_full.get("payload")

        if rpc_response_payload and rpc_response_payload.get("success"): # <-- ИСПОЛЬЗУЕМ rpc_response_payload
            issued_token = rpc_response_payload.get("token") # <-- ИСПОЛЬЗУЕМ rpc_response_payload
            expires_in = rpc_response_payload.get("expires_in") # <-- ИСПОЛЬЗУЕМ rpc_response_payload
            
            if not issued_token:
                logger.error("RPC-ответ от AuthService не содержит 'token' в payload.")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Сервер не смог выдать токен.")
            
            logger.info(f"Токен успешно выдан для клиента типа {request_data.client_type}.")
            return APIResponse(success=True, message="Токен выдан.", data=AuthResponse(token=issued_token, expires_in=expires_in))
        else:
            # 🔥 ИСПРАВЛЕНО: Извлекаем ошибку из payload
            error_message = rpc_response_payload.get("error", "Неизвестная ошибка AuthService.") if rpc_response_payload else "Неизвестная ошибка AuthService."
            logger.warning(f"AuthService отказал в выдаче токена для клиента типа {request_data.client_type}: {error_message}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_message)

    except Exception as e:
        logger.error(f"Ошибка при RPC-вызове get_auth_token для типа {request_data.client_type}: {e}", exc_info=True)
        # Проверяем, является ли исключение HTTPException, чтобы не обернуть его дважды
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Внутренняя ошибка сервера при выдаче токена.")



auth_routes_router = router