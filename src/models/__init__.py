"""도메인 모델 패키지.

검증 규칙·매핑·오류 레코드 등 시스템 전반에서 공유하는 Pydantic 모델을 모은다.
규칙과 메시지는 '코드가 아닌 데이터'로 다룬다(PRD §14.3).
"""

from .constants import SYSTEM_COLUMNS
from .enums import DataType, ErrorType, MappingRole
from .error import ErrorRecord
from .mapping import ColumnMapping
from .messages import DEFAULT_MESSAGES, resolve_message
from .rule import ColumnRule, ConditionalRule, RuleTemplate

__all__ = [
    "SYSTEM_COLUMNS",
    "DataType",
    "ErrorType",
    "MappingRole",
    "ErrorRecord",
    "ColumnMapping",
    "DEFAULT_MESSAGES",
    "resolve_message",
    "ColumnRule",
    "ConditionalRule",
    "RuleTemplate",
]
