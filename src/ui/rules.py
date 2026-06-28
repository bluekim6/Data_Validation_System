"""3단계 화면: 컬럼별 검증 규칙 설정 + 템플릿 관리 (PRD §5.3, §5.4, §6.4).

코드 없이(PRD §10.3) 표 형태로 컬럼별 규칙을 설정하고, 자주 쓰는 규칙은 템플릿으로
저장/불러오기/복사/삭제한다. 마지막 사용 템플릿은 자동으로 불러온다(PRD §5.4).
"""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from ..models import ColumnRule, DataType, RuleTemplate
from ..storage import TemplateRepository
from . import state

_DATA_TYPES = [dt.value for dt in DataType]


def render() -> None:
    mapping = st.session_state.mapping
    if mapping is None or not mapping.column_map:
        st.warning("먼저 2단계에서 컬럼 매핑을 완료하세요.")
        return

    st.header("3. 검증 규칙 설정")
    repo = TemplateRepository()

    # 마지막 사용 템플릿 자동 불러오기 (최초 진입 시)
    if st.session_state.template is None:
        st.session_state.template = repo.get_last_used()

    _load_controls(repo)

    st.caption("기준 컬럼별로 검증 기준을 설정하세요. 빈 칸은 해당 검증을 적용하지 않습니다.")
    canonical_columns = list(dict.fromkeys(mapping.column_map.values()))
    editor_df = _build_editor_df(canonical_columns, st.session_state.template)

    edited = st.data_editor(
        editor_df,
        use_container_width=True,
        hide_index=True,
        disabled=["컬럼"],
        column_config={
            "컬럼": st.column_config.TextColumn("기준 컬럼"),
            "필수": st.column_config.CheckboxColumn("필수"),
            "데이터타입": st.column_config.SelectboxColumn(
                "데이터 타입", options=_DATA_TYPES, required=True
            ),
            "최소값": st.column_config.NumberColumn("최소값"),
            "최대값": st.column_config.NumberColumn("최대값"),
            "허용목록": st.column_config.TextColumn(
                "허용 목록", help="쉼표로 구분 (예: High, Medium, Low)"
            ),
            "중복검사": st.column_config.CheckboxColumn("중복 불가"),
            "오류메시지": st.column_config.TextColumn(
                "오류 메시지(선택)", help="비워두면 기본 메시지를 사용합니다"
            ),
        },
        key="rules_editor",
    )

    current_name = (
        st.session_state.template.name
        if st.session_state.template else "(현재 설정)"
    )
    current = _to_template(edited, current_name)
    _save_controls(repo, current)

    nav_prev, nav_next = st.columns(2)
    with nav_prev:
        if st.button("← 이전: 컬럼 매핑"):
            st.session_state.template = current
            state.goto(1)
            st.rerun()
    with nav_next:
        if st.button("검증 실행 →", type="primary"):
            st.session_state.template = current
            st.session_state.result = None  # 새로 실행
            st.session_state.run_id = None
            state.goto(3)
            st.rerun()


def _load_controls(repo: TemplateRepository) -> None:
    names = repo.list_names()
    if not names:
        return
    with st.expander("💾 저장된 템플릿 불러오기 / 삭제", expanded=False):
        col1, col2, col3 = st.columns([3, 1, 1])
        choice = col1.selectbox("템플릿", names, key="tpl_load_choice")
        if col2.button("불러오기"):
            loaded = repo.get(choice)
            if loaded is not None:
                repo.mark_used(choice)
                st.session_state.template = loaded
                st.success(f"'{choice}' 템플릿을 불러왔습니다.")
                st.rerun()
        if col3.button("삭제"):
            repo.delete(choice)
            st.warning(f"'{choice}' 템플릿을 삭제했습니다.")
            st.rerun()


def _save_controls(repo: TemplateRepository, current: RuleTemplate) -> None:
    with st.expander("💾 현재 규칙을 템플릿으로 저장", expanded=False):
        col1, col2 = st.columns([3, 1])
        default = "" if current.name == "(현재 설정)" else current.name
        name = col1.text_input("템플릿 이름", value=default, key="tpl_save_name")
        if col2.button("저장", type="primary", disabled=not name.strip()):
            to_save = RuleTemplate(
                name=name.strip(), description=current.description, rules=current.rules
            )
            repo.save(to_save)
            repo.mark_used(name.strip())
            st.session_state.template = to_save
            st.success(f"'{name.strip()}' 템플릿을 저장했습니다.")
            st.rerun()


def _build_editor_df(columns: list[str], template: RuleTemplate | None) -> pd.DataFrame:
    rows = []
    for col in columns:
        rule = template.get_rule(col) if template else None
        rows.append(
            {
                "컬럼": col,
                "필수": rule.required if rule else False,
                "데이터타입": rule.data_type.value if rule else DataType.TEXT.value,
                "최소값": rule.min_value if rule else None,
                "최대값": rule.max_value if rule else None,
                "허용목록": ", ".join(rule.allowed_list) if rule else "",
                "중복검사": rule.duplicate_check if rule else False,
                "오류메시지": (rule.custom_message or "") if rule else "",
            }
        )
    return pd.DataFrame(rows)


def _to_template(edited: pd.DataFrame, name: str) -> RuleTemplate:
    rules: list[ColumnRule] = []
    for row in edited.itertuples(index=False):
        allowed = [s.strip() for s in str(row.허용목록).split(",") if s.strip()]
        rules.append(
            ColumnRule(
                column=row.컬럼,
                required=bool(row.필수),
                data_type=DataType(row.데이터타입),
                min_value=_num_or_none(row.최소값),
                max_value=_num_or_none(row.최대값),
                allowed_list=allowed,
                duplicate_check=bool(row.중복검사),
                custom_message=str(row.오류메시지).strip() or None,
            )
        )
    return RuleTemplate(name=name, rules=rules)


def _num_or_none(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return float(value)
