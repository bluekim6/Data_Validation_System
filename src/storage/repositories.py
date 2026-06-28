"""저장소(Repository) 계층.

도메인 모델(RuleTemplate/ColumnMapping)과 ORM 행 사이를 변환하며, UI는 이 계층만
사용한다. 읽기 결과는 가벼운 Pydantic read-model로 반환한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import desc, select

from ..engine import ValidationResult
from ..models import ColumnMapping, RuleTemplate
from .db import Database, get_database
from .orm import MailSendRow, MappingRow, TemplateRow, ValidationRunRow, utcnow


# --------------------------------------------------------------------------- #
# 읽기 모델
# --------------------------------------------------------------------------- #
class ValidationRunInfo(BaseModel):
    id: int
    file_name: str
    sheet_name: str
    run_user: str
    template_name: str
    total_rows: int
    error_rows: int
    error_count: int
    run_at: datetime


class MailSendInfo(BaseModel):
    id: int
    run_id: int
    person: str
    email: str
    report_file_name: str
    status: str
    error_message: str
    sent_at: datetime


# --------------------------------------------------------------------------- #
# 템플릿 CRUD (PRD §5.4)
# --------------------------------------------------------------------------- #
class TemplateRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def save(self, template: RuleTemplate) -> None:
        """이름 기준 upsert(생성 또는 수정)."""
        with self.db.Session.begin() as s:
            row = s.scalar(select(TemplateRow).where(TemplateRow.name == template.name))
            if row is None:
                s.add(
                    TemplateRow(
                        name=template.name,
                        description=template.description,
                        rules_json=template.to_json(),
                    )
                )
            else:
                row.description = template.description
                row.rules_json = template.to_json()
                row.updated_at = utcnow()

    def get(self, name: str) -> Optional[RuleTemplate]:
        with self.db.Session() as s:
            row = s.scalar(select(TemplateRow).where(TemplateRow.name == name))
            return RuleTemplate.from_json(row.rules_json) if row else None

    def list_names(self) -> list[str]:
        with self.db.Session() as s:
            return list(s.scalars(select(TemplateRow.name).order_by(TemplateRow.name)))

    def copy(self, src_name: str, new_name: str) -> RuleTemplate:
        template = self.get(src_name)
        if template is None:
            raise KeyError(f"템플릿을 찾을 수 없습니다: {src_name}")
        copied = RuleTemplate(
            name=new_name, description=template.description, rules=template.rules
        )
        self.save(copied)
        return copied

    def delete(self, name: str) -> None:
        with self.db.Session.begin() as s:
            row = s.scalar(select(TemplateRow).where(TemplateRow.name == name))
            if row is not None:
                s.delete(row)

    def mark_used(self, name: str) -> None:
        with self.db.Session.begin() as s:
            row = s.scalar(select(TemplateRow).where(TemplateRow.name == name))
            if row is not None:
                row.last_used_at = utcnow()

    def get_last_used(self) -> Optional[RuleTemplate]:
        """마지막 사용 템플릿 자동 불러오기 (PRD §5.4)."""
        with self.db.Session() as s:
            row = s.scalar(
                select(TemplateRow)
                .where(TemplateRow.last_used_at.is_not(None))
                .order_by(desc(TemplateRow.last_used_at))
                .limit(1)
            )
            return RuleTemplate.from_json(row.rules_json) if row else None


# --------------------------------------------------------------------------- #
# 매핑 프리셋 (PRD §5.2)
# --------------------------------------------------------------------------- #
class MappingRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def save(self, name: str, mapping: ColumnMapping) -> None:
        with self.db.Session.begin() as s:
            row = s.scalar(select(MappingRow).where(MappingRow.name == name))
            if row is None:
                s.add(MappingRow(name=name, mapping_json=mapping.model_dump_json()))
            else:
                row.mapping_json = mapping.model_dump_json()

    def get(self, name: str) -> Optional[ColumnMapping]:
        with self.db.Session() as s:
            row = s.scalar(select(MappingRow).where(MappingRow.name == name))
            return ColumnMapping.model_validate_json(row.mapping_json) if row else None

    def list_names(self) -> list[str]:
        with self.db.Session() as s:
            return list(s.scalars(select(MappingRow.name).order_by(MappingRow.name)))

    def delete(self, name: str) -> None:
        with self.db.Session.begin() as s:
            row = s.scalar(select(MappingRow).where(MappingRow.name == name))
            if row is not None:
                s.delete(row)


# --------------------------------------------------------------------------- #
# 검증/발송 이력 (PRD §5.9, §5.10)
# --------------------------------------------------------------------------- #
class HistoryRepository:
    def __init__(self, db: Optional[Database] = None) -> None:
        self.db = db or get_database()

    def record_validation(
        self,
        *,
        file_name: str,
        sheet_name: str,
        run_user: str,
        template_name: str,
        result: ValidationResult,
    ) -> int:
        with self.db.Session.begin() as s:
            row = ValidationRunRow(
                file_name=file_name,
                sheet_name=sheet_name,
                run_user=run_user,
                template_name=template_name,
                total_rows=result.total_rows,
                error_rows=result.error_rows,
                error_count=result.error_count,
            )
            s.add(row)
            s.flush()
            return row.id

    def record_mail(
        self,
        *,
        run_id: int,
        person: str,
        email: str,
        report_file_name: str,
        status: str,
        error_message: str = "",
    ) -> None:
        with self.db.Session.begin() as s:
            s.add(
                MailSendRow(
                    run_id=run_id,
                    person=person,
                    email=email,
                    report_file_name=report_file_name,
                    status=status,
                    error_message=error_message,
                )
            )

    def list_validations(self, limit: int = 20) -> list[ValidationRunInfo]:
        with self.db.Session() as s:
            rows = s.scalars(
                select(ValidationRunRow)
                .order_by(desc(ValidationRunRow.run_at))
                .limit(limit)
            )
            return [ValidationRunInfo.model_validate(r, from_attributes=True)
                    for r in rows]

    def list_mails(self, run_id: int) -> list[MailSendInfo]:
        with self.db.Session() as s:
            rows = s.scalars(
                select(MailSendRow)
                .where(MailSendRow.run_id == run_id)
                .order_by(MailSendRow.sent_at)
            )
            return [MailSendInfo.model_validate(r, from_attributes=True) for r in rows]
