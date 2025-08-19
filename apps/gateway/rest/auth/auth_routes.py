# apps/gateway/rest/auth/auth_routes.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request  # <-- Добавил Request

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues, Exchanges  # <-- Добавил Exchanges
from libs.app.errors import get_http_status, ErrorCode
from apps.gateway.dependencies import get_message_bus
from apps.gateway.rest.auth.dto import APIResponse, AuthRequest, AuthResponse, RegisterResponse, RegisterRequest

router = APIRouter()


@router.post("/token", response_model=APIResponse[AuthResponse])
async def issue_token(
        request: Request,  # <-- Добавил Request
        body: AuthRequest,
        message_bus: IMessageBus = Depends(get_message_bus),
):
    payload = body.model_dump()
    # Пробрасываем X-Request-ID как correlation_id
    correlation_id = request.headers.get("x-request-id")

    try:
        rpc_resp = await message_bus.call_rpc(
            exchange_name=Exchanges.RPC,  # <-- ИЗМЕНЕНИЕ
            routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,  # <-- ИЗМЕНЕНИЕ
            payload=payload,
            correlation_id=correlation_id
        )
    except asyncio.TimeoutError:  # Эта ошибка теперь ловится внутри call_rpc, но оставим на всякий случай
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT), detail="Auth service timeout.")

    if not rpc_resp:
        # Может быть таймаут или unroutable
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT),
                            detail="Auth service did not respond or is unavailable.")

    if not rpc_resp.get("success", False):
        error_code = rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR)
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Failed to issue token.")
        )

    return APIResponse[AuthResponse](success=True, data=rpc_resp.get("data"))


# Аналогичные изменения для register...
@router.post("/register", response_model=APIResponse[RegisterResponse])
async def register(
        request: Request,  # <-- Добавил Request
        body: RegisterRequest,
        message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    try:
        rpc_resp = await message_bus.call_rpc(
            exchange_name=Exchanges.RPC,  # <-- ИЗМЕНЕНИЕ
            routing_key=Queues.AUTH_REGISTER_RPC,  # <-- ИЗМЕНЕНИЕ
            payload=body.model_dump(),
            correlation_id=correlation_id
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT), detail="Registration service timeout.")

    if not rpc_resp:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_BAD_RESPONSE),
                            detail="Empty or unroutable response from auth_svc.")

    if not rpc_resp.get("success", False):
        error_code = rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR)
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Registration failed.")
        )

    return APIResponse[RegisterResponse](success=True, data=rpc_resp.get("data"))


auth_routes_router = router