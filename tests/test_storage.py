"""영속화 계층 테스트 (PRD §5.4, §5.9, §5.10).

각 테스트는 임시 파일 DB를 사용해 격리한다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.engine import ValidationResult
from src.models import ColumnMapping, ColumnRule, DataType, ErrorRecord, ErrorType, RuleTemplate
from src.storage import (
    Database,
    HistoryRepository,
    MappingRepository,
    TemplateRepository,
)


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(f"sqlite:///{tmp_path / 'test.db'}")


def _template(name: str = "T1") -> RuleTemplate:
    return RuleTemplate(
        name=name,
        description="desc",
        rules=[
            ColumnRule(column="Maintenance Cycle", data_type=DataType.NUMBER,
                       min_value=1, max_value=120),
        ],
    )


def test_template_save_and_get(db: Database) -> None:
    repo = TemplateRepository(db)
    repo.save(_template())
    loaded = repo.get("T1")
    assert loaded is not None
    assert loaded.get_rule("Maintenance Cycle").max_value == 120


def test_template_upsert_updates(db: Database) -> None:
    repo = TemplateRepository(db)
    repo.save(_template())
    updated = _template()
    updated.description = "changed"
    repo.save(updated)
    assert repo.list_names() == ["T1"]  # 중복 생성되지 않음
    assert repo.get("T1").description == "changed"


def test_template_copy_and_delete(db: Database) -> None:
    repo = TemplateRepository(db)
    repo.save(_template())
    repo.copy("T1", "T2")
    assert set(repo.list_names()) == {"T1", "T2"}
    repo.delete("T1")
    assert repo.list_names() == ["T2"]


def test_template_last_used(db: Database) -> None:
    repo = TemplateRepository(db)
    repo.save(_template("A"))
    repo.save(_template("B"))
    assert repo.get_last_used() is None
    repo.mark_used("A")
    repo.mark_used("B")
    assert repo.get_last_used().name == "B"


def test_mapping_save_load(db: Database) -> None:
    repo = MappingRepository(db)
    mapping = ColumnMapping(
        column_map={"설비태그": "Equipment Tag No."},
        data_id_column="Data ID",
    )
    repo.save("preset1", mapping)
    loaded = repo.get("preset1")
    assert loaded.column_map == {"설비태그": "Equipment Tag No."}
    assert "preset1" in repo.list_names()


def test_history_validation_and_mail(db: Database) -> None:
    history = HistoryRepository(db)
    result = ValidationResult(
        errors=[
            ErrorRecord(data_id="EQ-001", row_number=3, column_name="X",
                        error_type=ErrorType.INVALID_DATA_TYPE,
                        error_message="m", responsible_email="a@b.com"),
        ],
        total_rows=10,
    )
    run_id = history.record_validation(
        file_name="data.xlsx", sheet_name="Sheet1", run_user="tester",
        template_name="T1", result=result,
    )
    assert run_id > 0

    history.record_mail(
        run_id=run_id, person="홍길동", email="a@b.com",
        report_file_name="r.xlsx", status="발송 완료",
    )

    runs = history.list_validations()
    assert len(runs) == 1
    assert runs[0].file_name == "data.xlsx"
    assert runs[0].error_count == 1

    mails = history.list_mails(run_id)
    assert len(mails) == 1
    assert mails[0].status == "발송 완료"
