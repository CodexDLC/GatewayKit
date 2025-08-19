# apps/auth_svc/config/auth_service_config.py
from __future__ import annotations
from typing import Dict, Type
from pydantic import BaseModel

from apps.auth_svc.handlers.auth_issue_token_rpc_handler import IssueTokenRequest
from apps.auth_svc.handlers.auth_validate_token_rpc_handler import ValidateTokenRequest
from apps.auth_svc.handlers.auth_register_rpc_handler import RegisterRequest

class Exchanges:
    EVENTS = "EVENTS"

class Queues:
    AUTH_VALIDATE_TOKEN_RPC = "rpc.auth.validate_token"
    AUTH_ISSUE_TOKEN_RPC    = "rpc.auth.issue_token"
    AUTH_REGISTER_RPC       = "rpc.auth.register"

RPC_DTO_MAP = {
    "rpc.auth.issue_token":    IssueTokenRequest,
    "rpc.auth.validate_token": ValidateTokenRequest,
    "rpc.auth.register":       RegisterRequest,  # new
}
