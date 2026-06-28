"""Streamlit 앱 진입점.

단계형 워크플로우(PRD §7)를 사이드바 스테퍼로 안내하고, 현재 단계 화면을 렌더링한다.
실행: 프로젝트 루트에서 `streamlit run app.py`
"""

from __future__ import annotations

import streamlit as st

from .storage import HistoryRepository
from .ui import mail, mapping, results, rules, state, upload

_PAGES = [upload.render, mapping.render, rules.render, results.render, mail.render]


def main() -> None:
    st.set_page_config(
        page_title="Maintenance Data Validation",
        page_icon="✅",
        layout="wide",
    )
    state.init_state()
    _render_sidebar()
    _PAGES[st.session_state.step]()


def _render_sidebar() -> None:
    with st.sidebar:
        st.title("Data Validation")
        st.caption("유지보수 데이터 검증 & 오류 리포트")
        st.divider()
        current = st.session_state.step
        for i, label in enumerate(state.STEPS):
            marker = "▶" if i == current else ("✓" if i < current else "○")
            st.write(f"{marker} {label}")
        st.divider()
        if st.session_state.file_name:
            st.caption(f"📄 {st.session_state.file_name}")
        if st.button("처음부터 다시"):
            state.reset()
            st.rerun()

        _render_recent_history()


def _render_recent_history() -> None:
    """최근 검증 이력 (PRD §6.1)."""
    st.divider()
    st.subheader("최근 검증 이력")
    try:
        runs = HistoryRepository().list_validations(limit=5)
    except Exception:  # DB 미준비 등은 조용히 무시
        return
    if not runs:
        st.caption("이력이 없습니다.")
        return
    for run in runs:
        st.caption(
            f"• {run.run_at:%Y-%m-%d %H:%M} · {run.file_name} · "
            f"오류 {run.error_count}건"
        )


if __name__ == "__main__":
    main()
