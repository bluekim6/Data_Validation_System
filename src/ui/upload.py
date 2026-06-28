"""1단계 화면: 엑셀 업로드 + 시트 선택 + 미리보기 (PRD §5.1, §6.2)."""

from __future__ import annotations

import streamlit as st

from ..dataio import DataReadError, ExcelReader, decrypt_fasoo_file, is_drm_supported
from . import state


def render() -> None:
    st.header("1. 엑셀 파일 업로드")
    st.caption("유지보수 데이터가 담긴 엑셀 파일(.xlsx, .xls)을 업로드하세요.")

    if is_drm_supported():
        st.caption("🔒 Fasoo DRM 환경: 업로드된 파일은 파싱 전 자동으로 DRM이 해제됩니다.")

    uploaded = st.file_uploader("엑셀 파일 선택", type=["xlsx", "xls"])
    if uploaded is None:
        return

    # 새 파일이면 임시 저장 후 시트 목록 로드
    if st.session_state.file_name != uploaded.name:
        try:
            path = state.save_upload(uploaded)
            # 파싱 전에 Fasoo DRM 해제(참조: creat_code.md). 실패해도 원본 경로 그대로 진행.
            path = decrypt_fasoo_file(path)
            reader = ExcelReader(path)
            st.session_state.upload_path = str(path)
            st.session_state.file_name = uploaded.name
            st.session_state.sheet_names = reader.sheet_names()
            st.session_state.selected_sheet = reader.sheet_names()[0]
            st.session_state.df = None
        except DataReadError as exc:
            st.error(f"파일을 읽을 수 없습니다: {exc}")
            return

    sheet = st.selectbox(
        "시트 선택",
        st.session_state.sheet_names,
        index=st.session_state.sheet_names.index(st.session_state.selected_sheet),
    )
    st.session_state.selected_sheet = sheet

    # 선택 시트 읽기 + 미리보기
    try:
        reader = ExcelReader(st.session_state.upload_path)
        df = reader.read_sheet(sheet)
    except DataReadError as exc:
        st.error(f"시트를 읽을 수 없습니다: {exc}")
        return

    st.session_state.df = df
    st.success(f"컬럼 {df.shape[1]}개 · 데이터 {df.shape[0]}행을 인식했습니다.")
    st.subheader("미리보기 (상위 20행)")
    st.dataframe(df.head(20), use_container_width=True)

    if st.button("다음: 컬럼 매핑 →", type="primary"):
        state.goto(1)
        st.rerun()
