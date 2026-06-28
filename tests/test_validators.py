"""검증기 단위 테스트 (정상/경계/오류 케이스)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.engine import validators as v


def _mask(values: list[object]) -> pd.Series:
    return pd.Series(values, dtype=object)


def test_is_missing() -> None:
    s = _mask(["A", "", "  ", None, np.nan, 0])
    result = v.is_missing(s).tolist()
    assert result == [False, True, True, True, True, False]  # 0은 입력값으로 본다


def test_invalid_number() -> None:
    s = _mask(["12", 3.5, "ABC", "", None, "-7"])
    assert v.invalid_number(s).tolist() == [False, False, True, False, False, False]


def test_invalid_integer() -> None:
    s = _mask(["12", 12.0, "12.5", "ABC", 7])
    assert v.invalid_integer(s).tolist() == [False, False, True, True, False]


def test_out_of_range() -> None:
    s = _mask([0, 1, 60, 120, 121, "ABC", None])
    # 1~120 범위: 0과 121만 범위 밖, 비숫자/빈값은 무시
    assert v.out_of_range(s, 1, 120).tolist() == [
        True, False, False, False, True, False, False
    ]


def test_out_of_range_min_only() -> None:
    s = _mask([-1, 0, 5])
    assert v.out_of_range(s, 0, None).tolist() == [True, False, False]


def test_invalid_list_value() -> None:
    s = _mask(["High", "Medium", "Low", "Very High", "", None])
    allowed = ["High", "Medium", "Low"]
    assert v.not_in_list(s, allowed).tolist() == [
        False, False, False, True, False, False
    ]


def test_invalid_email() -> None:
    s = _mask([
        "abc@company.com",
        "abc.company.com",
        "abc@",
        "gildong.hong@company.com",
        "",
        None,
    ])
    assert v.invalid_email(s).tolist() == [False, True, True, False, False, False]


def test_invalid_date() -> None:
    s = _mask(["2026-06-27", pd.Timestamp("2026-01-01"), "not-a-date", "", None])
    assert v.invalid_date(s).tolist() == [False, False, True, False, False]


def test_invalid_boolean() -> None:
    s = _mask([True, False, "Y", "no", "1", "maybe", "", None])
    assert v.invalid_boolean(s).tolist() == [
        False, False, False, False, False, True, False, False
    ]


def test_invalid_url() -> None:
    s = _mask(["https://x.com", "http://a.b/c", "ftp://x", "x.com", "", None])
    assert v.invalid_url(s).tolist() == [False, False, True, True, False, False]


def test_duplicates_single_column() -> None:
    frame = pd.DataFrame({"Data ID": ["EQ-001", "EQ-002", "EQ-001", None, None]})
    # EQ-001 두 행만 중복, None은 비교 대상에서 제외
    assert v.duplicates(frame, ["Data ID"]).tolist() == [
        True, False, True, False, False
    ]


def test_duplicates_combo() -> None:
    frame = pd.DataFrame(
        {
            "Equipment Tag No.": ["T1", "T1", "T1"],
            "Part No.": ["P1", "P2", "P1"],
        }
    )
    # (T1,P1) 조합이 0,2행에서 중복
    assert v.duplicates(frame, ["Equipment Tag No.", "Part No."]).tolist() == [
        True, False, True
    ]
