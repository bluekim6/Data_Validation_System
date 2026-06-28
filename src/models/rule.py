"""검증 규칙 모델 (PRD §5.3, §8.2).

규칙은 코드가 아닌 '데이터'다. RuleTemplate은 JSON으로 직렬화되어 저장·재사용된다
(PRD §5.4). 컬럼명은 '시스템 기준 컬럼명'을 가리킨다 — 원본 엑셀 컬럼명은 ColumnMapping
을 통해 연결된다(PRD §14.1).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from .enums import DataType


class ConditionalRule(BaseModel):
    """조건부 검증 (PRD §5.3.8).

    'when_column 값이 조건을 만족하면, 이 컬럼에 then_* 규칙을 적용한다'.
    MVP에서는 모델만 정의하고, 실제 평가는 2차 고도화에서 구현한다(PRD §12.2).
    """

    when_column: str
    operator: Literal["equals", "not_equals"] = "equals"
    when_value: str
    then_required: Optional[bool] = None
    then_allowed_list: list[str] = Field(default_factory=list)
    then_min_value: Optional[float] = None
    then_max_value: Optional[float] = None


class ColumnRule(BaseModel):
    """단일 컬럼에 적용되는 검증 규칙 묶음."""

    column: str  # 시스템 기준 컬럼명
    required: bool = False
    data_type: DataType = DataType.TEXT

    # 숫자 범위 (PRD §5.3.3)
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # 정형 목록 (PRD §5.3.4)
    allowed_list: list[str] = Field(default_factory=list)

    # 중복 검증 (PRD §5.3.7)
    duplicate_check: bool = False
    # 조합 중복: 함께 묶을 다른 컬럼들. 비어 있으면 이 컬럼 단독 중복 검사.
    duplicate_group: list[str] = Field(default_factory=list)

    # 날짜 옵션 (PRD §5.3.5)
    allow_future: bool = True
    allow_past: bool = True
    reference_date: Optional[date] = None

    # 조건부 규칙 (PRD §5.3.8) — 2차
    conditional_rules: list[ConditionalRule] = Field(default_factory=list)

    # 사용자 정의 오류 메시지 (PRD §14.3). None이면 기본 메시지 사용.
    custom_message: Optional[str] = None


class RuleTemplate(BaseModel):
    """재사용 가능한 검증 규칙 집합 (PRD §5.4)."""

    name: str
    description: str = ""
    rules: list[ColumnRule] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def get_rule(self, column: str) -> Optional[ColumnRule]:
        """기준 컬럼명으로 규칙을 찾는다. 없으면 None."""
        for rule in self.rules:
            if rule.column == column:
                return rule
        return None

    @property
    def columns(self) -> list[str]:
        """규칙이 정의된 기준 컬럼 목록."""
        return [rule.column for rule in self.rules]

    def to_json(self) -> str:
        """JSON 문자열로 직렬화 (저장용)."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "RuleTemplate":
        """JSON 문자열에서 복원."""
        return cls.model_validate_json(raw)
