# apps/auth_svc/handlers/auth_register_rpc_handler.py
from __future__ import annotations
from libs.domain.dto.auth import RegisterRequest, RegisterResponse
from libs.domain.dto.rpc import RpcResponse
from libs.app.errors import ErrorCode
from apps.auth_svc.i_auth_handler import IAuthHandler
from sqlalchemy.ext.asyncio import AsyncSession
from asyncpg.exceptions import UniqueViolationError
from sqlalchemy.exc import IntegrityError
from libs.utils.transactional_decorator import transactional


# TODO: перенести декоратор в libs/app
# TODO: добавить логику
# TODO: дописать
class AuthRegisterRpcHandler(IAuthHandler):
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    @transactional(lambda: self.session_factory())
    async def process(self, session: AsyncSession, dto: RegisterRequest) -> RpcResponse:
        from apps.auth_svc.db.auth_repository import \
            AuthRepository  # Импортируем здесь, чтобы избежать циклических зависимостей

        try:
            repo = AuthRepository(session)
            account_id, email, username = await repo.create_user(dto)

            return RpcResponse(
                success=True,
                data=RegisterResponse(
                    account_id=account_id,
                    email=email,
                    username=username
                )
            )

        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolationError):
                return RpcResponse(
                    success=False,
                    error_code=ErrorCode.AUTH_USER_EXISTS,
                    message="Пользователь с таким именем или email уже существует."
                )
            else:
                return RpcResponse(
                    success=False,
                    error_code=ErrorCode.INTERNAL_ERROR,
                    message="Ошибка базы данных при регистрации."
                )
        except Exception as e:
            return RpcResponse(
                success=False,
                error_code=ErrorCode.INTERNAL_ERROR,
                message="Внутренняя ошибка сервера."
            )