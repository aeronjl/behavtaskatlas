from pathlib import Path

from behavtaskatlas.models import VerticalSlice
from behavtaskatlas.validation import validate_repository


def test_seed_records_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    report = validate_repository(root)
    assert report.ok, [f"{issue.path}: {issue.message}" for issue in report.issues]
    assert len(report.records) >= 12
    assert sum(isinstance(record, VerticalSlice) for record in report.records) == 3
