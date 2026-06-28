"""검증 엔진 (PRD §5.5).

매핑(ColumnMapping) + 규칙 템플릿(RuleTemplate) + 데이터(DataFrame)를 받아
ErrorRecord 목록과 집계를 담은 ValidationResult를 생성한다.

핵심 동작:
- 원본 컬럼을 시스템 기준 컬럼으로 변환(매핑)한 뒤, 기준 컬럼에 규칙을 적용한다(PRD §14.1).
- 필수 역할(Data ID/담당자/이메일) 매핑 누락은 Column Mapping Error로 분류한다(PRD §14.2).
- 빈 셀은 필수값 검증에서만 다루고, 타입/범위/목록/이메일 검증에서는 무시한다.
- 검증기는 벡터 마스크를 반환하고, 엔진이 마스크 → ErrorRecord로 변환한다.
"""

from __future__ import annotations

from typing import Callable, Optional

import pandas as pd

from ..models import (
    ColumnMapping,
    ColumnRule,
    DataType,
    ErrorRecord,
    ErrorType,
    RuleTemplate,
    resolve_message,
)
from . import validators as v
from .result import ValidationResult

# 진행률 콜백: (완료비율 0.0~1.0, 메시지)
ProgressCallback = Callable[[float, str], None]

# 숫자 계열 타입
_NUMERIC_TYPES = {DataType.NUMBER, DataType.INTEGER, DataType.DECIMAL}


class ValidationEngine:
    """규칙 템플릿과 컬럼 매핑을 적용해 데이터를 검증한다."""

    def __init__(self, template: RuleTemplate, mapping: ColumnMapping) -> None:
        self.template = template
        self.mapping = mapping

    def validate(
        self,
        df: pd.DataFrame,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> ValidationResult:
        work = self._to_canonical_frame(df)
        total_rows = len(work)
        errors: list[ErrorRecord] = []

        # 1) 필수 역할 매핑 누락 (PRD §14.2)
        for role in self.mapping.missing_required_roles():
            errors.append(
                ErrorRecord(
                    row_number=0,
                    column_name=role.value,
                    error_type=ErrorType.COLUMN_MAPPING_ERROR,
                    error_message=resolve_message(
                        ErrorType.COLUMN_MAPPING_ERROR, column=role.value
                    ),
                )
            )

        # 행 메타데이터 (엑셀 행번호: 헤더=1, 첫 데이터=2)
        row_numbers = [i + 2 for i in range(total_rows)]
        data_id = self._role_series(work, self.mapping.data_id_column)
        person = self._role_series(work, self.mapping.responsible_person_column)
        email = self._role_series(work, self.mapping.responsible_email_column)

        # 2) 규칙별 검증 (기준 컬럼이 실제 매핑된 것만)
        rules = [r for r in self.template.rules if r.column in work.columns]
        for idx, rule in enumerate(rules):
            errors.extend(
                self._validate_rule(rule, work, row_numbers, data_id, person, email)
            )
            if progress_callback is not None:
                progress_callback((idx + 1) / len(rules), f"검증 중: {rule.column}")

        if progress_callback is not None and not rules:
            progress_callback(1.0, "검증할 규칙이 없습니다.")

        return ValidationResult(errors=errors, total_rows=total_rows)

    # ------------------------------------------------------------------ #
    # 내부 헬퍼
    # ------------------------------------------------------------------ #

    def _to_canonical_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        """원본 컬럼을 시스템 기준 컬럼으로 변환한 프레임을 만든다.

        매핑에 있고 원본 df에도 존재하는 컬럼만 가져온다. 인덱스는 0..n-1로 재설정.
        """
        data: dict[str, pd.Series] = {}
        for source, canonical in self.mapping.column_map.items():
            if source in df.columns:
                data[canonical] = df[source].reset_index(drop=True)
        if not data:
            return pd.DataFrame(index=range(len(df)))
        return pd.DataFrame(data)

    @staticmethod
    def _role_series(work: pd.DataFrame, column: Optional[str]) -> Optional[pd.Series]:
        if column and column in work.columns:
            return work[column]
        return None

    def _validate_rule(
        self,
        rule: ColumnRule,
        work: pd.DataFrame,
        row_numbers: list[int],
        data_id: Optional[pd.Series],
        person: Optional[pd.Series],
        email: Optional[pd.Series],
    ) -> list[ErrorRecord]:
        series = work[rule.column]
        out: list[ErrorRecord] = []

        def emit(mask: pd.Series, error_type: ErrorType, **ctx: object) -> None:
            out.extend(
                self._records_from_mask(
                    mask, series, rule, error_type, row_numbers,
                    data_id, person, email, **ctx,
                )
            )

        # 필수값 (PRD §5.3.1)
        if rule.required:
            emit(v.is_missing(series), ErrorType.MISSING_REQUIRED)

        # 데이터 타입 (PRD §5.3.2, §5.3.5, §5.3.6)
        dt = rule.data_type
        if dt in {DataType.NUMBER, DataType.DECIMAL}:
            emit(v.invalid_number(series), ErrorType.INVALID_DATA_TYPE,
                 data_type=dt.value)
        elif dt == DataType.INTEGER:
            emit(v.invalid_integer(series), ErrorType.INVALID_DATA_TYPE,
                 data_type=dt.value)
        elif dt == DataType.DATE:
            emit(v.invalid_date(series), ErrorType.INVALID_DATE_FORMAT)
        elif dt == DataType.EMAIL:
            emit(v.invalid_email(series), ErrorType.INVALID_EMAIL_FORMAT)
        elif dt == DataType.BOOLEAN:
            emit(v.invalid_boolean(series), ErrorType.INVALID_DATA_TYPE,
                 data_type=dt.value)
        elif dt == DataType.URL:
            emit(v.invalid_url(series), ErrorType.INVALID_DATA_TYPE,
                 data_type=dt.value)

        # 숫자 범위 (PRD §5.3.3)
        if dt in _NUMERIC_TYPES and (
            rule.min_value is not None or rule.max_value is not None
        ):
            emit(
                v.out_of_range(series, rule.min_value, rule.max_value),
                ErrorType.OUT_OF_RANGE,
                min=_fmt_num(rule.min_value),
                max=_fmt_num(rule.max_value),
            )

        # 정형 목록 (PRD §5.3.4)
        if rule.allowed_list:
            emit(
                v.not_in_list(series, rule.allowed_list),
                ErrorType.INVALID_LIST_VALUE,
                allowed=", ".join(rule.allowed_list),
            )

        # 중복 (PRD §5.3.7) — 단일 컬럼 또는 조합
        if rule.duplicate_check:
            cols = rule.duplicate_group or [rule.column]
            if all(c in work.columns for c in cols):
                emit(v.duplicates(work, cols), ErrorType.DUPLICATE_VALUE)

        return out

    def _records_from_mask(
        self,
        mask: pd.Series,
        series: pd.Series,
        rule: ColumnRule,
        error_type: ErrorType,
        row_numbers: list[int],
        data_id: Optional[pd.Series],
        person: Optional[pd.Series],
        email: Optional[pd.Series],
        **ctx: object,
    ) -> list[ErrorRecord]:
        records: list[ErrorRecord] = []
        # mask가 True인 위치만 순회
        positions = [i for i, flag in enumerate(mask.tolist()) if bool(flag)]
        for i in positions:
            value = series.iat[i]
            input_value = _to_str(value)
            message = resolve_message(
                error_type,
                custom_message=rule.custom_message,
                column=rule.column,
                value=input_value,
                **ctx,
            )
            records.append(
                ErrorRecord(
                    data_id=_to_str(data_id.iat[i]) if data_id is not None else None,
                    row_number=row_numbers[i],
                    column_name=rule.column,
                    input_value=input_value,
                    error_type=error_type,
                    error_message=message,
                    responsible_person=(
                        _to_str(person.iat[i]) if person is not None else None
                    ),
                    responsible_email=(
                        _to_str(email.iat[i]) if email is not None else None
                    ),
                )
            )
        return records


def _to_str(value: object) -> Optional[str]:
    """표시용 문자열. 미입력은 None."""
    if not v._is_present_scalar(value):
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _fmt_num(value: Optional[float]) -> str:
    """범위 메시지용 숫자 포맷. None이면 '제한 없음'."""
    if value is None:
        return "제한 없음"
    f = float(value)
    return str(int(f)) if f.is_integer() else str(f)
