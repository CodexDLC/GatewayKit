# apps/auth_svc/handlers/auth_logout_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import LogoutRequest, LogoutResponse
from libs.domain.dto.rpc import RpcResponse
from ..services.auth_service import AuthService


class AuthLogoutRpcHandler:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def process(self, dto: LogoutRequest) -> RpcResponse:
        """Делегирует выход из системы в AuthService."""
        error = await self.auth_service.logout(dto.refresh_token)

        if error:
            return RpcResponse(
                success=False, error_code=error, message="Logout failed."
            )

        return RpcResponse(success=True, data=LogoutResponse())
