# Maintenance Data Validation & Error Report System — 개발 계획서

> 본 문서는 `data_validation_prd.md`(PRD)를 기반으로 한 5단계 개발 계획이다.
> MVP(PRD §12.1) 범위를 우선 구현하고, 2차 기능(PRD §12.2)은 확장 지점만 열어둔다.

---

## 0. 기술 스택 및 설계 결정

> 비개발자(검토자·담당자)가 **코딩 없이** 사용해야 하고(PRD §10.3), 내부 데이터 품질 관리 도구라는 점을 고려한 선택이다. 시작 전 확정 필요.

| 영역 | 선택 | 사유 |
|---|---|---|
| 언어 | Python 3.13 | `venv627` 이미 구성됨 |
| UI | **Streamlit** | 파일 업로드·미리보기·단계형 화면을 코드 최소로 구현. 내부 도구에 적합. (대안: FastAPI+React = 공수 큼, PyQt = 배포 복잡) |
| 데이터 처리 | **pandas** | 벡터화 검증으로 1만 행 1분 내 목표 달성(PRD §10.1) |
| 엑셀 I/O | **openpyxl** (.xlsx), **xlrd**(.xls 읽기) | 읽기/리포트 생성 |
| 규칙 모델 | **Pydantic v2** | 규칙을 "데이터"로 직렬화(JSON)하여 템플릿 저장·재사용 |
| 이력 저장 | **SQLite** (SQLAlchemy) | 무설치 영속화. 향후 RDB 전환 시 ORM으로 흡수 |
| 메일 | **smtplib + email** (표준 라이브러리) | 사내 SMTP 연동. 자격증명은 환경변수/`.env` |
| 테스트 | **pytest** | 검증기 단위 테스트 |
| 설정/비밀 | **.env** (python-dotenv) | SMTP 계정 등 |

**핵심 설계 원칙 (PRD §14)**
- 원본 업로드 파일은 절대 변경하지 않는다. 리포트는 별도 파일로 생성. (§14.4)
- 컬럼명은 고정하지 않고 **매핑**으로 처리한다. (§14.1)
- 검증 규칙·오류 메시지는 **코드가 아닌 데이터**로 다룬다. (§14.3)
- 검증기는 오류 유형(PRD §9)과 1:1로 대응하는 독립·테스트 가능한 단위로 구현한다.

**제안 디렉터리 구조**
```
src/
  models/        # Pydantic: Rule, RuleTemplate, ColumnMapping, ErrorRecord, ErrorType
  io/            # excel_reader, report_writer
  engine/        # validators/*, validation_engine
  mailer/        # smtp_client, mail_template
  storage/       # db.py, repositories (upload/validation/mail history, templates)
  ui/            # streamlit 페이지 (main, upload, mapping, rules, results, mail)
  app.py         # 진입점
tests/           # 검증기·엔진 단위 테스트
data/            # sqlite db, 생성 리포트 (gitignore)
```

---

## 1단계 — 기반 구축 (Foundation & Domain Models)

> 이후 모든 단계가 의존하는 도메인 모델·입출력 토대를 만든다.

**작업 내용**
- 의존성 확정 및 `requirements.txt` 작성, `venv627`에 설치
- 프로젝트 구조 스캐폴딩 + `.gitignore`, `.env.example`
- 도메인 모델 정의 (Pydantic)
  - `ErrorType` 열거형 — PRD §9의 9개 오류 유형 정확히 사용
  - `DataType` 열거형 — Text/Number/Integer/Decimal/Date/Email/Boolean/Code-List/URL
  - `ColumnRule` — required, data_type, min/max, allowed_list, duplicate, conditional, error_message(override)
  - `RuleTemplate` — 이름 + ColumnRule 목록 (JSON 직렬화 가능)
  - `ColumnMapping` — 원본 컬럼 ↔ 시스템 기준 컬럼 (Data ID / Responsible Person / Responsible Email 필수 지정)
  - `ErrorRecord` — Data ID, Row No, Column, Input Value, Error Type, Error Message, 담당자/이메일 (PRD §8.3)
- 엑셀 리더 (`io/excel_reader.py`): `.xlsx`/`.xls` 로드, 시트 목록, 첫 행=헤더 인식, 미리보기 DataFrame, 예외 처리(형식 오류·헤더 없음·데이터 없음 — PRD §5.1)
  - CSV 확장(PRD §10.4)을 위해 Reader 인터페이스로 추상화

**산출물**: 도메인 모델 모듈, 엑셀 리더, 모델 직렬화 단위 테스트
**완료 기준**: 샘플 엑셀을 읽어 시트/헤더/미리보기를 반환하고, RuleTemplate을 JSON 저장·로드 왕복 가능

---

## 2단계 — 검증 엔진 (Validation Engine)

> 프로그램의 심장. UI와 완전히 분리하여 단위 테스트로 정확도를 보장한다.

**작업 내용 (MVP 검증기 — 오류 유형별 1:1 구현)**
- `Missing Required Value` — 빈값·공백·NULL 검출 (PRD §5.3.1)
- `Invalid Data Type` — Number/Integer/Decimal/Date/Boolean/URL 형식 검증 (§5.3.2)
- `Out of Range` — 숫자 min/max (§5.3.3)
- `Invalid List Value` — 허용 목록 검증 (§5.3.4)
- `Invalid Email Format` — 이메일 형식 (§5.3.6)
- `Duplicate Value` — 단일 컬럼 + 컬럼 조합 중복 (§5.3.7)
- `Column Mapping Error` — Data ID/담당자/이메일 매핑 누락 분류 (§14.2)
- (날짜 형식 §5.3.5는 타입 검증에 포함, 조건부 §5.3.8은 2차 고도화로 인터페이스만 확보)
- `ValidationEngine`: 매핑+템플릿+DataFrame → `ErrorRecord` 목록
  - pandas 벡터 연산 우선, 행 단위 파이썬 루프 지양 (성능 목표)
  - 진행률 콜백 제공 (UI 진행바 연동용)
  - 집계: 전체/정상/오류 행 수, 컬럼별·담당자별 오류 건수 (PRD §5.5)
- 기본 오류 메시지 + 컬럼별 사용자 정의 메시지 머지 로직 (§14.3)

**산출물**: `engine/validators/*`, `validation_engine.py`, 검증기별 pytest (정상/경계/오류 케이스)
**완료 기준**: PRD 부록 A 규칙 + 샘플 데이터로 부록 B의 오류가 정확히 재현됨

---

## 3단계 — UI 워크플로우 (Streamlit Screens)

> PRD §6, §7의 단계형 사용자 흐름을 화면으로 구현한다.

**작업 내용**
- 메인 화면: 업로드 영역, 최근 검증 이력, 템플릿 선택, 검증 시작 (§6.1)
- 업로드 화면: 파일 선택, 시트 선택, 미리보기, 컬럼 자동 인식 (§6.2)
- 컬럼 매핑 화면: 원본↔기준 컬럼 매핑, 담당자명/이메일/Data ID 지정, 매핑 저장·불러오기 (§6.3)
- 검증 규칙 설정 화면: 컬럼별 필수/타입/min·max/허용목록/중복/메시지 편집 (코드 없이) (§6.4)
- 검증 실행: 진행바, 2단계 엔진 호출
- 검증 결과 화면: 요약 카드(전체/정상/오류), 담당자별·컬럼별 건수, 오류 상세 테이블, 필터(담당자/컬럼/유형)·Data ID 검색, 엑셀 다운로드 (§6.5, §5.6)
- 세션 상태로 단계 간 데이터 전달

**산출물**: `ui/` 페이지 모듈, 실행 가능한 Streamlit 앱
**완료 기준**: 업로드→매핑→규칙→검증→결과 확인까지 화면으로 끝까지 수행 가능

---

## 4단계 — 담당자별 리포트 & 메일 발송 (Reports & Email)

> 검증 결과를 담당자별로 분리해 리포트화하고 메일로 전달한다.

**작업 내용**
- 리포트 생성 (`io/report_writer.py`): Responsible Person/Email 기준 분리, 담당자별 오류만 포함, Excel 생성 (PRD §5.7)
  - 구성: 요약 / 담당자 정보 / 오류 건수 / 오류 상세 / 수정 요청 코멘트 / 재제출 안내
  - 파일명 자동: `Validation_Report_{담당자}_{YYYY-MM-DD}.xlsx`
  - 원본 미변경 원칙 준수 — `data/reports/`에 별도 생성
- 메일 발송 화면 (§6.6): 담당자별 리포트 목록·건수, 제목·본문 템플릿(플레이스홀더 `{Error Count}`, `{Data ID List}`), 미리보기, 선택/전체 발송
- SMTP 클라이언트 (`mailer/`): 첨부 발송, 자격증명은 `.env`, 발송 결과(성공/실패) 반환
- 메일 제목·본문 기본 템플릿은 PRD 부록 C 사용

**산출물**: 리포트 생성기, 메일 발송기, 메일 화면
**완료 기준**: 검증 결과로 담당자별 리포트가 생성되고, 미리보기 후 (테스트 SMTP로) 첨부 메일 발송 성공

---

## 5단계 — 이력 관리 · 템플릿 영속화 · 마무리 (Persistence & Hardening)

> 반복 사용·추적성을 위한 영속화와 품질 마감.

**작업 내용**
- SQLite 스키마 + 리포지토리 (PRD §8.1~8.4)
  - 업로드 이력 / 검증 이력(파일명·일시·수행자·적용 템플릿·전체/오류 행 수) / 메일 발송 이력(대상·이메일·파일명·상태·실패사유)
  - 발송 상태: 발송완료/실패/대기/재발송완료, **재발송** 기능 (§5.9)
- Rule Template CRUD 영속화: 생성/수정/복사/삭제, 마지막 사용 템플릿 자동 로드 (§5.4)
- 컬럼 매핑 저장/불러오기 연동 (§5.2)
- 재검증: 수정 파일을 동일 템플릿으로 재실행 (§14.5)
- 마감: 통합 테스트, 에러 핸들링·사용자 메시지 정비, `README.md`(실행/설정/SMTP 가이드), `CLAUDE.md`의 빌드·실행·테스트 명령 갱신

**산출물**: storage 계층, 이력 화면 연동, 문서, 테스트 스위트
**완료 기준**: PRD §13.1 기능 성공 기준 7개 항목 전부 충족 — 업로드/규칙설정/자동검출/결과표시/리포트생성/메일발송/이력저장

---

## 단계 간 의존성

```
1단계(모델·IO) ─┬─▶ 2단계(엔진) ─▶ 3단계(UI) ─▶ 4단계(리포트·메일) ─▶ 5단계(이력·마감)
                └────────────────────────────────▲ (storage는 3·4단계에서 부분 사용)
```

## MVP 이후 (2차, PRD §12.2 — 본 계획 범위 외)
조건부 검증 고도화 · PDF 리포트 · 대시보드 · 프로젝트별 템플릿 · 재검증 비교 · 사내 메일/API 연동 · 승인 워크플로우.
→ 각 단계에서 인터페이스(Reader, Validator, Mailer, Repository)를 추상화해 확장 지점을 미리 확보한다.

## 시작 전 확정 필요 사항
1. **UI 형태**: Streamlit(권장) vs 데스크톱 앱 vs 웹(FastAPI+프론트)
2. **메일 발송 방식**: 사내 SMTP 서버 정보 / 별도 메일 API
3. **권한 관리(PRD §11)**: MVP에서 단일 사용자로 시작할지, 역할(Admin/Validator/Reviewer/Data Owner) 분리를 1차부터 넣을지
```

