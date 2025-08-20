# libs/infra/migrate.py
from __future__ import annotations
import os
from pathlib import Path

from alembic import command
from alembic.config import Config

def upgrade_to_head() -> None:
    root = Path(__file__).resolve().parents[2]  # корень проекта (/app)
    cfg = Config(str(root / "alembic.ini"))
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)
    # DB_SCHEMA берёт env.py из os.getenv("DB_SCHEMA"), так что -x не нужен
    command.upgrade(cfg, "head")
