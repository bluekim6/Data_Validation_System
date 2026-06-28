"""SMTP 설정 로딩 (.env 기반).

자격증명은 코드/저장소에 두지 않고 환경변수(.env)로 관리한다. .env.example 참조.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel


class SmtpConfig(BaseModel):
    host: str = ""
    port: int = 587
    user: str = ""
    password: str = ""
    use_tls: bool = True
    from_name: str = "Data Validation System"

    @property
    def from_address(self) -> str:
        return self.user

    @property
    def is_configured(self) -> bool:
        """실제 발송에 필요한 최소 정보가 채워졌는지."""
        return bool(self.host and self.user)


def load_smtp_config() -> SmtpConfig:
    """환경변수에서 SMTP 설정을 읽는다."""
    load_dotenv()
    return SmtpConfig(
        host=os.getenv("SMTP_HOST", ""),
        port=int(os.getenv("SMTP_PORT", "587")),
        user=os.getenv("SMTP_USER", ""),
        password=os.getenv("SMTP_PASSWORD", ""),
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"},
        from_name=os.getenv("SMTP_FROM_NAME", "Data Validation System"),
    )
