"""오류 유형별 기본 메시지 (PRD §5.6, §14.3).

메시지는 '데이터'로 취급한다. 시스템 기본 메시지를 제공하되, ColumnRule.custom_message
로 컬럼별 재정의가 가능하다. 실제 메시지 조립(컨텍스트 치환)은 검증 엔진(2단계)에서
resolve_message()를 통해 수행한다.

플레이스홀더:
    {column}      대상 컬럼명
    {data_type}   데이터 타입
    {min} {max}   숫자 범위
    {allowed}     허용 목록(콤마 구분)
    {value}       입력값
"""

from __future__ import annotations

from .enums import ErrorType

DEFAULT_MESSAGES: dict[ErrorType, str] = {
    ErrorType.MISSING_REQUIRED: "{column}은(는) 필수 입력 항목입니다.",
    ErrorType.INVALID_DATA_TYPE: "{column}은(는) {data_type} 형식이어야 합니다.",
    ErrorType.OUT_OF_RANGE: "{column}은(는) {min}~{max} 사이의 값이어야 합니다.",
    ErrorType.INVALID_LIST_VALUE: "{column}은(는) {allowed} 중 하나여야 합니다.",
    ErrorType.INVALID_DATE_FORMAT: "{column}의 날짜 형식이 올바르지 않습니다.",
    ErrorType.INVALID_EMAIL_FORMAT: "{column} 형식이 올바르지 않습니다.",
    ErrorType.DUPLICATE_VALUE: "동일한 {column} 값이 중복 입력되었습니다.",
    ErrorType.CONDITIONAL_RULE_ERROR: "{column}의 조건부 규칙을 위반했습니다.",
    ErrorType.COLUMN_MAPPING_ERROR: "{column} 기준 컬럼이 매핑되지 않았습니다.",
}


def resolve_message(
    error_type: ErrorType,
    *,
    custom_message: str | None = None,
    **context: object,
) -> str:
    """오류 메시지를 조립한다.

    custom_message가 있으면 우선 사용하고, 없으면 기본 메시지를 사용한다.
    어느 쪽이든 동일한 context로 플레이스홀더를 치환한다. 누락된 플레이스홀더가
    있어도 예외 없이 원문을 유지한다(format_map + 안전 dict).
    """
    template = custom_message or DEFAULT_MESSAGES[error_type]
    return template.format_map(_SafeDict(context))


class _SafeDict(dict):
    """format_map에서 누락 키를 '{key}' 원문으로 남겨 KeyError를 방지한다."""

    def __missing__(self, key: str) -> str:  # noqa: D401
        return "{" + key + "}"
