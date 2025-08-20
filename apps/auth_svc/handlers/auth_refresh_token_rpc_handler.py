# apps/auth_svc/handlers/auth_refresh_token_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import RefreshTokenRequest, RefreshTokenResponse
from libs.domain.dto.rpc import RpcResponse
from ..services.auth_service import AuthService



class AuthRefreshTokenRpcHandler:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def process(self, dto: RefreshTokenRequest) -> RpcResponse:
        """Делегирует обновление токена в AuthService."""
        token_data, error = await self.auth_service.refresh_token(dto.refresh_token)

        if error:
            return RpcResponse(
                success=False, error_code=error, message="Failed to refresh token."
            )

        # ИЗМЕНЕНИЕ: Явно приводим token_data к типу dict
        return RpcResponse(success=True, data=RefreshTokenResponse(**token_data))