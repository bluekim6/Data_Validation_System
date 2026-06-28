"""SQLAlchemy ORM 테이블 정의 (PRD §8.1~8.4).

도메인 모델(src/models)과 구분하기 위해 테이블 클래스는 *Row 접미사를 쓴다.
규칙/매핑 등 복합 구조는 JSON 컬럼으로 저장한다(규칙=데이터 원칙, PRD §14.3).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TemplateRow(Base):
    """검증 규칙 템플릿 (PRD §5.4, §8.2)."""

    __tablename__ = "rule_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    rules_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MappingRow(Base):
    """컬럼 매핑 프리셋 (PRD §5.2)."""

    __tablename__ = "column_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    mapping_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ValidationRunRow(Base):
    """검증 실행 이력 (PRD §5.10, §8.1)."""

    __tablename__ = "validation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(500))
    sheet_name: Mapped[str] = mapped_column(String(200), default="")
    run_user: Mapped[str] = mapped_column(String(200), default="")
    template_name: Mapped[str] = mapped_column(String(200), default="")
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    mails: Mapped[list["MailSendRow"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class MailSendRow(Base):
    """메일 발송 이력 (PRD §5.9, §8.4)."""

    __tablename__ = "mail_sends"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("validation_runs.id"))
    person: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(320), default="")
    report_file_name: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(50), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    run: Mapped["ValidationRunRow"] = relationship(back_populates="mails")
