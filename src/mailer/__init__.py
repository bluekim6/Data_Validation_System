"""메일 발송 패키지 (PRD §5.8).

config(설정) / templates(제목·본문) / smtp_client(발송)로 구성된다.
"""

from .config import SmtpConfig, load_smtp_config
from .smtp_client import (
    STATUS_DRYRUN,
    STATUS_FAILED,
    STATUS_SENT,
    SendResult,
    build_message,
    send_report,
)
from .templates import DEFAULT_BODY, DEFAULT_SUBJECT, safe_format

__all__ = [
    "SmtpConfig",
    "load_smtp_config",
    "SendResult",
    "build_message",
    "send_report",
    "STATUS_SENT",
    "STATUS_FAILED",
    "STATUS_DRYRUN",
    "DEFAULT_SUBJECT",
    "DEFAULT_BODY",
    "safe_format",
]
