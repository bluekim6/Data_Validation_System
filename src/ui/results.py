"""4단계 화면: 검증 실행 + 결과 (PRD §5.5, §5.6, §6.5)."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from ..engine import ValidationEngine
from ..storage import HistoryRepository
from . import state


def render() -> None:
    df = st.session_state.df
    template = st.session_state.template
    mapping = st.session_state.mapping
    if df is None or template is None or mapping is None:
        st.warning("먼저 이전 단계를 완료하세요.")
        return

    st.header("4. 검증 결과")

    # 결과가 없으면 검증 실행 (진행률 표시)
    if st.session_state.result is None:
        progress = st.progress(0.0, text="검증 준비 중...")

        def on_progress(frac: float, message: str) -> None:
            progress.progress(min(frac, 1.0), text=message)

        engine = ValidationEngine(template, mapping)
        st.session_state.result = engine.validate(df, progress_callback=on_progress)
        progress.empty()

        # 검증 이력 저장 (PRD §5.10)
        st.session_state.run_id = HistoryRepository().record_validation(
            file_name=st.session_state.file_name or "",
            sheet_name=st.session_state.selected_sheet or "",
            run_user="사용자",
            template_name=template.name,
            result=st.session_state.result,
        )

    result = st.session_state.result

    # 요약 (PRD §5.5)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 행", result.total_rows)
    c2.metric("정상 행", result.valid_rows)
    c3.metric("오류 행", result.error_rows)
    c4.metric("오류 건수", result.error_count)

    if result.error_count == 0:
        st.success("🎉 오류가 발견되지 않았습니다.")
        _nav()
        return

    _to_mail_button()

    # 집계 차트
    a1, a2 = st.columns(2)
    with a1:
        st.subheader("담당자별 오류")
        st.bar_chart(_counter_df(result.errors_by_person, "담당자"))
    with a2:
        st.subheader("컬럼별 오류")
        st.bar_chart(_counter_df(result.errors_by_column, "컬럼"))

    # 오류 상세 + 필터 (PRD §5.6)
    st.subheader("오류 상세")
    table = result.to_dataframe()

    f1, f2, f3, f4 = st.columns(4)
    person = f1.selectbox("담당자", _options(table, "Responsible Person"))
    column = f2.selectbox("컬럼", _options(table, "Column Name"))
    etype = f3.selectbox("오류 유형", _options(table, "Error Type"))
    keyword = f4.text_input("Data ID 검색")

    filtered = table
    if person != "(전체)":
        filtered = filtered[filtered["Responsible Person"] == person]
    if column != "(전체)":
        filtered = filtered[filtered["Column Name"] == column]
    if etype != "(전체)":
        filtered = filtered[filtered["Error Type"] == etype]
    if keyword:
        filtered = filtered[
            filtered["Data ID"].astype(str).str.contains(keyword, case=False, na=False)
        ]

    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.caption(f"{len(filtered)} / {len(table)} 건 표시 중")

    st.download_button(
        "📥 오류 목록 엑셀 다운로드",
        data=_to_excel_bytes(table),
        file_name="validation_errors.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    _nav()


def _to_mail_button() -> None:
    if st.button("리포트·메일 발송 →", type="primary"):
        st.session_state.reports = None       # 새 결과 기준으로 재생성
        st.session_state.send_results = None
        state.goto(4)
        st.rerun()


def _nav() -> None:
    n1, n2 = st.columns(2)
    with n1:
        if st.button("← 이전: 검증 규칙"):
            state.goto(2)
            st.rerun()
    with n2:
        if st.button("🔄 처음부터 다시"):
            state.reset()
            st.rerun()


def _counter_df(counter: dict[str, int], label: str) -> pd.DataFrame:
    if not counter:
        return pd.DataFrame({label: [], "오류 건수": []}).set_index(label)
    return (
        pd.DataFrame({label: list(counter.keys()), "오류 건수": list(counter.values())})
        .set_index(label)
    )


def _options(table: pd.DataFrame, column: str) -> list[str]:
    values = [str(v) for v in table[column].dropna().unique()]
    return ["(전체)"] + sorted(values)


def _to_excel_bytes(table: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        table.to_excel(writer, index=False, sheet_name="Errors")
    return buffer.getvalue()
