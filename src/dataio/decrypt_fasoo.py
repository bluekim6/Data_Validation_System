"""Fasoo DRM 복호화 (참조: creat_code.md).

운영 환경(사내 Windows)에서 업로드되는 CSV/Excel 파일에는 **Fasoo DRM**이 걸려
있을 수 있다. 파싱 전에 `decrypt_fasoo_file()`을 호출하면, 현재 프로세스가 Fasoo
커널 드라이버를 통해 DRM 콘텐츠를 **투명하게 복호화**하여 읽을 수 있게 된다
(`f_nxldr.dll`의 `EnableDRM()`은 파일이 아니라 *프로세스* 단위로 동작한다).

설계 원칙:
- **Windows 전용**: `C:/Windows/System32/f_nxldr.dll`(경로는 `FASOO_DLL_PATH`로 재정의
  가능). 그 외 OS(개발용 macOS/Linux)에서는 안전하게 no-op으로 동작해 개발 흐름을
  막지 않는다.
- **실패해도 멈추지 않음**: DRM 해제에 실패하면 원본 파일 경로를 그대로 반환하고
  파싱을 계속 시도한다(DRM이 걸려 있지 않은 일반 파일이라면 그대로 읽힌다).
- **프로세스 1회 활성화**: `EnableDRM()`은 프로세스 단위라 한 번만 호출하고 결과를
  캐시한다 → 업로드/시트 전환마다 재호출돼도 비용이 없다.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# 운영(사내 Windows) 기본 DLL 경로 — 필요 시 환경변수로 재정의한다.
DEFAULT_FASOO_DLL = r"C:/Windows/System32/f_nxldr.dll"

# EnableDRM()은 프로세스 단위로 동작하므로 활성화 시도 결과를 캐시한다.
#   None  = 아직 시도 안 함
#   True  = 활성화 성공 (이 프로세스는 DRM 파일을 투명하게 읽을 수 있음)
#   False = 미지원 또는 활성화 실패 (원본 그대로 읽기 시도)
_drm_enabled: bool | None = None


def is_drm_supported() -> bool:
    """현재 환경에서 Fasoo DRM 해제를 시도할 수 있는지(=Windows) 판정한다."""
    return sys.platform.startswith("win")


def _dll_path() -> str:
    return os.getenv("FASOO_DLL_PATH", DEFAULT_FASOO_DLL)


def enable_drm() -> bool:
    """현재 프로세스에서 Fasoo DRM 투명 복호화를 활성화한다(프로세스당 1회, 캐시).

    Returns:
        활성화 성공 여부. Windows가 아니거나 DLL 로드/호출에 실패하면 False.
    """
    global _drm_enabled
    if _drm_enabled is not None:
        return _drm_enabled

    if not is_drm_supported():
        logger.info("Fasoo DRM 미지원 환경(%s) — 복호화 없이 진행합니다.", sys.platform)
        _drm_enabled = False
        return _drm_enabled

    # ctypes는 Windows 전용 경로에서만 import 비용을 치른다.
    from ctypes import CDLL, c_int

    dll_path = _dll_path()
    try:
        fasoo = CDLL(dll_path)
        fasoo.EnableDRM.restype = c_int
        ret = fasoo.EnableDRM()
        if not ret:
            raise RuntimeError("EnableDRM()이 실패(0)를 반환했습니다.")
        logger.info("Fasoo DRM 활성화 성공 (%s)", dll_path)
        _drm_enabled = True
    except Exception as exc:  # noqa: BLE001 - DLL 부재/권한/심볼 누락 등 일괄 처리
        logger.warning("Fasoo DRM 활성화 실패 (%s): %s — 원본 그대로 진행합니다.", dll_path, exc)
        _drm_enabled = False

    return _drm_enabled


def decrypt_fasoo_file(uploaded_file_path: str | Path) -> Path:
    """업로드 파일을 파싱하기 전에 호출한다.

    Fasoo DRM 투명 복호화를 활성화한 뒤, 동일 경로를 반환한다(복호화는 이후 읽기
    시점에 커널 드라이버가 투명하게 수행한다). 활성화에 실패해도 **원본 경로를 그대로
    반환**하여 파싱 시도를 계속한다.
    """
    path = Path(uploaded_file_path)
    enable_drm()  # 결과와 무관하게(실패 시 원본 그대로) 경로를 반환한다.
    return path


def reset_cache() -> None:
    """활성화 캐시를 초기화한다(테스트 용)."""
    global _drm_enabled
    _drm_enabled = None
