"""Streamlit 세션 상태 관리.

단계형 워크플로우(PRD §7)의 단계 간 데이터를 session_state로 전달한다.
업로드 파일은 임시 경로에 저장하여 ExcelReader(경로 기반)로 읽는다 — 원본은 변경하지
않는다(PRD §14.4).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

# 워크플로우 단계 (PRD §7)
STEPS: list[str] = [
    "1. 업로드",
    "2. 컬럼 매핑",
    "3. 검증 규칙",
    "4. 검증 결과",
    "5. 리포트·메일",
]

# session_state 기본값
_DEFAULTS: dict[str, object] = {
    "step": 0,
    "upload_path": None,
    "file_name": None,
    "sheet_names": [],
    "selected_sheet": None,
    "df": None,            # 읽어들인 DataFrame
    "mapping": None,       # ColumnMapping
    "template": None,      # RuleTemplate
    "result": None,        # ValidationResult
    "run_id": None,        # 검증 이력 ID (메일 이력 연결용)
    "reports": None,       # list[(OwnerReport, Path)]
    "send_results": None,  # list[SendResult]
}


def init_state() -> None:
    for key, value in _DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def goto(step: int) -> None:
    st.session_state.step = step


def reset() -> None:
    """처음부터 다시 시작."""
    for key, value in _DEFAULTS.items():
        st.session_state[key] = value


def save_upload(uploaded_file) -> Path:
    """업로드된 파일을 임시 경로에 저장하고 경로를 반환한다."""
    suffix = Path(uploaded_file.name).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded_file.getvalue())
    tmp.flush()
    tmp.close()
    return Path(tmp.name)
