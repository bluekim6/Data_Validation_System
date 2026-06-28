"""검증 결과(오류) 레코드 모델 (PRD §5.5, §8.3).

검증 엔진(2단계)이 생성하는 단위 결과물. 담당자별 리포트(4단계)는 이 레코드를
Responsible Person/Email 기준으로 그룹화하여 만든다.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from .enums import ErrorType


class ErrorRecord(BaseModel):
    """개별 셀/행에서 검출된 하나의 오류."""

    data_id: Optional[str] = None
    row_number: int  # 엑셀 기준 행 번호 (헤더=1, 첫 데이터=2)
    column_name: str  # 시스템 기준 컬럼명
    input_value: Optional[str] = None
    error_type: ErrorType
    error_message: str
    responsible_person: Optional[str] = None
    responsible_email: Optional[str] = None

    def as_row(self) -> dict[str, object]:
        """리포트/엑셀 출력용 평면 딕셔너리 (PRD §5.5 결과 항목 순서)."""
        return {
            "Data ID": self.data_id,
            "Row Number": self.row_number,
            "Column Name": self.column_name,
            "Input Value": self.input_value,
            "Error Type": self.error_type.value,
            "Error Message": self.error_message,
            "Responsible Person": self.responsible_person,
            "Responsible Email": self.responsible_email,
        }
