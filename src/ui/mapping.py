"""2단계 화면: 컬럼 매핑 + 역할(담당자/이메일/Data ID) 지정 (PRD §5.2, §6.3, §14.2)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ..models import ColumnMapping, MappingRole
from . import state


def render() -> None:
    df = st.session_state.df
    if df is None:
        st.warning("먼저 1단계에서 파일을 업로드하세요.")
        return

    st.header("2. 컬럼 매핑")
    st.caption(
        "원본 엑셀 컬럼을 시스템 기준 컬럼에 연결합니다. "
        "기본값은 원본 컬럼명과 동일하며, 필요 시 수정하세요."
    )

    source_columns = [str(c) for c in df.columns]

    # 기존 매핑이 있으면 복원, 없으면 기본값(원본=기준)
    existing = st.session_state.mapping
    if existing is not None:
        default_canon = {
            src: existing.column_map.get(src, src) for src in source_columns
        }
        default_use = {src: src in existing.column_map for src in source_columns}
    else:
        default_canon = {src: src for src in source_columns}
        default_use = {src: True for src in source_columns}

    editor_df = pd.DataFrame(
        {
            "원본 컬럼": source_columns,
            "기준 컬럼": [default_canon[s] for s in source_columns],
            "사용": [default_use[s] for s in source_columns],
        }
    )

    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        disabled=["원본 컬럼"],
        column_config={
            "사용": st.column_config.CheckboxColumn("사용", help="검증에 포함할지 여부"),
            "기준 컬럼": st.column_config.TextColumn("기준 컬럼", required=True),
        },
        key="mapping_editor",
    )

    # 사용 체크된 행만 매핑
    used = edited[edited["사용"]]
    column_map = dict(zip(used["원본 컬럼"], used["기준 컬럼"]))
    canonical_options = ["(선택)"] + list(dict.fromkeys(column_map.values()))

    st.subheader("필수 역할 컬럼 지정 (PRD §14.2)")
    st.caption("담당자별 리포트 생성을 위해 아래 세 컬럼은 반드시 지정해야 합니다.")
    col1, col2, col3 = st.columns(3)
    with col1:
        data_id = _role_select("Data ID 컬럼", canonical_options,
                               _prev_role(existing, MappingRole.DATA_ID))
    with col2:
        person = _role_select("담당자명 컬럼", canonical_options,
                              _prev_role(existing, MappingRole.RESPONSIBLE_PERSON))
    with col3:
        email = _role_select("담당자 이메일 컬럼", canonical_options,
                             _prev_role(existing, MappingRole.RESPONSIBLE_EMAIL))

    mapping = ColumnMapping(
        column_map=column_map,
        data_id_column=data_id,
        responsible_person_column=person,
        responsible_email_column=email,
    )

    missing = mapping.missing_required_roles()
    if missing:
        st.warning(
            "다음 필수 역할이 지정되지 않았습니다: "
            + ", ".join(r.value for r in missing)
            + " — 검증은 가능하지만 매핑 오류로 분류되고, 담당자 리포트가 제한됩니다."
        )

    nav_prev, nav_next = st.columns(2)
    with nav_prev:
        if st.button("← 이전: 업로드"):
            st.session_state.mapping = mapping
            state.goto(0)
            st.rerun()
    with nav_next:
        if st.button("다음: 검증 규칙 →", type="primary"):
            st.session_state.mapping = mapping
            state.goto(2)
            st.rerun()


def _role_select(label: str, options: list[str], previous: str | None) -> str | None:
    index = options.index(previous) if previous in options else 0
    choice = st.selectbox(label, options, index=index)
    return None if choice == "(선택)" else choice


def _prev_role(mapping: ColumnMapping | None, role: MappingRole) -> str | None:
    if mapping is None:
        return None
    return mapping.role_columns().get(role)
