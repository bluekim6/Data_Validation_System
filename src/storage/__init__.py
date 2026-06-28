"""영속화 패키지: SQLite 기반 템플릿/매핑 CRUD + 검증·발송 이력 (PRD §5.4, §5.9, §5.10)."""

from .db import Database, get_database
from .repositories import (
    HistoryRepository,
    MailSendInfo,
    MappingRepository,
    TemplateRepository,
    ValidationRunInfo,
)

__all__ = [
    "Database",
    "get_database",
    "TemplateRepository",
    "MappingRepository",
    "HistoryRepository",
    "ValidationRunInfo",
    "MailSendInfo",
]
