"""테스트용 샘플 엑셀 생성기.

PRD 부록 A 규칙에 대해 의도적으로 다양한 오류를 섞은 데이터를 만든다.
실행: python scripts/generate_sample.py  →  data/sample_maintenance.xlsx
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROWS = [
    # 정상
    {"Data ID": "EQ-001", "Equipment Tag No.": "TAG-100", "Part No.": "P-1",
     "Maintenance Type": "Preventive", "Maintenance Cycle": 12,
     "Criticality": "High", "Inspection Date": "2026-01-15",
     "Responsible Person": "홍길동", "Responsible Email": "gildong.hong@company.com"},
    # 타입 오류 (Maintenance Cycle = ABC)
    {"Data ID": "EQ-002", "Equipment Tag No.": "TAG-101", "Part No.": "P-2",
     "Maintenance Type": "Corrective", "Maintenance Cycle": "ABC",
     "Criticality": "Medium", "Inspection Date": "2026-02-01",
     "Responsible Person": "김철수", "Responsible Email": "chulsoo.kim@company.com"},
    # 목록 오류 (Criticality = Very High)
    {"Data ID": "EQ-003", "Equipment Tag No.": "TAG-102", "Part No.": "P-3",
     "Maintenance Type": "Predictive", "Maintenance Cycle": 24,
     "Criticality": "Very High", "Inspection Date": "2026-03-10",
     "Responsible Person": "홍길동", "Responsible Email": "gildong.hong@company.com"},
    # 이메일 오류 + 범위 오류 (Cycle=200)
    {"Data ID": "EQ-004", "Equipment Tag No.": "TAG-103", "Part No.": "P-4",
     "Maintenance Type": "Preventive", "Maintenance Cycle": 200,
     "Criticality": "Low", "Inspection Date": "2026-04-05",
     "Responsible Person": "이영희", "Responsible Email": "younghee.company.com"},
    # 필수값 누락 (Equipment Tag No. 빈값) + 중복 Data ID
    {"Data ID": "EQ-001", "Equipment Tag No.": "", "Part No.": "P-5",
     "Maintenance Type": "PM", "Maintenance Cycle": 6,
     "Criticality": "High", "Inspection Date": "not-a-date",
     "Responsible Person": "김철수", "Responsible Email": "chulsoo.kim@company.com"},
]


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "data" / "sample_maintenance.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ROWS).to_excel(out, index=False, sheet_name="Maintenance")
    print(f"샘플 생성 완료: {out}")


if __name__ == "__main__":
    main()
