"""데이터 리더 추상화 + 공통 예외.

엑셀 외 포맷(CSV 등) 확장을 위해 리더를 인터페이스로 분리한다(PRD §10.4).
패키지명은 stdlib `io`와의 혼동을 피하기 위해 `dataio`로 둔다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class DataReadError(Exception):
    """업로드 파일 읽기 실패의 기반 예외."""


class InvalidFileFormatError(DataReadError):
    """지원하지 않는 형식이거나 파일이 손상된 경우 (PRD §5.1)."""


class NoColumnsError(DataReadError):
    """컬럼명(헤더) 행을 인식할 수 없는 경우 (PRD §5.1)."""


class NoDataError(DataReadError):
    """데이터 행이 하나도 없는 경우 (PRD §5.1)."""


class DataReader(ABC):
    """표 형태 데이터 소스 리더 인터페이스."""

    @abstractmethod
    def sheet_names(self) -> list[str]:
        """시트(또는 그에 준하는 단위) 목록."""

    @abstractmethod
    def read_sheet(self, sheet_name: str | None = None) -> pd.DataFrame:
        """지정 시트를 첫 행=헤더로 읽어 DataFrame으로 반환."""

    @abstractmethod
    def preview(self, sheet_name: str | None = None, n: int = 20) -> pd.DataFrame:
        """미리보기용 상위 n행."""
