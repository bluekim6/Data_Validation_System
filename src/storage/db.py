"""데이터베이스 연결 관리.

SQLite를 기본으로 하며, 향후 RDB 전환 시 URL만 교체하면 되도록 ORM/세션을 캡슐화한다.
DB 경로는 환경변수 DB_PATH(기본 data/validation.db)에서 읽는다.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .orm import Base


class Database:
    """엔진 + 세션 팩토리를 보유하고 스키마를 생성한다."""

    def __init__(self, url: str) -> None:
        self.engine = create_engine(url, future=True)
        self.Session: sessionmaker[Session] = sessionmaker(
            bind=self.engine, expire_on_commit=False, future=True
        )
        Base.metadata.create_all(self.engine)


def default_url() -> str:
    load_dotenv()
    path = Path(os.getenv("DB_PATH", "data/validation.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.resolve()}"


_default: Database | None = None


def get_database() -> Database:
    """기본 DB 싱글톤."""
    global _default
    if _default is None:
        _default = Database(default_url())
    return _default
