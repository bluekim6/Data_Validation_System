"""입출력 패키지: 업로드 파일 읽기 / 리포트 쓰기.

stdlib `io`와의 혼동을 피하기 위해 패키지명은 `dataio`로 둔다.
"""

from .base import (
    DataReader,
    DataReadError,
    InvalidFileFormatError,
    NoColumnsError,
    NoDataError,
)
from .decrypt_fasoo import decrypt_fasoo_file, enable_drm, is_drm_supported
from .excel_reader import SUPPORTED_SUFFIXES, ExcelReader

__all__ = [
    "DataReader",
    "DataReadError",
    "InvalidFileFormatError",
    "NoColumnsError",
    "NoDataError",
    "ExcelReader",
    "SUPPORTED_SUFFIXES",
    "decrypt_fasoo_file",
    "enable_drm",
    "is_drm_supported",
]
