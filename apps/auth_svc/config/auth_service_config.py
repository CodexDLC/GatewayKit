from __future__ import annotations
from typing import Dict, Type
from pydantic import BaseModel

from apps.auth_svc.handlers.auth_issue_token_rpc_handler import IssueTokenRequest
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import ValidateTokenRequest

class Exchanges:
    EVENTS = "EVENTS"

class Queues:
    AUTH_VALIDATE_TOKEN_RPC = "auth.validate.rpc"
    AUTH_ISSUE_TOKEN_RPC = "auth.issue.rpc"

# RPC-запросы (auth сейчас только RPC)
RPC_DTO_MAP: Dict[str, Type[BaseModel]] = {
    "rpc.auth.issue_token":    IssueTokenRequest,
    "rpc.auth.validate_token": ValidateTokenRequest,
}

# Команд нет — вынесем в другие сервисы позже
# COMMAND_DTO_MAP: Dict[str, Type[BaseModel]] = {}
