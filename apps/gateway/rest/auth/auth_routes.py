# apps/gateway/rest/auth/auth_routes.py
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request, Header

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues, Exchanges
from libs.app.errors import get_http_status, ErrorCode
from apps.gateway.dependencies import get_message_bus
from apps.gateway.rest.auth.dto import (
    APIResponse, LoginRequest, LoginResponse,
    RegisterRequest, RegisterResponse,
    ValidateResponse, ValidatedTokenData
)

# --- ИЗМЕНЕНИЕ: Префикс теперь v1 ---
router = APIRouter(prefix="/v1/auth")

@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
        request: Request,
        body: LoginRequest,
        message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_ISSUE_TOKEN_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id
    )
    if not rpc_resp or not rpc_resp.get("success"):
        error_code = rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR) if rpc_resp else ErrorCode.RPC_TIMEOUT
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Login failed.") if rpc_resp else "Auth service timeout."
        )
    return APIResponse[LoginResponse](success=True, data=rpc_resp.get("data"))


@router.post("/register", response_model=APIResponse[RegisterResponse])
async def register(
        request: Request,
        body: RegisterRequest,
        message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REGISTER_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id
    )

    if not rpc_resp:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_BAD_RESPONSE),
                            detail="Empty response from auth_svc.")

    if not rpc_resp.get("success", False):
        error_code = rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR)
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Registration failed.")
        )

    return APIResponse[RegisterResponse](success=True, data=rpc_resp.get("data"))


@router.get("/validate", response_model=APIResponse[ValidateResponse])
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
        raise HTTPException(status_code=401, detail="Invalid authorization header format")

    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_VALIDATE_TOKEN_RPC,
        payload={"access_token": token},
        correlation_id=correlation_id
    )

    if not rpc_resp:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT),
                            detail="Auth service did not respond.")

    if not rpc_resp.get("valid", False):
        raise HTTPException(status_code=401, detail=rpc_resp.get("error_message", "Invalid token"))

    token_data = ValidatedTokenData(
        account_id=rpc_resp.get("account_id"),
        client_id=rpc_resp.get("client_id"),
        scopes=rpc_resp.get("scopes", []),
        exp=rpc_resp.get("exp")
    )
    return APIResponse[ValidateResponse](success=True, data=ValidateResponse(valid=True, token_data=token_data))


@router.post("/refresh", response_model=APIResponse[RefreshTokenResponse])
async def refresh(
    request: Request,
    body: RefreshTokenRequest,
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_REFRESH_TOKEN_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id
    )
    if not rpc_resp or not rpc_resp.get("success"):
        error_code = rpc_resp.get("error_code", ErrorCode.AUTH_REFRESH_INVALID) if rpc_resp else ErrorCode.RPC_TIMEOUT
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Failed to refresh token.") if rpc_resp else "Auth service timeout."
        )
    return APIResponse[RefreshTokenResponse](success=True, data=rpc_resp.get("data"))


@router.post("/logout", response_model=APIResponse[LogoutResponse])
async def logout(
    request: Request,
    body: LogoutRequest,
    message_bus: IMessageBus = Depends(get_message_bus),
):
    correlation_id = request.headers.get("x-request-id")
    rpc_resp = await message_bus.call_rpc(
        exchange_name=Exchanges.RPC,
        routing_key=Queues.AUTH_LOGOUT_RPC,
        payload=body.model_dump(),
        correlation_id=correlation_id
    )
    # Для logout нам не важна ошибка, мы просто подтверждаем выход
    if not rpc_resp or not rpc_resp.get("success"):
        # Можно добавить логгирование, но клиенту всегда отдаем успех
        pass
    return APIResponse[LogoutResponse](success=True, data=LogoutResponse())

auth_routes_router = router