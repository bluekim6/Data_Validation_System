"""전체 흐름 통합 테스트 (PRD §13.1 기능 성공 기준).

업로드 → 검증 → 리포트 → 발송(드라이런) → 이력 저장까지 한 번에 검증한다.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.dataio import ExcelReader
from src.engine import ValidationEngine
from src.mailer import SmtpConfig, send_report
from src.models import ColumnMapping, ColumnRule, DataType, RuleTemplate
from src.reporting import generate_reports
from src.storage import Database, HistoryRepository, TemplateRepository


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    path = tmp_path / "sample.xlsx"
    pd.DataFrame(
        {
            "Data ID": ["EQ-001", "EQ-002", "EQ-001"],
            "Maintenance Cycle": [12, "ABC", 6],
            "Criticality": ["High", "Very High", "Low"],
            "Responsible Person": ["홍길동", "김철수", "홍길동"],
            "Responsible Email": ["a@b.com", "bad-email", "a@b.com"],
        }
    ).to_excel(path, index=False, sheet_name="Data")
    return path


def test_full_pipeline(sample_file: Path, tmp_path: Path) -> None:
    db = Database(f"sqlite:///{tmp_path / 'it.db'}")

    # 1) 업로드/읽기
    df = ExcelReader(sample_file).read_sheet("Data")
    assert len(df) == 3

    # 2) 매핑 + 템플릿
    cols = list(df.columns)
    mapping = ColumnMapping(
        column_map={c: c for c in cols},
        data_id_column="Data ID",
        responsible_person_column="Responsible Person",
        responsible_email_column="Responsible Email",
    )
    template = RuleTemplate(
        name="IT",
        rules=[
            ColumnRule(column="Data ID", required=True, duplicate_check=True),
            ColumnRule(column="Maintenance Cycle", data_type=DataType.NUMBER,
                       min_value=1, max_value=120),
            ColumnRule(column="Criticality",
                       allowed_list=["High", "Medium", "Low"]),
            ColumnRule(column="Responsible Email", required=True,
                       data_type=DataType.EMAIL),
        ],
    )

    # 템플릿 저장/재로드 (재검증 시나리오, PRD §14.5)
    TemplateRepository(db).save(template)
    reloaded = TemplateRepository(db).get("IT")
    assert reloaded is not None

    # 3) 검증
    result = ValidationEngine(reloaded, mapping).validate(df)
    assert result.error_count > 0
    # 중복(EQ-001), 타입(ABC), 목록(Very High), 이메일(bad-email) 검출
    types = set(result.errors_by_type)
    assert {"Duplicate Value", "Invalid Data Type",
            "Invalid List Value", "Invalid Email Format"} <= types

    # 4) 이력 저장
    history = HistoryRepository(db)
    run_id = history.record_validation(
        file_name=sample_file.name, sheet_name="Data", run_user="tester",
        template_name=reloaded.name, result=result,
    )

    # 5) 리포트 생성 + 드라이런 발송 + 발송 이력
    reports = generate_reports(result.errors, tmp_path / "reports")
    assert len(reports) >= 1
    for report, path in reports:
        res = send_report(
            to_email=report.email, subject="s", body="b",
            config=SmtpConfig(), attachment=path, dry_run=True,
        )
        assert res.success
        history.record_mail(
            run_id=run_id, person=report.person, email=report.email,
            report_file_name=path.name, status=res.status,
        )

    # 이력 확인
    runs = history.list_validations()
    assert runs[0].id == run_id
    assert len(history.list_mails(run_id)) == len(reports)
