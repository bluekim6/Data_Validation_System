"""컬럼 매핑 모델 (PRD §5.2, §14.1).

원본 엑셀 컬럼명은 변경될 수 있으므로 고정하지 않고, '원본 컬럼 → 시스템 기준 컬럼'
매핑으로 관리한다. 담당자별 리포트 생성을 위해 Data ID / Responsible Person /
Responsible Email 세 기준 컬럼은 반드시 지정되어야 한다(PRD §14.2). 누락 시
Column Mapping Error로 분류한다.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .enums import MappingRole


class ColumnMapping(BaseModel):
    """원본 컬럼과 시스템 기준 컬럼 간의 매핑."""

    # 원본 엑셀 컬럼명 -> 시스템 기준 컬럼명
    column_map: dict[str, str] = Field(default_factory=dict)

    # 역할 컬럼 (값은 '시스템 기준 컬럼명')
    data_id_column: Optional[str] = None
    responsible_person_column: Optional[str] = None
    responsible_email_column: Optional[str] = None

    def source_for(self, canonical: str) -> Optional[str]:
        """기준 컬럼명에 대응하는 원본 컬럼명을 반환한다. 없으면 None."""
        for source, mapped in self.column_map.items():
            if mapped == canonical:
                return source
        return None

    @property
    def canonical_columns(self) -> list[str]:
        """매핑된 시스템 기준 컬럼 목록."""
        return list(self.column_map.values())

    def role_columns(self) -> dict[MappingRole, Optional[str]]:
        """역할별 지정된 기준 컬럼을 반환한다."""
        return {
            MappingRole.DATA_ID: self.data_id_column,
            MappingRole.RESPONSIBLE_PERSON: self.responsible_person_column,
            MappingRole.RESPONSIBLE_EMAIL: self.responsible_email_column,
        }

    def missing_required_roles(self) -> list[MappingRole]:
        """미지정되었거나, 지정됐지만 실제 매핑에 없는 필수 역할 목록 (PRD §14.2)."""
        missing: list[MappingRole] = []
        mapped = set(self.canonical_columns)
        for role, col in self.role_columns().items():
            if not col or col not in mapped:
                missing.append(role)
        return missing
