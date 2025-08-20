# libs/domain/orm/schema_mixin.py
import os
class InAuthSchema:
    __table_args__ = {"schema": os.getenv("DB_SCHEMA", "")}
