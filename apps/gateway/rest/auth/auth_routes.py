# apps/gateway/rest/auth/auth_routes.py
import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from apps.gateway.dependencies import get_message_bus
from libs.messaging.i_message_bus import IMessageBus
from libs.messaging.rabbitmq_names import Queues

from apps.gateway.rest.auth.dto import APIResponse, AuthRequest, AuthResponse, RegisterResponse, RegisterRequest

router = APIRouter()

@router.post("/token", response_model=APIResponse[AuthResponse])
async def issue_token(
    body: Annotated[AuthRequest, Depends()],
    message_bus: IMessageBus = Depends(get_message_bus),
):
    payload = {
        "grant_type": "password",
        "username": body.username,
        "password": body.password,
    }
    if body.otp_code:
        payload["otp_code"] = body.otp_code

    # RPC к auth_svc
    try:
        rpc_resp = await message_bus.call_rpc(
            queue_name=Queues.AUTH_ISSUE_TOKEN_RPC,  # <- единая очередь выдачи токена
            payload=payload,
            timeout=5,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Сервис аутентификации не отвечает.")

    if not rpc_resp:
        raise HTTPException(status_code=502, detail="Пустой ответ от auth_svc.")
    if not rpc_resp.get("success", True):
        raise HTTPException(status_code=401, detail=rpc_resp.get("error_message", "Не удалось выдать токен."))

    try:
        account_id = int(rpc_resp.get("account_id"))
    except Exception:
        raise HTTPException(status_code=502, detail="auth_svc не вернул account_id.")

    return APIResponse[AuthResponse](
        success=True,
        data=AuthResponse(
            token=rpc_resp["token"],
            expires_in=int(rpc_resp["expires_in"]),
            account_id=account_id,
        ),
    )

@router.post("/register", response_model=APIResponse[RegisterResponse])
async def register(
        body: Annotated[RegisterRequest, Depends()],
        message_bus: IMessageBus = Depends(get_message_bus),
    ):
    try:
         rpc = await message_bus.call_rpc(
                queue_name=Queues.AUTH_REGISTER_RPC,
                payload=body.model_dump(),
                timeout=5,
            )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Сервис регистрации не отвечает.")

    if not rpc or not rpc.get("success", False):
            # ожидаем, что сервис вернёт {success:false, error_code?, error_message?} пока БД не подключена
        raise HTTPException(status_code=501, detail=rpc.get("error_message", "Регистрация ещё не реализована."))

    return APIResponse[RegisterResponse](
            success=True,
            data=RegisterResponse(
                account_id=int(rpc["account_id"]),
                email=rpc["email"],
                username=rpc["username"],
            ),
        )
# роутер наружу
auth_routes_router = router
