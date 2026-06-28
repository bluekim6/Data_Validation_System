"""엑셀 파일 리더 (PRD §5.1).

- .xlsx / .xls 지원
- 시트 선택, 첫 행을 컬럼명으로 인식
- 미리보기 제공
- 예외: 형식 오류 / 헤더 없음 / 데이터 없음

원본 파일은 절대 변경하지 않는다(PRD §14.4) — 읽기 전용으로만 접근한다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import (
    DataReader,
    InvalidFileFormatError,
    NoColumnsError,
    NoDataError,
)
from .decrypt_fasoo import enable_drm

SUPPORTED_SUFFIXES = {".xlsx", ".xls"}


class ExcelReader(DataReader):
    """openpyxl/xlrd 백엔드를 사용하는 엑셀 리더."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise InvalidFileFormatError(f"파일을 찾을 수 없습니다: {self.path}")
        if self.path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise InvalidFileFormatError(
                f"지원하지 않는 파일 형식입니다: {self.path.suffix} "
                f"(지원: {', '.join(sorted(SUPPORTED_SUFFIXES))})"
            )
        # 파싱 전에 Fasoo DRM 투명 복호화를 활성화한다(프로세스당 1회, 캐시).
        # 운영(사내 Windows)에서 DRM 파일이 열리도록 하며, 그 외 환경/실패 시 no-op.
        enable_drm()
        try:
            # 시트 목록만 먼저 읽어 형식 유효성을 검증한다.
            self._excel = pd.ExcelFile(self.path)
        except Exception as exc:  # pandas가 던지는 다양한 예외를 일괄 변환
            raise InvalidFileFormatError(
                f"엑셀 파일을 열 수 없습니다: {self.path.name}"
            ) from exc

    def sheet_names(self) -> list[str]:
        return list(self._excel.sheet_names)

    def read_sheet(self, sheet_name: str | None = None) -> pd.DataFrame:
        """시트를 읽어 DataFrame으로 반환한다.

        - 첫 행을 헤더로 사용한다.
        - 완전히 빈 행은 제거한다.
        - 모든 값은 dtype=object로 읽어 원본 입력값을 보존한다(검증 단계에서 타입 판정).
        """
        sheet = sheet_name or self.sheet_names()[0]
        try:
            df = self._excel.parse(sheet, header=0, dtype=object)
        except Exception as exc:
            raise InvalidFileFormatError(
                f"시트를 읽을 수 없습니다: {sheet}"
            ) from exc

        if self._has_no_header(df):
            raise NoColumnsError("컬럼명(헤더)을 인식할 수 없습니다.")

        df = df.dropna(how="all")  # 전부 빈 행 제거
        if df.empty:
            raise NoDataError("데이터 행이 없습니다.")

        df = df.reset_index(drop=True)
        return df

    def preview(self, sheet_name: str | None = None, n: int = 20) -> pd.DataFrame:
        """미리보기용 상위 n행 (PRD §5.1)."""
        return self.read_sheet(sheet_name).head(n)

    @staticmethod
    def _has_no_header(df: pd.DataFrame) -> bool:
        """헤더가 비었거나 모두 자동 생성된(Unnamed) 이름인지 판정한다."""
        if df.shape[1] == 0:
            return True
        cols = [str(c) for c in df.columns]
        return all(c.startswith("Unnamed:") or c.strip() == "" for c in cols)
