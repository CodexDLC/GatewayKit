# apps/gateway/rest/auth/auth_routes.py
from fastapi import APIRouter, Depends, HTTPException, Request, Header

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues, Exchanges
from libs.app.errors import get_http_status, ErrorCode
from apps.gateway.dependencies import get_message_bus

# --- ИМПОРТЫ ОБНОВЛЕНЫ НА НОВЫЕ ИМЕНА DTO ---
from .dto import (
    APIResponse,
    ApiLoginRequest,
    ApiLoginResponse,
    ApiRegisterRequest,
    ApiRegisterResponse,
    ApiValidateResponse,
    ApiRefreshTokenRequest,
    ApiRefreshTokenResponse,
    ApiLogoutRequest,
    ApiLogoutResponse,
)

router = APIRouter(prefix="/v1/auth")


@router.post("/login", response_model=APIResponse[ApiLoginResponse])
async def login(
    request: Request,
    body: ApiLoginRequest,  # <-- ИСПОЛЬЗУЕМ НОВОЕ ИМЯ
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id,
    )
    if not rpc_resp or not rpc_resp.get("success"):
        error_code = (
            rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR)
            if rpc_resp
            else ErrorCode.RPC_TIMEOUT
        )
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=(
                rpc_resp.get("message", "Login failed.")
                if rpc_resp
                else "Auth service timeout."
            ),
        )
    return APIResponse[ApiLoginResponse](success=True, data=rpc_resp.get("data"))


@router.post("/register", response_model=APIResponse[ApiRegisterResponse])
async def register(
    request: Request,
    body: ApiRegisterRequest,  # <-- ИСПОЛЬЗУЕМ НОВОЕ ИМЯ
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REGISTER_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id,
    )
    if not rpc_resp or not rpc_resp.get("success"):
        error_code = (
            rpc_resp.get("error_code", ErrorCode.AUTH_USER_EXISTS)
            if rpc_resp
            else ErrorCode.RPC_TIMEOUT
        )
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=(
                rpc_resp.get("message", "Registration failed.")
                if rpc_resp
                else "Auth service timeout."
            ),
        )
    return APIResponse[ApiRegisterResponse](success=True, data=rpc_resp.get("data"))


@router.get("/validate", response_model=APIResponse[ApiValidateResponse])
async def validate_token(
    request: Request,
    authorization: str = Header(...),
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    try:
        token_type, token = authorization.split()
        if token_type.lower() != "bearer":
            raise ValueError("Invalid token type")
    except ValueError:
        raise HTTPException(
            status_code=401, detail="Invalid authorization header format"
        )

    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_VALIDATE_TOKEN_RPC,
        payload={"access_token": token},
        correlation_id=correlation_id,
    )
    if not rpc_resp or not rpc_resp.get("valid"):
        raise HTTPException(
            status_code=401,
            detail=(
                rpc_resp.get("error_message", "Invalid token")
                if rpc_resp
                else "Auth service timeout."
            ),
        )

    # ИЗМЕНЕНИЕ: Преобразование dict в DTO
    return APIResponse[ApiValidateResponse](
        success=True, data=ApiValidateResponse(**rpc_resp)
    )


@router.post("/refresh", response_model=APIResponse[ApiRefreshTokenResponse])
async def refresh(
    request: Request,
    body: ApiRefreshTokenRequest,  # <-- ИСПОЛЬЗУЕМ НОВОЕ ИМЯ
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REFRESH_TOKEN_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id,
    )
    if not rpc_resp or not rpc_resp.get("success"):
        error_code = (
            rpc_resp.get("error_code", ErrorCode.AUTH_REFRESH_INVALID)
            if rpc_resp
            else ErrorCode.RPC_TIMEOUT
        )
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=(
                rpc_resp.get("message", "Failed to refresh token.")
                if rpc_resp
                else "Auth service timeout."
            ),
        )
    return APIResponse[ApiRefreshTokenResponse](success=True, data=rpc_resp.get("data"))


@router.post("/logout", response_model=APIResponse[ApiLogoutResponse])
async def logout(
    request: Request,
    body: ApiLogoutRequest,  # <-- ИСПОЛЬЗУЕМ НОВОЕ ИМЯ
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_LOGOUT_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id,
    )
    # Для logout клиенту всегда возвращаем успех, даже если токен уже был невалиден
    return APIResponse[ApiLogoutResponse](success=True, data=ApiLogoutResponse())


auth_routes_router = router
