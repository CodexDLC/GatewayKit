# apps/auth_svc/config/auth_service_config.py
from __future__ import annotations

from libs.domain.dto import IssueTokenRequest, ValidateTokenRequest, RegisterRequest
from libs.messaging.rabbitmq_names import Queues

# Карта DTO для RPC может остаться, если она используется для валидации или mapping
RPC_DTO_MAP = {
    Queues.AUTH_ISSUE_TOKEN_RPC:    IssueTokenRequest,
    Queues.AUTH_VALIDATE_TOKEN_RPC: ValidateTokenRequest,
    Queues.AUTH_REGISTER_RPC:       RegisterRequest,
}

