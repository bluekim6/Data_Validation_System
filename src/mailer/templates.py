"""메일 제목/본문 템플릿 (PRD §5.8, 부록 C).

기본 템플릿을 제공하되 사용자가 화면에서 수정할 수 있다. 플레이스홀더는
safe_format으로 치환하며, 누락된 키가 있어도 예외 없이 원문을 유지한다.

플레이스홀더:
    {person}        담당자명
    {error_count}   오류 건수
    {data_id_list}  대상 Data ID 목록
"""

from __future__ import annotations

DEFAULT_SUBJECT = "[Data Validation Result] 유지보수 데이터 오류 수정 요청"

DEFAULT_BODY = """안녕하세요, {person}님.

업로드하신 유지보수 데이터 검증 결과, 일부 항목에서 오류가 확인되었습니다.

첨부된 오류 리포트를 확인하신 후 수정하여 재제출 부탁드립니다.

오류 건수: {error_count}건
담당 데이터 ID: {data_id_list}

주요 오류 내용은 첨부 리포트에서 확인하실 수 있습니다.

감사합니다."""


def safe_format(template: str, **context: object) -> str:
    """누락 플레이스홀더를 원문으로 남기는 안전한 치환."""
    return template.format_map(_SafeDict(context))


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"
