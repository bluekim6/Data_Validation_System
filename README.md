# Maintenance Data Validation & Error Report System

해양플랜트 유지보수 데이터(엑셀)를 업로드하여 정합성 오류를 자동 검증하고, 담당자별
오류 리포트를 생성·메일 발송하는 도구입니다. 자세한 요구사항은
[`data_validation_prd.md`](data_validation_prd.md), 개발 계획은
[`development_plan.md`](development_plan.md)를 참고하세요.

## 주요 기능

- 엑셀(.xlsx/.xls) 업로드 · 시트 선택 · 컬럼 자동 인식
- 원본↔기준 컬럼 매핑 (담당자/이메일/Data ID 지정)
- 코드 없이 컬럼별 검증 규칙 설정 (필수/타입/범위/허용목록/이메일/중복)
- 검증 규칙 템플릿 저장·불러오기·복사·삭제, 마지막 사용 템플릿 자동 로드
- 검증 결과 화면 (요약·담당자별/컬럼별 집계·필터·엑셀 다운로드)
- 담당자별 Excel 리포트 생성 + 메일 발송 (미리보기 / 선택 발송 / 테스트 모드)
- 검증·발송 이력 저장 (SQLite)

## 설치

```bash
python -m venv venv627          # 이미 있으면 생략
source venv627/bin/activate
pip install -r requirements.txt
```

## 실행

```bash
streamlit run app.py
```

브라우저에서 워크플로우를 따라 진행합니다:
**업로드 → 컬럼 매핑 → 검증 규칙 → 검증 결과 → 리포트·메일**

테스트용 샘플 데이터 생성:

```bash
python scripts/generate_sample.py     # data/sample_maintenance.xlsx
```

## 메일 발송 설정

SMTP 정보를 `.env`에 설정합니다 (`.env.example` 복사):

```bash
cp .env.example .env
# SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / SMTP_USE_TLS 입력
```

설정이 없으면 메일 화면은 **테스트 모드(실제 발송 안 함)** 로만 동작합니다.

## 테스트

```bash
python -m pytest                 # 전체
python -m pytest tests/test_validation_engine.py::test_aggregations   # 단일
```

## 아키텍처

| 패키지 | 역할 |
|---|---|
| `src/models/` | 도메인 모델 (규칙·매핑·오류 — 규칙은 데이터로 취급) |
| `src/dataio/` | 엑셀 리더 (`DataReader` 인터페이스, 원본 불변) |
| `src/engine/` | 검증기(오류 유형별 1:1) + 검증 엔진 + 결과 집계 |
| `src/reporting/` | 담당자별 Excel 리포트 생성 |
| `src/mailer/` | SMTP 설정·템플릿·발송 (dry_run 지원) |
| `src/storage/` | SQLite 영속화 (템플릿/매핑 CRUD, 검증/발송 이력) |
| `src/ui/` | Streamlit 단계형 화면 |

검증 엔진은 UI와 완전히 분리되어 있어 단위 테스트로 정확도를 보장합니다.

## 데이터 저장 위치

- DB: `data/validation.db` (환경변수 `DB_PATH`)
- 리포트: `data/reports/` (환경변수 `REPORT_DIR`)

> 참고: 검증 과정에서 **원본 업로드 파일은 변경하지 않습니다**. 리포트는 별도 파일로 생성됩니다.
# Data_Validation_System
