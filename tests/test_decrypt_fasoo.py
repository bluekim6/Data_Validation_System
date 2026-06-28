"""Fasoo DRM 복호화 훅 단위 테스트 (참조: creat_code.md).

핵심 계약:
- 호출은 항상 "원본 경로"를 반환한다(복호화 성공/실패/미지원 무관) → 파싱은 계속된다.
- Windows가 아닌 개발 환경에서는 안전하게 no-op으로 동작한다.
- DLL 로드/호출 실패 시에도 예외를 던지지 않고 원본 경로를 그대로 반환한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.dataio import decrypt_fasoo_file, enable_drm, is_drm_supported
from src.dataio import decrypt_fasoo as df


@pytest.fixture(autouse=True)
def _reset_cache():
    df.reset_cache()
    yield
    df.reset_cache()


def test_returns_original_path(tmp_path: Path) -> None:
    src = tmp_path / "maintenance.xlsx"
    src.write_bytes(b"dummy")
    assert decrypt_fasoo_file(src) == src


def test_returns_path_even_when_file_missing(tmp_path: Path) -> None:
    # 파일이 없어도 경로 반환 자체는 실패하지 않는다(읽기 단계에서 별도 처리).
    missing = tmp_path / "nope.xlsx"
    assert decrypt_fasoo_file(missing) == missing


def test_accepts_str_path(tmp_path: Path) -> None:
    src = tmp_path / "data.xlsx"
    src.write_bytes(b"x")
    assert decrypt_fasoo_file(str(src)) == src


def test_noop_on_non_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(df.sys, "platform", "darwin")
    df.reset_cache()
    assert is_drm_supported() is False
    assert enable_drm() is False


def test_enable_drm_is_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(df.sys, "platform", "darwin")
    df.reset_cache()
    assert enable_drm() is False
    # 캐시된 결과를 그대로 반환(재시도하지 않음).
    assert enable_drm() is False


def test_windows_dll_load_failure_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    # Windows로 가장하되 DLL 로드가 실패하도록 하여, 예외 없이 False가 되는지 확인.
    monkeypatch.setattr(df.sys, "platform", "win32")
    monkeypatch.setenv("FASOO_DLL_PATH", "Z:/does/not/exist/f_nxldr.dll")
    df.reset_cache()
    assert is_drm_supported() is True
    assert enable_drm() is False  # 로드 실패해도 예외 없이 False


def test_decrypt_continues_after_drm_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(df.sys, "platform", "win32")
    monkeypatch.setenv("FASOO_DLL_PATH", "Z:/does/not/exist/f_nxldr.dll")
    df.reset_cache()
    src = tmp_path / "drm.xlsx"
    src.write_bytes(b"dummy")
    # DRM 해제 실패 시에도 원본 경로 반환(계약).
    assert decrypt_fasoo_file(src) == src
