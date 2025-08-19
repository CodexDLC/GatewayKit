# apps/gateway/rest/auth/auth_routes.py
import asyncio

from fastapi import APIRouter, Depends, HTTPException

from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues
from libs.app.errors import get_http_status, ErrorCode
from apps.gateway.dependencies import get_message_bus
from apps.gateway.rest.auth.dto import APIResponse, AuthRequest, AuthResponse, RegisterResponse, RegisterRequest

router = APIRouter()


@router.post("/token", response_model=APIResponse[AuthResponse])
async def issue_token(
        body: AuthRequest,  # Убрал Depends() для ясности
        message_bus: IMessageBus = Depends(get_message_bus),
):
    payload = body.model_dump()

    try:
        rpc_resp = await message_bus.call_rpc(
            queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,
            payload=payload,
            timeout=5,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT), detail="Auth service timeout.")

    if not rpc_resp:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_BAD_RESPONSE),
                            detail="Empty response from auth_svc.")

    if not rpc_resp.get("success", False):
        error_code = rpc_resp.get("error_code", ErrorCode.INTERNAL_ERROR)
        raise HTTPException(
            status_code=get_http_status(error_code),
            detail=rpc_resp.get("message", "Failed to issue token.")
        )

    # Pydantic сам вызовет ошибку, если data не соответствует AuthResponse
    return APIResponse[AuthResponse](success=True, data=rpc_resp.get("data"))


@router.post("/register", response_model=APIResponse[RegisterResponse])
async def register(
        body: RegisterRequest,
        message_bus: IMessageBus = Depends(get_message_bus),
):
    try:
        rpc_resp = await message_bus.call_rpc(
            queue_name=Queues.AUTH_REGISTER_RPC,
            payload=body.model_dump(),
            timeout=5,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=get_http_status(ErrorCode.RPC_TIMEOUT), detail="Registration service timeout.")

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


auth_routes_router = router