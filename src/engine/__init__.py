"""검증 엔진 패키지.

검증기(validators)는 오류 검출에, 엔진(ValidationEngine)은 ErrorRecord 조립과
집계(ValidationResult)에 집중한다.
"""

from .result import ValidationResult
from .validation_engine import ProgressCallback, ValidationEngine

__all__ = [
    "ValidationEngine",
    "ValidationResult",
    "ProgressCallback",
]
