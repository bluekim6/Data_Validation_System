"""검증 결과 집계 모델 (PRD §5.5).

엔진이 생성한 ErrorRecord 목록과 요약 통계(전체/정상/오류 행 수, 컬럼별·담당자별
오류 건수)를 담는다.
"""

from __future__ import annotations

from collections import Counter

import pandas as pd
from pydantic import BaseModel, Field

from ..models import ErrorRecord

UNASSIGNED = "(미지정)"


class ValidationResult(BaseModel):
    """검증 실행 1회의 결과."""

    errors: list[ErrorRecord] = Field(default_factory=list)
    total_rows: int = 0

    @property
    def error_count(self) -> int:
        """총 오류 건수."""
        return len(self.errors)

    @property
    def error_rows(self) -> int:
        """오류가 1건 이상 있는 데이터 행 수 (매핑 오류 row=0 제외)."""
        return len({e.row_number for e in self.errors if e.row_number > 0})

    @property
    def valid_rows(self) -> int:
        """정상 행 수."""
        return max(self.total_rows - self.error_rows, 0)

    @property
    def errors_by_column(self) -> dict[str, int]:
        """컬럼별 오류 건수."""
        return dict(Counter(e.column_name for e in self.errors))

    @property
    def errors_by_person(self) -> dict[str, int]:
        """담당자별 오류 건수."""
        return dict(
            Counter(e.responsible_person or UNASSIGNED for e in self.errors)
        )

    @property
    def errors_by_type(self) -> dict[str, int]:
        """오류 유형별 건수."""
        return dict(Counter(e.error_type.value for e in self.errors))

    def to_dataframe(self) -> pd.DataFrame:
        """오류 상세 테이블 (화면 표시/엑셀 다운로드용)."""
        if not self.errors:
            return pd.DataFrame(
                columns=[
                    "Data ID",
                    "Row Number",
                    "Column Name",
                    "Input Value",
                    "Error Type",
                    "Error Message",
                    "Responsible Person",
                    "Responsible Email",
                ]
            )
        return pd.DataFrame([e.as_row() for e in self.errors])
