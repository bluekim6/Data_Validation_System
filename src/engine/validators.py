"""검증기 함수 모음 (PRD §5.3, §9).

각 검증기는 pandas Series(또는 frame)를 받아 '오류 여부 불리언 마스크'를 반환하는
순수 함수다. 오류 유형과 1:1로 대응하며 독립적으로 단위 테스트한다. ErrorRecord 조립은
엔진(validation_engine)이 담당하여 검증기는 검출에만 집중한다.

규칙:
- 미입력(빈값/공백/NaN) 셀은 각 검증기가 무시한다(마스크 False). 필수값 누락은
  is_missing()으로 별도 검출한다. → '빈 셀'이 타입/범위 오류로 중복 검출되지 않게 한다.
- 성능을 위해 숫자/날짜는 pandas 벡터 연산(to_numeric/to_datetime)을 사용한다(PRD §10.1).
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

import pandas as pd

# 이메일/URL 형식 정규식 (실용 수준)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
_BOOL_TRUE = {"true", "1", "yes", "y"}
_BOOL_FALSE = {"false", "0", "no", "n"}


def _is_present_scalar(value: object) -> bool:
    """단일 값이 '입력됨'인지 판정한다 (빈값/공백/NaN 제외)."""
    if value is None:
        return False
    try:
        if pd.isna(value):  # NaN, NaT
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def present_mask(series: pd.Series) -> pd.Series:
    """입력된 셀 = True 인 마스크."""
    return series.map(_is_present_scalar)


def is_missing(series: pd.Series) -> pd.Series:
    """필수값 누락 (PRD §5.3.1): 빈값/공백/NULL → True."""
    return ~present_mask(series)


def _numeric(series: pd.Series) -> pd.Series:
    """입력된 셀만 숫자로 변환, 나머지는 NaN."""
    return pd.to_numeric(series.where(present_mask(series)), errors="coerce")


def invalid_number(series: pd.Series) -> pd.Series:
    """숫자(Number/Decimal) 형식 오류 (PRD §5.3.2): 입력됐지만 숫자 변환 불가 → True."""
    present = present_mask(series)
    return present & _numeric(series).isna()


def invalid_integer(series: pd.Series) -> pd.Series:
    """정수(Integer) 형식 오류: 숫자가 아니거나 정수가 아님(소수) → True."""
    present = present_mask(series)
    num = _numeric(series)
    not_whole = num.notna() & (num != num.round())
    return present & (num.isna() | not_whole)


def out_of_range(
    series: pd.Series,
    min_value: Optional[float],
    max_value: Optional[float],
) -> pd.Series:
    """숫자 범위 오류 (PRD §5.3.3): 숫자로 해석되는 값 중 범위 밖 → True.

    숫자가 아닌 값은 타입 검증이 잡으므로 여기서는 무시한다.
    """
    num = _numeric(series)
    valid_num = num.notna()
    mask = pd.Series(False, index=series.index)
    if min_value is not None:
        mask = mask | (valid_num & (num < min_value))
    if max_value is not None:
        mask = mask | (valid_num & (num > max_value))
    return mask


def invalid_date(series: pd.Series) -> pd.Series:
    """날짜 형식 오류 (PRD §5.3.5): 입력됐지만 날짜로 해석 불가 → True."""
    present = present_mask(series)
    parsed = pd.to_datetime(series.where(present), errors="coerce")
    return present & parsed.isna()


def invalid_boolean(series: pd.Series) -> pd.Series:
    """Boolean 형식 오류: true/false/1/0/yes/no/y/n 외의 값 → True."""

    def bad(value: object) -> bool:
        if not _is_present_scalar(value):
            return False
        if isinstance(value, bool):
            return False
        token = str(value).strip().lower()
        return token not in _BOOL_TRUE and token not in _BOOL_FALSE

    return series.map(bad)


def invalid_url(series: pd.Series) -> pd.Series:
    """URL 형식 오류: http(s):// 형식이 아님 → True."""

    def bad(value: object) -> bool:
        if not _is_present_scalar(value):
            return False
        return _URL_RE.match(str(value).strip()) is None

    return series.map(bad)


def invalid_email(series: pd.Series) -> pd.Series:
    """이메일 형식 오류 (PRD §5.3.6)."""

    def bad(value: object) -> bool:
        if not _is_present_scalar(value):
            return False
        return _EMAIL_RE.match(str(value).strip()) is None

    return series.map(bad)


def not_in_list(series: pd.Series, allowed: Iterable[str]) -> pd.Series:
    """정형 목록 오류 (PRD §5.3.4): 허용 목록 외 값 → True (대소문자 구분)."""
    allowed_set = {str(a).strip() for a in allowed}

    def bad(value: object) -> bool:
        if not _is_present_scalar(value):
            return False
        return str(value).strip() not in allowed_set

    return series.map(bad)


def duplicates(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    """중복값 오류 (PRD §5.3.7): 단일 컬럼 또는 컬럼 조합 중복 → True(모든 중복 행 표시).

    모든 대상 컬럼이 입력된 행만 비교 대상으로 삼는다.
    """
    present_all = pd.Series(True, index=frame.index)
    for col in columns:
        present_all = present_all & present_mask(frame[col])

    key = frame[columns].astype(str)
    dup = key.duplicated(keep=False)
    return present_all & dup
