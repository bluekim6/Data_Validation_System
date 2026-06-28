"""5단계 화면: 담당자별 리포트 생성 + 메일 발송 (PRD §5.7, §5.8, §6.6)."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from ..mailer import (
    DEFAULT_BODY,
    DEFAULT_SUBJECT,
    load_smtp_config,
    safe_format,
    send_report,
)
from ..reporting import generate_reports
from ..storage import HistoryRepository
from . import state

_REPORT_DIR = os.getenv("REPORT_DIR", "data/reports")


def render() -> None:
    result = st.session_state.result
    if result is None:
        st.warning("먼저 4단계에서 검증을 실행하세요.")
        return

    st.header("5. 담당자별 리포트 & 메일 발송")

    # 리포트 생성 (최초 1회)
    if st.session_state.reports is None:
        with st.spinner("담당자별 리포트 생성 중..."):
            st.session_state.reports = generate_reports(result.errors, _REPORT_DIR)

    reports = st.session_state.reports
    if not reports:
        st.info(
            "발송할 담당자 리포트가 없습니다. "
            "오류가 없거나, 담당자 이메일이 매핑되지 않았습니다(2단계 매핑 확인)."
        )
        _back_button()
        return

    config = load_smtp_config()
    if not config.is_configured:
        st.warning("SMTP가 설정되지 않았습니다(.env). 아래 '테스트 모드'로만 발송을 시뮬레이션합니다.")

    # 메일 템플릿 (PRD §5.8)
    st.subheader("메일 템플릿")
    subject_tpl = st.text_input("제목", value=DEFAULT_SUBJECT)
    body_tpl = st.text_area("본문", value=DEFAULT_BODY, height=220)
    dry_run = st.checkbox(
        "테스트 모드(실제 발송 안 함)", value=not config.is_configured,
    )

    st.divider()
    st.subheader("담당자별 발송 목록 (PRD §6.6)")

    selected: list[dict] = []
    for report, path in reports:
        data_ids = sorted({e.data_id for e in report.errors if e.data_id})
        ctx = {
            "person": report.person,
            "error_count": report.error_count,
            "data_id_list": ", ".join(data_ids) if data_ids else "-",
        }
        subject = safe_format(subject_tpl, **ctx)
        body = safe_format(body_tpl, **ctx)

        with st.expander(
            f"{report.person} <{report.email}> — 오류 {report.error_count}건"
        ):
            send_flag = st.checkbox(
                "발송 대상", value=True, key=f"send_{report.email}"
            )
            st.caption(f"첨부: {path.name}")
            st.text(f"제목: {subject}")
            st.text(body)

        if send_flag:
            selected.append(
                {"report": report, "path": path, "subject": subject, "body": body}
            )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        send_clicked = st.button(
            f"📤 선택 발송 ({len(selected)}명)", type="primary",
            disabled=not selected,
        )
    with col2:
        _back_button()

    if send_clicked:
        results = []
        history = HistoryRepository()
        run_id = st.session_state.run_id
        progress = st.progress(0.0, text="발송 중...")
        for i, item in enumerate(selected, start=1):
            res = send_report(
                to_email=item["report"].email,
                subject=item["subject"],
                body=item["body"],
                config=config,
                attachment=item["path"],
                dry_run=dry_run,
            )
            results.append(res)
            # 발송 이력 저장 (PRD §5.9)
            if run_id is not None:
                history.record_mail(
                    run_id=run_id,
                    person=item["report"].person,
                    email=item["report"].email,
                    report_file_name=item["path"].name,
                    status=res.status,
                    error_message=res.error or "",
                )
            progress.progress(i / len(selected), text=f"발송 중... ({i}/{len(selected)})")
        progress.empty()
        st.session_state.send_results = results

    # 발송 결과 (PRD §5.9)
    if st.session_state.send_results:
        st.subheader("발송 결과")
        table = pd.DataFrame(
            {
                "이메일": [r.email for r in st.session_state.send_results],
                "상태": [r.status for r in st.session_state.send_results],
                "오류": [r.error or "" for r in st.session_state.send_results],
            }
        )
        st.dataframe(table, use_container_width=True, hide_index=True)
        ok = sum(1 for r in st.session_state.send_results if r.success)
        st.success(f"{ok} / {len(st.session_state.send_results)} 건 처리 완료")


def _back_button() -> None:
    if st.button("← 이전: 검증 결과"):
        state.goto(3)
        st.rerun()
