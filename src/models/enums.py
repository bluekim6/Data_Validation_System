"""핵심 열거형: 오류 유형 / 데이터 타입 / 매핑 역할.

오류 유형은 PRD §9, 데이터 타입은 PRD §5.3.2 정의를 그대로 따른다.
문자열 값은 화면 표시 및 리포트에 그대로 사용되므로 변경 시 주의한다.
"""

from __future__ import annotations

from enum import Enum


class ErrorType(str, Enum):
    """검증 오류 유형 (PRD §9)."""

    MISSING_REQUIRED = "Missing Required Value"
    INVALID_DATA_TYPE = "Invalid Data Type"
    OUT_OF_RANGE = "Out of Range"
    INVALID_LIST_VALUE = "Invalid List Value"
    INVALID_DATE_FORMAT = "Invalid Date Format"
    INVALID_EMAIL_FORMAT = "Invalid Email Format"
    DUPLICATE_VALUE = "Duplicate Value"
    CONDITIONAL_RULE_ERROR = "Conditional Rule Error"
    COLUMN_MAPPING_ERROR = "Column Mapping Error"


class DataType(str, Enum):
    """컬럼 데이터 타입 (PRD §5.3.2)."""

    TEXT = "Text"
    NUMBER = "Number"
    INTEGER = "Integer"
    DECIMAL = "Decimal"
    DATE = "Date"
    EMAIL = "Email"
    BOOLEAN = "Boolean"
    CODE_LIST = "Code/List"
    URL = "URL"


class MappingRole(str, Enum):
    """담당자별 리포트 생성을 위해 반드시 지정되어야 하는 기준 컬럼 (PRD §14.2)."""

    DATA_ID = "Data ID"
    RESPONSIBLE_PERSON = "Responsible Person"
    RESPONSIBLE_EMAIL = "Responsible Email"
