# apps/auth_svc/handlers/auth_issue_token_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import IssueTokenRequest, IssueTokenResponse
from libs.domain.dto.rpc import RpcResponse
from ..services.auth_service import AuthService


class AuthIssueTokenRpcHandler:
    def __init__(self, auth_service: AuthService) -> None:
        self.auth_service = auth_service

    async def process(self, dto: IssueTokenRequest) -> RpcResponse:
        """Делегирует выпуск токена в AuthService."""
        # TODO: Добавить account_id в ответ, когда сервис будет его возвращать
        token, error = await self.auth_service.issue_token(dto)

        if error:
            return RpcResponse(
                success=False,
                error_code=error,
                message="Failed to issue token."
            )

        return RpcResponse(
            success=True,
            data=IssueTokenResponse(
                token=token,
                expires_in=3600,  # TODO: Брать из настроек
                account_id=0  # TODO: Вернуть реальный ID
            )
        )