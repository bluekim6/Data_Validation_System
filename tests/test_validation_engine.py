"""검증 엔진 통합 테스트.

PRD 부록 A(대표 검증 규칙) + 샘플 데이터로 부록 B의 오류가 정확히 재현되는지 확인한다.
이것이 2단계 완료 기준이다.
"""

from __future__ import annotations

import pandas as pd

from src.engine import ValidationEngine
from src.models import (
    ColumnMapping,
    ColumnRule,
    DataType,
    ErrorType,
    MappingRole,
    RuleTemplate,
)


def _appendix_a_template() -> RuleTemplate:
    """PRD 부록 A 대표 검증 규칙."""
    return RuleTemplate(
        name="Spare Part Master Validation Rule",
        rules=[
            ColumnRule(column="Data ID", required=True, data_type=DataType.TEXT,
                       duplicate_check=True),
            ColumnRule(column="Equipment Tag No.", required=True,
                       data_type=DataType.TEXT),
            ColumnRule(column="Part No.", required=True, data_type=DataType.TEXT),
            ColumnRule(column="Maintenance Type", required=True,
                       data_type=DataType.CODE_LIST,
                       allowed_list=["Preventive", "Corrective", "Predictive"]),
            ColumnRule(column="Maintenance Cycle", data_type=DataType.NUMBER,
                       min_value=1, max_value=120),
            ColumnRule(column="Criticality", required=True,
                       data_type=DataType.CODE_LIST,
                       allowed_list=["High", "Medium", "Low"]),
            ColumnRule(column="Inspection Date", data_type=DataType.DATE),
            ColumnRule(column="Responsible Person", required=True,
                       data_type=DataType.TEXT),
            ColumnRule(column="Responsible Email", required=True,
                       data_type=DataType.EMAIL),
        ],
    )


def _full_mapping() -> ColumnMapping:
    """원본 컬럼명이 기준 컬럼명과 동일한 단순 매핑."""
    cols = [
        "Data ID", "Equipment Tag No.", "Part No.", "Maintenance Type",
        "Maintenance Cycle", "Criticality", "Inspection Date",
        "Responsible Person", "Responsible Email",
    ]
    return ColumnMapping(
        column_map={c: c for c in cols},
        data_id_column="Data ID",
        responsible_person_column="Responsible Person",
        responsible_email_column="Responsible Email",
    )


def _appendix_b_data() -> pd.DataFrame:
    """부록 B 오류를 담은 데이터. 0번 행은 정상, 이후 각 행에 오류 1건."""
    base = {
        "Data ID": "EQ-000",
        "Equipment Tag No.": "TAG",
        "Part No.": "P1",
        "Maintenance Type": "Preventive",
        "Maintenance Cycle": 12,
        "Criticality": "High",
        "Inspection Date": "2026-01-01",
        "Responsible Person": "정상담당",
        "Responsible Email": "ok@company.com",
    }
    rows = [dict(base)]  # row 2: 정상

    r1 = dict(base); r1["Data ID"] = "EQ-001"; r1["Maintenance Cycle"] = "ABC"
    r1["Responsible Person"] = "홍길동"; r1["Responsible Email"] = "gildong.hong@company.com"
    rows.append(r1)  # row 3: Invalid Data Type

    r2 = dict(base); r2["Data ID"] = "EQ-002"; r2["Criticality"] = "Very High"
    rows.append(r2)  # row 4: Invalid List Value

    r3 = dict(base); r3["Data ID"] = "EQ-003"
    r3["Responsible Email"] = "gildong.company.com"
    rows.append(r3)  # row 5: Invalid Email Format

    return pd.DataFrame(rows)


def test_reproduces_appendix_b_error_types() -> None:
    engine = ValidationEngine(_appendix_a_template(), _full_mapping())
    result = engine.validate(_appendix_b_data())

    by_id = {(e.data_id, e.error_type) for e in result.errors}
    assert ("EQ-001", ErrorType.INVALID_DATA_TYPE) in by_id
    assert ("EQ-002", ErrorType.INVALID_LIST_VALUE) in by_id
    assert ("EQ-003", ErrorType.INVALID_EMAIL_FORMAT) in by_id

    # 정상 행(EQ-000)은 오류가 없어야 한다
    assert not any(e.data_id == "EQ-000" for e in result.errors)


def test_error_record_details() -> None:
    engine = ValidationEngine(_appendix_a_template(), _full_mapping())
    result = engine.validate(_appendix_b_data())

    type_err = next(e for e in result.errors if e.data_id == "EQ-001")
    assert type_err.column_name == "Maintenance Cycle"
    assert type_err.input_value == "ABC"
    assert type_err.row_number == 3  # 헤더=1, 첫 데이터=2, EQ-001은 3번째 행
    assert type_err.responsible_person == "홍길동"
    assert type_err.responsible_email == "gildong.hong@company.com"
    assert "숫자" in type_err.error_message or "Number" in type_err.error_message


def test_aggregations() -> None:
    engine = ValidationEngine(_appendix_a_template(), _full_mapping())
    result = engine.validate(_appendix_b_data())

    assert result.total_rows == 4
    assert result.error_rows == 3  # EQ-001/002/003
    assert result.valid_rows == 1  # EQ-000
    assert result.errors_by_type[ErrorType.INVALID_LIST_VALUE.value] == 1
    assert "홍길동" in result.errors_by_person


def test_missing_required_value() -> None:
    template = RuleTemplate(name="t", rules=[
        ColumnRule(column="Equipment Tag No.", required=True, data_type=DataType.TEXT),
    ])
    mapping = ColumnMapping(
        column_map={"Equipment Tag No.": "Equipment Tag No."},
    )
    df = pd.DataFrame({"Equipment Tag No.": ["TAG-1", "", None]})
    result = ValidationEngine(template, mapping).validate(df)

    missing = [e for e in result.errors
               if e.error_type == ErrorType.MISSING_REQUIRED]
    assert len(missing) == 2
    assert {e.row_number for e in missing} == {3, 4}


def test_duplicate_detection() -> None:
    template = RuleTemplate(name="t", rules=[
        ColumnRule(column="Data ID", required=True, data_type=DataType.TEXT,
                   duplicate_check=True),
    ])
    mapping = ColumnMapping(
        column_map={"Data ID": "Data ID"}, data_id_column="Data ID",
    )
    df = pd.DataFrame({"Data ID": ["EQ-001", "EQ-002", "EQ-001"]})
    result = ValidationEngine(template, mapping).validate(df)

    dup = [e for e in result.errors if e.error_type == ErrorType.DUPLICATE_VALUE]
    assert len(dup) == 2  # 중복된 두 행 모두


def test_missing_role_mapping_error() -> None:
    # 담당자/이메일 역할 미지정 → Column Mapping Error
    template = RuleTemplate(name="t", rules=[
        ColumnRule(column="Data ID", required=True, data_type=DataType.TEXT),
    ])
    mapping = ColumnMapping(
        column_map={"ID": "Data ID"}, data_id_column="Data ID",
    )
    df = pd.DataFrame({"ID": ["EQ-001"]})
    result = ValidationEngine(template, mapping).validate(df)

    mapping_errors = [e for e in result.errors
                      if e.error_type == ErrorType.COLUMN_MAPPING_ERROR]
    cols = {e.column_name for e in mapping_errors}
    assert MappingRole.RESPONSIBLE_PERSON.value in cols
    assert MappingRole.RESPONSIBLE_EMAIL.value in cols
    assert MappingRole.DATA_ID.value not in cols


def test_custom_message_override() -> None:
    template = RuleTemplate(name="t", rules=[
        ColumnRule(column="Maintenance Cycle", data_type=DataType.NUMBER,
                   min_value=1, max_value=120,
                   custom_message="Maintenance Cycle은 1개월 이상 120개월 이하로 입력해 주세요."),
    ])
    mapping = ColumnMapping(
        column_map={"Maintenance Cycle": "Maintenance Cycle"},
    )
    df = pd.DataFrame({"Maintenance Cycle": [0]})
    result = ValidationEngine(template, mapping).validate(df)

    range_err = next(e for e in result.errors
                     if e.error_type == ErrorType.OUT_OF_RANGE)
    assert range_err.error_message == \
        "Maintenance Cycle은 1개월 이상 120개월 이하로 입력해 주세요."


def test_progress_callback_invoked() -> None:
    template = _appendix_a_template()
    mapping = _full_mapping()
    seen: list[float] = []
    ValidationEngine(template, mapping).validate(
        _appendix_b_data(), progress_callback=lambda frac, msg: seen.append(frac)
    )
    assert seen and seen[-1] == 1.0
