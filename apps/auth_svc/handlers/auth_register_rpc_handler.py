# apps/auth_svc/handlers/auth_register_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import RegisterRequest, RegisterResponse
from libs.domain.dto.rpc import RpcResponse
from libs.app.errors import ErrorCode
from apps.auth_svc.i_auth_handler import IAuthHandler

class AuthRegisterRpcHandler(IAuthHandler):
    async def process(self, dto: RegisterRequest) -> dict: # Возвращаем dict
        # TODO: Реальная логика с БД
        return RpcResponse(
            success=False,
            error_code=ErrorCode.NOT_IMPLEMENTED,
            message="Registration is not implemented yet.",
        ).model_dump(mode="json")