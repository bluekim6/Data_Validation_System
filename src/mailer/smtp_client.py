"""SMTP 메일 발송 (PRD §5.8).

담당자별 리포트를 첨부하여 발송한다. dry_run=True이면 메시지만 구성하고 실제 발송은
하지 않는다(SMTP 미설정 환경/미리보기 테스트용).
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from .config import SmtpConfig

_XLSX_MAINTYPE = "application"
_XLSX_SUBTYPE = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# 발송 상태 (PRD §5.9)
STATUS_SENT = "발송 완료"
STATUS_FAILED = "발송 실패"
STATUS_DRYRUN = "테스트(미발송)"


class SendResult(BaseModel):
    email: str
    success: bool
    status: str
    error: Optional[str] = None


def build_message(
    *,
    to_email: str,
    subject: str,
    body: str,
    config: SmtpConfig,
    attachment: Optional[Path] = None,
) -> EmailMessage:
    """첨부 포함 EmailMessage를 구성한다."""
    msg = EmailMessage()
    msg["Subject"] = subject
    from_addr = config.from_address or "no-reply@localhost"
    msg["From"] = f"{config.from_name} <{from_addr}>"
    msg["To"] = to_email
    msg.set_content(body)

    if attachment is not None:
        attachment = Path(attachment)
        data = attachment.read_bytes()
        msg.add_attachment(
            data,
            maintype=_XLSX_MAINTYPE,
            subtype=_XLSX_SUBTYPE,
            filename=attachment.name,
        )
    return msg


def send_report(
    *,
    to_email: str,
    subject: str,
    body: str,
    config: SmtpConfig,
    attachment: Optional[Path] = None,
    dry_run: bool = False,
) -> SendResult:
    """리포트 메일을 발송한다. 실패는 예외 없이 SendResult로 보고한다."""
    try:
        msg = build_message(
            to_email=to_email, subject=subject, body=body,
            config=config, attachment=attachment,
        )
    except Exception as exc:  # 첨부 읽기 실패 등
        return SendResult(email=to_email, success=False, status=STATUS_FAILED,
                          error=f"메시지 구성 실패: {exc}")

    if dry_run:
        return SendResult(email=to_email, success=True, status=STATUS_DRYRUN)

    if not config.is_configured:
        return SendResult(email=to_email, success=False, status=STATUS_FAILED,
                          error="SMTP 설정이 없습니다(.env 확인).")

    try:
        with smtplib.SMTP(config.host, config.port, timeout=30) as server:
            if config.use_tls:
                server.starttls()
            if config.password:
                server.login(config.user, config.password)
            server.send_message(msg)
        return SendResult(email=to_email, success=True, status=STATUS_SENT)
    except Exception as exc:
        return SendResult(email=to_email, success=False, status=STATUS_FAILED,
                          error=str(exc))
