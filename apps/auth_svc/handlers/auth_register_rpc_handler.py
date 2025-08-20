# apps/auth_svc/handlers/auth_register_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import RegisterRequest, RegisterResponse
from libs.domain.dto.rpc import RpcResponse
from ..services.auth_service import AuthService


class AuthRegisterRpcHandler:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def process(self, dto: RegisterRequest) -> RpcResponse:
        """Делегирует создание аккаунта в AuthService."""
        account, error = await self.auth_service.register(dto)

        if error:
            return RpcResponse(
                success=False, error_code=error, message="Registration failed."
            )

        # ДОБАВЛЕНО: Проверка на None
        if account:
            return RpcResponse(
                success=True,
                data=RegisterResponse(
                    account_id=account.id, email=account.email, username=account.username
                ),
            )
        else:
            return RpcResponse(success=False, error_code="auth.internal_error", message="Account not created.")