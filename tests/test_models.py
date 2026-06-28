"""도메인 모델 단위 테스트 (1단계 완료 기준).

- RuleTemplate JSON 직렬화/복원 왕복
- ColumnMapping 필수 역할 누락 검출 (PRD §14.2)
- resolve_message 기본/사용자 정의 메시지
"""

from __future__ import annotations

from src.models import (
    ColumnMapping,
    ColumnRule,
    DataType,
    ErrorRecord,
    ErrorType,
    MappingRole,
    RuleTemplate,
    resolve_message,
)


def test_rule_template_json_roundtrip() -> None:
    template = RuleTemplate(
        name="Spare Part Master Validation Rule",
        description="부록 A 예시",
        rules=[
            ColumnRule(column="Data ID", required=True, data_type=DataType.TEXT,
                       duplicate_check=True),
            ColumnRule(column="Maintenance Cycle", data_type=DataType.NUMBER,
                       min_value=1, max_value=120),
            ColumnRule(column="Criticality", required=True, data_type=DataType.CODE_LIST,
                       allowed_list=["High", "Medium", "Low"]),
            ColumnRule(column="Responsible Email", required=True,
                       data_type=DataType.EMAIL),
        ],
    )

    raw = template.to_json()
    restored = RuleTemplate.from_json(raw)

    assert restored == template
    assert restored.get_rule("Maintenance Cycle").max_value == 120
    assert restored.columns == [
        "Data ID",
        "Maintenance Cycle",
        "Criticality",
        "Responsible Email",
    ]


def test_rule_template_get_rule_missing() -> None:
    template = RuleTemplate(name="empty")
    assert template.get_rule("Nonexistent") is None


def test_mapping_source_lookup() -> None:
    mapping = ColumnMapping(
        column_map={"설비태그": "Equipment Tag No.", "담당자": "Responsible Person"},
    )
    assert mapping.source_for("Equipment Tag No.") == "설비태그"
    assert mapping.source_for("Unmapped") is None
    assert "Equipment Tag No." in mapping.canonical_columns


def test_mapping_missing_required_roles() -> None:
    # 역할 미지정 → 3개 모두 누락
    mapping = ColumnMapping(column_map={"ID": "Data ID"})
    assert set(mapping.missing_required_roles()) == {
        MappingRole.DATA_ID,
        MappingRole.RESPONSIBLE_PERSON,
        MappingRole.RESPONSIBLE_EMAIL,
    }


def test_mapping_all_roles_present() -> None:
    mapping = ColumnMapping(
        column_map={
            "ID": "Data ID",
            "이름": "Responsible Person",
            "메일": "Responsible Email",
        },
        data_id_column="Data ID",
        responsible_person_column="Responsible Person",
        responsible_email_column="Responsible Email",
    )
    assert mapping.missing_required_roles() == []


def test_mapping_role_set_but_not_mapped() -> None:
    # 역할로 지정했지만 실제 column_map에는 없는 경우도 누락으로 본다.
    mapping = ColumnMapping(
        column_map={"ID": "Data ID"},
        data_id_column="Data ID",
        responsible_person_column="Responsible Person",  # 매핑에 없음
        responsible_email_column="Responsible Email",  # 매핑에 없음
    )
    missing = mapping.missing_required_roles()
    assert MappingRole.DATA_ID not in missing
    assert MappingRole.RESPONSIBLE_PERSON in missing
    assert MappingRole.RESPONSIBLE_EMAIL in missing


def test_resolve_message_default() -> None:
    msg = resolve_message(ErrorType.OUT_OF_RANGE, column="Maintenance Cycle",
                          min=1, max=120)
    assert msg == "Maintenance Cycle은(는) 1~120 사이의 값이어야 합니다."


def test_resolve_message_custom_overrides_default() -> None:
    msg = resolve_message(
        ErrorType.OUT_OF_RANGE,
        custom_message="Maintenance Cycle은 1개월 이상 120개월 이하로 입력해 주세요.",
        column="Maintenance Cycle",
    )
    assert "1개월 이상 120개월 이하" in msg


def test_resolve_message_missing_placeholder_is_safe() -> None:
    # context에 없는 플레이스홀더가 있어도 예외 없이 원문 유지
    msg = resolve_message(ErrorType.INVALID_DATA_TYPE, column="X")
    assert "{data_type}" in msg


def test_error_record_as_row_order() -> None:
    rec = ErrorRecord(
        data_id="EQ-001",
        row_number=15,
        column_name="Maintenance Cycle",
        input_value="ABC",
        error_type=ErrorType.INVALID_DATA_TYPE,
        error_message="숫자 형식으로 입력해 주세요.",
        responsible_person="홍길동",
        responsible_email="gildong.hong@company.com",
    )
    row = rec.as_row()
    assert list(row.keys()) == [
        "Data ID",
        "Row Number",
        "Column Name",
        "Input Value",
        "Error Type",
        "Error Message",
        "Responsible Person",
        "Responsible Email",
    ]
    assert row["Error Type"] == "Invalid Data Type"
