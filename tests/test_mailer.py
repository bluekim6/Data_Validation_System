"""메일 템플릿 / SMTP 클라이언트 테스트 (PRD §5.8).

실제 네트워크 발송은 하지 않는다. dry_run 및 메시지 구성만 검증한다.
"""

from __future__ import annotations

from pathlib import Path

from src.mailer import (
    DEFAULT_BODY,
    SmtpConfig,
    build_message,
    safe_format,
    send_report,
)
from src.mailer.smtp_client import STATUS_DRYRUN, STATUS_FAILED


def test_safe_format_replaces_known_and_keeps_unknown() -> None:
    out = safe_format(DEFAULT_BODY, person="홍길동", error_count=5,
                      data_id_list="EQ-001, EQ-003")
    assert "홍길동" in out
    assert "5건" in out
    assert "EQ-001, EQ-003" in out
    # 누락 키가 있어도 예외 없이 원문 유지
    assert safe_format("{missing}") == "{missing}"


def test_build_message_with_attachment(tmp_path: Path) -> None:
    attachment = tmp_path / "report.xlsx"
    attachment.write_bytes(b"dummy-bytes")
    config = SmtpConfig(host="smtp.test", user="bot@test.com")

    msg = build_message(
        to_email="user@company.com",
        subject="제목",
        body="본문",
        config=config,
        attachment=attachment,
    )
    assert msg["To"] == "user@company.com"
    assert "bot@test.com" in msg["From"]
    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.xlsx"


def test_send_report_dry_run_does_not_connect() -> None:
    config = SmtpConfig()  # 미설정
    res = send_report(
        to_email="user@company.com", subject="s", body="b",
        config=config, attachment=None, dry_run=True,
    )
    assert res.success is True
    assert res.status == STATUS_DRYRUN


def test_send_report_fails_without_config() -> None:
    config = SmtpConfig()  # 미설정
    res = send_report(
        to_email="user@company.com", subject="s", body="b",
        config=config, attachment=None, dry_run=False,
    )
    assert res.success is False
    assert res.status == STATUS_FAILED


def test_smtp_config_is_configured() -> None:
    assert not SmtpConfig().is_configured
    assert SmtpConfig(host="smtp.test", user="a@b.com").is_configured
