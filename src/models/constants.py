"""시스템 기준 컬럼 목록 (PRD §5.2).

컬럼 매핑 화면에서 원본 엑셀 컬럼을 연결할 '기준 컬럼' 후보로 사용한다.
이 목록은 제안용이며, 사용자가 임의의 기준 컬럼명을 직접 입력할 수도 있다.
"""

from __future__ import annotations

SYSTEM_COLUMNS: list[str] = [
    "Data ID",
    "Equipment Tag No.",
    "Part No.",
    "Maintenance Type",
    "Maintenance Cycle",
    "Inspection Interval",
    "Inspection Date",
    "Responsible Person",
    "Responsible Email",
    "Comment",
    "Status",
]
